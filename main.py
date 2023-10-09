import logging
import os
import traceback
from dotenv import load_dotenv
import asyncio
from eth_typing import ChecksumAddress

from fastapi import FastAPI, HTTPException
from chain_indexer import ChainIndexer
from common_types import Chain
from constants import ALL_CHAINS_CONFIGS

from database import Database

load_dotenv()

db = Database(
    name=os.environ['DB_NAME'],
    user=os.environ['DB_USER'],
    host=os.environ['DB_HOST'],
    password=os.environ['DB_PASSWORD'],
    port=int(os.environ['DB_PORT']),
)

app = FastAPI()

indexers: dict[Chain, ChainIndexer] = {}
for config in ALL_CHAINS_CONFIGS:
    indexers[config.chain] = ChainIndexer(
        chain=config.chain,
        router_address=config.router_address,
        rpc=config.rpc,
        db=db,
        min_block=config.min_block,
    )

async def check_subscriptions():
    for indexer in indexers.values():
        await indexer.discover_new_subscriptions()
        await indexer.discover_new_payments()

async def loop():
    await asyncio.sleep(0.1)  # Allow the rest of the server to start
    while True:
        try:
            await check_subscriptions()
        except Exception:
            logging.error(f"Error while checking subscriptions: {traceback.format_exc()}")
        
        await asyncio.sleep(12)  # Almost no delay in the loop since we want to be checking subscriptions continuously


@app.get('/subscriptions')
async def get_all_subscriptions():
    subs =  db.get_all_subscriptions()
    return [sub.to_json() for sub in subs]


@app.get("/subscriptions/{address}")
async def get_subscriptions_by_Address(address: ChecksumAddress):
    subs = db.get_subscriptions_by_address(address)
    return [sub.to_json() for sub in subs]


@app.get("/subscription/{subscription_hash}")
async def get_subscription_by_hash(subscription_hash: str):
    sub = db.get_subscription_by_hash(subscription_hash)
    if sub is None:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return sub.to_json()


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(loop())
