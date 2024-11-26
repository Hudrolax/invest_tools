import aiohttp
import logging
import json
from core.config import ALERT_BOT_ENDPOINT, ALERT_BOT_TOKEN


logger = logging.getLogger("alert_bot_connector")


async def send_alert(chat_id: int, text: str) -> None:
    params = dict(chat_id=chat_id, text=text)
    headers = {
        "TOKEN": ALERT_BOT_TOKEN,
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        async with session.request(
            "POST", ALERT_BOT_ENDPOINT, json=params, headers=headers
        ) as response:
            response.raise_for_status()  # проверка на ошибки HTTP
            text = await response.text()
            logger.debug(f"raw response: {text}")
            return json.loads(text)
