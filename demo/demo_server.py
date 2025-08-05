import asyncio
import pathlib
import time
from collections import defaultdict
from contextlib import asynccontextmanager

import httpx
import msgspec
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from loguru import logger
from starlette.responses import HTMLResponse

from demo.const import IONIC_API_HOST, IONIC_API_KEY
from demo.ionic_data_feed import ionic_data_feed
from demo.messages import WsMessage, INVALID_MESSAGE, PairSubscribe

pair_to_client = defaultdict(set)
hot_tokens: set[str] = set()
hot_tokens_lock = asyncio.Lock()

# Track which pair each websocket is subscribed to
client_to_pair = {}


def disconnect_client(ws: WebSocket):
    to_remove = []

    for pair, clients in pair_to_client.items():
        clients.discard(ws)
        if not clients:
            to_remove.append(pair)

    for pair in to_remove:
        del pair_to_client[pair]

    # Remove from client_to_pair as well
    client_to_pair.pop(ws, None)


async def update_hot_tokens_periodically():
    global hot_tokens
    while True:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://{IONIC_API_HOST}/api/v1/hot_tokens",
                    headers={"x-api-key": IONIC_API_KEY}
                )
                resp.raise_for_status()
                tokens = set(resp.json())
                async with hot_tokens_lock:
                    hot_tokens.clear()
                    hot_tokens.update(tokens)
                    hot_tokens.add('6AJcP7wuLwmRYLBNbi825wgguaPsWzPBEHcHndpRpump')
                    hot_tokens.add('Dz9mQ9NzkBcCsuGPFJ3r1bS4wgqKMHBPiVuniW8Mbonk')
                    hot_tokens.add('73NhQ8pJPnusH7qkLvXMsG6qwzuFBMqDST65viDkbonk')
                logger.info(f"Updated hot tokens: {tokens}")
        except Exception as e:
            logger.exception(f"Failed to update hot tokens: {e}")
        await asyncio.sleep(30)


async def broadcast_data():
    while True:
        try:
            async for event in ionic_data_feed():
                message = msgspec.json.encode(event).decode()

                disconnected = []

                for client in pair_to_client.get(event.pair, []):
                    try:
                        await client.send_text(message)
                    except:
                        disconnected.append(client)

                for client in disconnected:
                    disconnect_client(client)
        except Exception as e:
            logger.exception(f"Error occurred in listener: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    broadcast_task = asyncio.create_task(broadcast_data())
    hot_tokens_task = asyncio.create_task(update_hot_tokens_periodically())
    logger.info("Started broadcast data and hot tokens update tasks")

    yield

    logger.info("Cancelling broadcast data and hot tokens update tasks")

    broadcast_task.cancel()
    hot_tokens_task.cancel()

    try:
        await broadcast_task
    except asyncio.CancelledError:
        logger.info("Broadcast data task cancelled")
    try:
        await hot_tokens_task
    except asyncio.CancelledError:
        logger.info("Hot tokens update task cancelled")


app = FastAPI(lifespan=lifespan)
HERE = pathlib.Path(__file__).parent


@app.get("/", response_class=HTMLResponse)
async def read_index():
    html_path = HERE / "index.html"
    return HTMLResponse(html_path.read_text(), status_code=200)


@app.get("/api/v1/hot_tokens")
async def hot_tokens_endpoint() -> list[str]:
    async with hot_tokens_lock:
        return list(hot_tokens)


@app.get("/api/v1/chart")
async def chart_endpoint(
        base_token: str,
        quote_token: str,
):
    """
    Proxy endpoint to fetch chart data from Ionic API with fixed interval, limit, and to_timestamp (now).
    Only allows chart for hot tokens.
    """

    IONIC_API_URL = f"https://{IONIC_API_HOST}/api/v1/chart"

    interval = 15
    limit = 500
    to_timestamp = int(time.time())

    params = {
        "base_token": base_token,
        "quote_token": quote_token,
        "to_timestamp": to_timestamp,
        "limit": limit,
        "interval": interval,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            IONIC_API_URL,
            params=params,
            headers={"X-API-key": IONIC_API_KEY},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            msg = await websocket.receive_text()

            try:
                parsed_msg = msgspec.json.decode(msg, type=WsMessage)

                match parsed_msg:
                    case PairSubscribe() as pair_subscription:
                        # Only allow subscription to hot tokens
                        async with hot_tokens_lock:
                            if pair_subscription.pair.split("_")[0] not in hot_tokens:
                                await websocket.send_text(
                                    msgspec.json.encode(
                                        {"type": "error", "message": "Subscription only allowed to hot tokens"}
                                    ).decode()
                                )
                                continue
                        # Unsubscribe from previous pair if any
                        prev_pair = client_to_pair.get(websocket)
                        if prev_pair and websocket in pair_to_client[prev_pair]:
                            pair_to_client[prev_pair].discard(websocket)
                            # Clean up empty sets
                            if not pair_to_client[prev_pair]:
                                del pair_to_client[prev_pair]
                        # Subscribe to new pair
                        logger.info(f"Subscribed to pair {pair_subscription.pair}")
                        pair_to_client[pair_subscription.pair].add(websocket)
                        client_to_pair[websocket] = pair_subscription.pair
            except (msgspec.ValidationError, msgspec.DecodeError):
                await websocket.send_text(INVALID_MESSAGE)
    except WebSocketDisconnect:
        disconnect_client(websocket)
        logger.info("WebSocket disconnected")
    except Exception as e:
        disconnect_client(websocket)
        logger.exception(f"Unexpected error: {e}")
