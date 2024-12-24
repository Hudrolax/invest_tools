from decimal import Decimal
from datetime import datetime
import logging

from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import sessionmanager
from sqlalchemy import delete
from brokers.bybit import BYBIT_MARKET_TYPE_BROKER, BybitBroker

from models.position import PositionORM
from models.broker import BrokerORM
from models.symbol import SymbolORM
from utils import log_error_with_traceback

logger = logging.getLogger(__name__)


async def refresh_positions_in_db(
    db: AsyncSession,
    positions: list[dict],
    broker: BybitBroker | None = None,
    symbol: str | None = None,
) -> None:
    try:
        if not broker:
            await db.execute(delete(PositionORM))
        else:
            if not symbol:
                raise ValueError("Symbol should be passed")

            symbol_instance = await SymbolORM.get_by_name_and_broker(db, name=symbol.upper(), broker_name=broker)
            await db.execute(delete(PositionORM).where(PositionORM.symbol_id == symbol_instance.id))

        for position in positions:
            if Decimal(position["positionValue"]) == Decimal(0):
                continue

            try:
                broker_name = broker if broker else BYBIT_MARKET_TYPE_BROKER[position["category"]]
                broker = await BrokerORM.get_by_name(db, name=broker_name)
                try:
                    symbol_instance = await SymbolORM.get_by_name_and_broker(
                        db, name=position["symbol"], broker_name=broker.name
                    )
                except NoResultFound:
                    symbol_instance = await SymbolORM.get_or_create(db, name=position["symbol"], broker_id=broker.id)

                await SymbolORM.update(db, id=symbol_instance.id, active_wss=True)
            except NoResultFound as ex:
                logger.error(ex)
                continue

            await PositionORM.create(
                db,
                user_id=1,
                symbol_id=symbol_instance.id,
                side=position["side"],
                size=Decimal(position["size"]),
                position_value=Decimal(position["positionValue"]),
                mark_price=Decimal(position["markPrice"]),
                entry_price=Decimal(position["entryPrice"] if position.get("entryPrice") else position["avgPrice"]),
                leverage=(Decimal(position["leverage"]) if position["leverage"] else None),
                position_balance=(Decimal(position["positionBalance"]) if position["positionBalance"] else None),
                liq_price=(Decimal(position["liqPrice"]) if position["liqPrice"] else None),
                take_profit=(Decimal(position["takeProfit"]) if position["takeProfit"] else None),
                stop_loss=(Decimal(position["stopLoss"]) if position["stopLoss"] else None),
                unrealised_pnl=Decimal(position["unrealisedPnl"]),
                cur_realised_pnl=Decimal(position["curRealisedPnl"]),
                cum_realised_pnl=Decimal(position["cumRealisedPnl"]),
                position_status=position["positionStatus"],
                created_time=datetime.fromtimestamp(int(position["createdTime"]) / 1000),
                updated_time=(
                    datetime.fromtimestamp(int(position["updatedTime"]) / 1000) if position["updatedTime"] else None
                ),
            )
            logger.info(f'add position {symbol} size {position["size"]}')

    except Exception as ex:
        log_error_with_traceback(logger, ex)
        raise


async def handle_positions(
    positions_data: dict,
) -> None:
    if not positions_data.get("data"):
        return

    positions = positions_data["data"]

    async with sessionmanager.session() as db:
        await refresh_positions_in_db(db, positions)
    logger.info("positions updated with ws")
