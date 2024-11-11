import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.config import Config
from uvicorn.server import Server

from core.db import sessionmanager
from routers.user_router import router as user_router
from routers.symbol_router import router as symbol_router
from routers.alert_router import router as alert_router
from routers.broker_router import router as broker_router
from routers.exin_item_router import router as exin_item_router
from routers.currency_router import router as currency_router
from routers.wallet_router import router as wallet_router
from routers.wallet_transaction_router import (
    router as wallet_transaction_router,
)
from routers.checklist_router import router as checklist_router
from routers.lines_router import router as lines_router
from routers.trade_router import router as trade_router

from tasks import (
    task_run_market_streams,
    task_update_market_data,
    task_remove_old_checklist_items,
    task_get_orders,
    task_get_usd_rub_rate,
    task_get_positions,
    task_remove_old_orders,
)
import core.config


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    stop_event.set()
    await sessionmanager.close()


app = FastAPI(
    lifespan=lifespan,
    openapi_prefix="/api/v2",
)

app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],  # Разрешенные источники
       allow_credentials=True,
       allow_methods=["*"],  # Разрешите все методы или укажите конкретные
       allow_headers=["*"],  # Разрешите все заголовки или укажите конкретные
   )

app.include_router(user_router)
app.include_router(symbol_router)
app.include_router(alert_router)
app.include_router(broker_router)
app.include_router(exin_item_router)
app.include_router(currency_router)
app.include_router(wallet_router)
app.include_router(wallet_transaction_router)
app.include_router(checklist_router)
app.include_router(lines_router)
app.include_router(trade_router)

stop_event = asyncio.Event()


async def run_fastapi():
    config = Config(app=app, host="0.0.0.0", port=9000, lifespan="on", log_level="warning")
    server = Server(config)
    await server.serve()


async def main() -> None:
    await asyncio.gather(
        run_fastapi(),
        task_run_market_streams(stop_event, sessionmanager),
        task_update_market_data(stop_event),
        task_remove_old_checklist_items(stop_event, sessionmanager),
        task_get_orders(stop_event, sessionmanager),
        task_get_usd_rub_rate(stop_event, sessionmanager),
        task_get_positions(stop_event, sessionmanager),
        task_remove_old_orders(stop_event, sessionmanager),
    )


if __name__ == "__main__":
    asyncio.run(main())
