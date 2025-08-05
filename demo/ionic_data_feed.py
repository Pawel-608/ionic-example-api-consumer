import asyncio
from typing import AsyncIterable

import msgspec
import websockets
from loguru import logger

from demo.const import IONIC_API_HOST, IONIC_API_KEY


class Trade(msgspec.Struct, tag="trade"):
    slot: int
    timestamp: int
    main_signature: str
    trader: str
    pair: str  # pair is ordered alphabetically
    mint_in: str
    mint_out: str
    tokens_in: str
    tokens_out: str
    base_price: str  # base is first token from pair in alphabetical order
    base_mcap: str  # base is first token from pair in alphabetical order
    quote_price: str  # quote is second token from pair in alphabetical order
    quote_mcap: str  # quote is second token from pair in alphabetical order
    ui_platform: str
    protocol: str


async def ionic_data_feed() -> AsyncIterable[Trade]:
    while True:
        try:
            logger.info("Connecting to Ionic WebSocket stream...")

            async with websockets.connect(
                    f"wss://{IONIC_API_HOST}/ws",
                    additional_headers={"x-api-key": IONIC_API_KEY}
            ) as websocket:
                logger.info("Connected to Ionic WebSocket")
                try:
                    while True:
                        try:
                            yield msgspec.json.decode(await websocket.recv(), type=Trade)
                        except msgspec.ValidationError:
                            pass
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("WebSocket connection closed, reconnecting...")
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.exception(f"Error in data stream: {e}")
                    await asyncio.sleep(1)
        except Exception as e:
            logger.exception(f"Error connecting to WebSocket: {e}")
            await asyncio.sleep(1)
