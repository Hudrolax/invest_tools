import asyncio
from contextlib import asynccontextmanager
import core.config
from fastapi import FastAPI
from uvicorn.config import Config
from uvicorn.server import Server

from core.db import sessionmanager
from routers.user_router import router as user_router
from routers.symbol_router import router as symbol_router
from routers.alert_router import router as alert_router
from routers.broker_router import router as broker_router

from tasks import task_run_market_streams
from tasks import task_update_market_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    stop_event.set()
    await sessionmanager.close()


app = FastAPI(lifespan=lifespan) # type: ignore
app.include_router(user_router)
app.include_router(symbol_router)
app.include_router(alert_router)
app.include_router(broker_router)

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