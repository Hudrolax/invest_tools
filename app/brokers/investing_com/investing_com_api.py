import aiohttp
from bs4 import BeautifulSoup
from decimal import Decimal
import logging
from utils import async_traceback_errors


logger = logging.getLogger(__name__)


@async_traceback_errors(logger)
async def get_rate(symbol: str):
    url = "https://www.investing.com/currencies/" + symbol
    async with aiohttp.ClientSession() as session:
        async with session.request("GET", url) as response:
            try:
                response.raise_for_status()  # проверка на ошибки HTTP
                text = await response.text()
                soup = BeautifulSoup(text, "html.parser")
                price_tag = soup.find("div", {"data-test": "instrument-price-last"})
                return Decimal(price_tag.text) if price_tag else None
            except Exception as ex:
                logger.error(str(ex))
