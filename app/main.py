import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
import config
from db.db_connection import db
from uvicorn.config import Config
from uvicorn.server import Server
from routers.brokers_router import router as brokers_router
from routers.users_router import router as users_router
from routers.symbols_router import router as symbols_router
from routers.alerts_router import router as alerts_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.on_startup()
    yield
    stop_event.set()
    await db.on_shutdown()


app = FastAPI(lifespan=lifespan) # type: ignore
app.include_router(brokers_router)
app.include_router(users_router)
app.include_router(symbols_router)
app.include_router(alerts_router)

stop_event = asyncio.Event()


async def run_fastapi():
    config = Config(app=app, host="0.0.0.0", port=9000, lifespan="on")
    server = Server(config)
    await server.serve()


async def main() -> None:
    await asyncio.gather(
        run_fastapi(),
    )

if __name__ == "__main__":
    asyncio.run(main())