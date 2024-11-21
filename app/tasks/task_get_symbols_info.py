import asyncio
import logging

from decimal import Decimal
from datetime import datetime

from brokers.bybit import BYBIT_BROKERS
from brokers.bybit.bybit_api import (
    get_symbols_info,
    get_fee_rate,
)
from models.broker import BrokerORM
from models.symbol import SymbolORM
from models.chart_settings import ChartSettingsORM
from models.user import UserORM
from core.db import DatabaseSessionManager
from utils import async_traceback_errors

logger = logging.getLogger(__name__)


@async_traceback_errors(logger=logger)
async def task_get_symbols_info(
    stop_event: asyncio.Event,
    sessionmaker: DatabaseSessionManager,
) -> None:
    logger = logging.getLogger("task_get_symbols_info")
    logger.info(f"start task: {logger.name}")
    while not stop_event.is_set():
        try:
            for broker in BYBIT_BROKERS:
                await asyncio.sleep(1)
                symbols = await get_symbols_info(broker)  # type: ignore
                fee_rates = await get_fee_rate(broker)  # type: ignore
                async with sessionmaker.session() as db:
                    hudrolax_user = await UserORM.get_by_username(
                        db, username="Hudrolax"
                    )
                    broker_instance = await BrokerORM.get_by_name(db, broker)
                    for symbol in symbols:
                        takerFeeRate = None
                        makerFeeRate = None
                        for fee_rate in fee_rates:
                            if fee_rate.get("symbol") == symbol["symbol"]:
                                takerFeeRate = Decimal(fee_rate["takerFeeRate"])
                                makerFeeRate = Decimal(fee_rate["makerFeeRate"])
                                break

                        symbol_instance = await SymbolORM.get_or_create(
                            db, name=symbol["symbol"], broker_id=broker_instance.id
                        )
                        chart_settings = await ChartSettingsORM.get_or_create(
                            db,
                            user_id=hudrolax_user.id,
                            symbol_id=symbol_instance.id,
                            taker_fee_rate=takerFeeRate,
                            maker_fee_rate=makerFeeRate,
                        )
                        await ChartSettingsORM.update(
                            db,
                            id=chart_settings.id,
                            taker_fee_rate=takerFeeRate,
                            maker_fee_rate=makerFeeRate,
                        )
                        await SymbolORM.update(
                            db,
                            id=symbol_instance.id,
                            contract_type=symbol.get("contractType"),
                            status=symbol.get("status"),
                            base_coin=symbol.get("baseCoin"),
                            quote_coin=symbol.get("quoteCoin"),
                            launch_time=(
                                datetime.fromtimestamp(
                                    int(symbol.get("launchTime", 0)) / 1000
                                )
                                if symbol.get("launchTime")
                                else None
                            ),
                            delivery_time=(
                                datetime.fromtimestamp(
                                    int(symbol.get("deliveryTime", 0)) / 1000
                                )
                                if symbol.get("deliveryTime")
                                else None
                            ),
                            delivery_fee_rate=(
                                Decimal(symbol.get("deliveryFeeRate", 0))
                                if symbol.get("deliveryFeeRate")
                                else None
                            ),
                            price_scale=(
                                Decimal(symbol.get("priceScale", 0))
                                if symbol.get("priceScale")
                                else None
                            ),
                            min_leverage=(
                                Decimal(symbol["leverageFilter"].get("minLeverage", 0))
                                if symbol.get("leverageFilter")
                                and symbol["leverageFilter"].get("minLeverage")
                                else None
                            ),
                            max_leverage=(
                                Decimal(symbol["leverageFilter"].get("maxLeverage", 0))
                                if symbol.get("leverageFilter")
                                and symbol["leverageFilter"].get("maxLeverage")
                                else None
                            ),
                            leverage_step=(
                                Decimal(symbol["leverageFilter"].get("leverageStep", 0))
                                if symbol.get("leverageFilter")
                                and symbol["leverageFilter"].get("leverageStep")
                                else None
                            ),
                            min_price=(
                                Decimal(symbol["priceFilter"].get("minPrice", 0))
                                if symbol.get("priceFilter")
                                and symbol["priceFilter"].get("minPrice")
                                else None
                            ),
                            max_price=(
                                Decimal(symbol["priceFilter"].get("maxPrice", 0))
                                if symbol.get("priceFilter")
                                and symbol["priceFilter"].get("maxPrice")
                                else None
                            ),
                            tick_size=(
                                Decimal(symbol["priceFilter"].get("tickSize", 0))
                                if symbol.get("priceFilter")
                                and symbol["priceFilter"].get("tickSize")
                                else None
                            ),
                            max_order_qty=(
                                Decimal(symbol["lotSizeFilter"].get("maxOrderQty", 0))
                                if symbol.get("lotSizeFilter")
                                and symbol["lotSizeFilter"].get("maxOrderQty")
                                else None
                            ),
                            max_mkt_order_qty=(
                                Decimal(
                                    symbol["lotSizeFilter"].get("maxMktOrderQty", 0)
                                )
                                if symbol.get("lotSizeFilter")
                                and symbol["lotSizeFilter"].get("maxMktOrderQty")
                                else None
                            ),
                            min_order_qty=(
                                Decimal(symbol["lotSizeFilter"].get("minOrderQty", 0))
                                if symbol.get("lotSizeFilter")
                                and symbol["lotSizeFilter"].get("minOrderQty")
                                else None
                            ),
                            qty_step=(
                                Decimal(symbol["lotSizeFilter"].get("qtyStep", 0))
                                if symbol.get("lotSizeFilter")
                                and symbol["lotSizeFilter"].get("qtyStep")
                                else None
                            ),
                            min_notional_value=(
                                Decimal(
                                    symbol["lotSizeFilter"].get("minNotionalValue", 0)
                                )
                                if symbol.get("lotSizeFilter")
                                and symbol["lotSizeFilter"].get("minNotionalValue")
                                else None
                            ),
                            unified_margin_trade=symbol.get("unifiedMarginTrade"),
                            funding_interval=(
                                int(symbol.get("fundingInterval", 0))
                                if symbol.get("fundingInterval")
                                else None
                            ),
                            settle_coin=symbol.get("settleCoin"),
                            copy_trading=symbol.get("copyTrading"),
                            upper_funding_rate=(
                                Decimal(symbol.get("upperFundingRate", 0))
                                if symbol.get("upperFundingRate")
                                else None
                            ),
                            lower_funding_rate=(
                                Decimal(symbol.get("lowerFundingRate", 0))
                                if symbol.get("lowerFundingRate")
                                else None
                            ),
                        )

            await asyncio.sleep(86400)
        except Exception as ex:
            logger.error(f"Error in task_get_positions: {str(ex)}")
            raise
