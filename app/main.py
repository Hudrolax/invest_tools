import asyncio
from contextlib import asynccontextmanager
import core.config
from fastapi import FastAPI
from uvicorn.config import Config
from uvicorn.server import Server
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse

from core.db import sessionmanager
from routers.user_router import router as user_router
from routers.symbol_router import router as symbol_router
from routers.alert_router import router as alert_router
from routers.broker_router import router as broker_router
from routers.exin_item_router import router as exin_item_router
from routers.currency_router import router as currency_router
from routers.wallet_router import router as wallet_router
from routers.wallet_transaction_router import router as wallet_transaction_router

from tasks import task_run_market_streams
from tasks import task_update_market_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    stop_event.set()
    await sessionmanager.close()


app = FastAPI(
    lifespan=lifespan, # type: ignore
    openapi_prefix="/api/v1",
)

# @app.middleware("http")
# async def redirect_docs(request, call_next):
#     if request.url.path == "/docs":
#         return RedirectResponse(url='/api/v1/docs')
#     return await call_next(request)


app.include_router(user_router)
app.include_router(symbol_router)
app.include_router(alert_router)
app.include_router(broker_router)
app.include_router(exin_item_router)
app.include_router(currency_router)
app.include_router(wallet_router)
app.include_router(wallet_transaction_router)

stop_event = asyncio.Event()


async def run_fastapi():
    config = Config(app=app, host="0.0.0.0", port=9000, lifespan="on")
    server = Server(config)
    await server.serve()


async def main() -> None:
    await asyncio.gather(
        run_fastapi(),
        task_run_market_streams(stop_event, sessionmanager),
        task_update_market_data(stop_event),
    )

if __name__ == "__main__":
    asyncio.run(main())
