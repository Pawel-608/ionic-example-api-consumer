import asyncio
import base64
import os
import time

import httpx
from dotenv import load_dotenv
from solana.rpc.api import Client
from solders.solders import Keypair, Transaction

load_dotenv()
PRIVATE_KEY = os.environ.get("PRIVATE_KEY")

wallet = Keypair.from_base58_string(PRIVATE_KEY)


async def send_ionic_quote_request(client: httpx.AsyncClient):
    url = "https://dev.api.ionic.trade/api/v1/trade/quote"
    params = {
        "trader": str(wallet.pubkey()),
        "mint_in": "So11111111111111111111111111111111111111112",
        "mint_out": "2i2ckTX6UNJ5j1ztELACe99epTFMvQGtnVjeFH9Ypump",
        "amount_in": "0.00001",
        "slippage": 0.8
    }
    response = await client.post(url, json=params)
    response.raise_for_status()
    return response.json()


async def send_ionic_execute_request(client: httpx.AsyncClient, signed_transaction: str):
    url = "https://dev.api.ionic.trade/api/v1/trade/execute"

    data = {
        "signed_transaction": signed_transaction,
    }
    response = await client.post(url, json=data)
    response.raise_for_status()
    return response.json()


async def main():
    rpc = Client("https://api.mainnet-beta.solana.com")
    blockhash = rpc.get_latest_blockhash()

    async with httpx.AsyncClient(timeout=120) as client:
        start_time = time.perf_counter()
        response = await send_ionic_quote_request(client)

        print(response)

        elapsed = time.perf_counter() - start_time

        print(f"Quote received in {elapsed:.4f} seconds")

        tx_b64 = response.get('transaction')

        tx = Transaction.from_bytes(base64.b64decode(tx_b64))
        tx.sign(keypairs=[wallet], recent_blockhash=blockhash.value.blockhash)

        exec_start_time = time.perf_counter()

        response = await send_ionic_execute_request(client, base64.b64encode(bytes(tx)).decode())

        print(response)
        print(f"Execution alone took {(time.perf_counter() - exec_start_time):.4f} seconds")
        print(f"Full quote and execution took {(time.perf_counter() - start_time):.4f} seconds")


if __name__ == "__main__":
    asyncio.run(main())
