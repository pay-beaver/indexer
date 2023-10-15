import logging
import os
import traceback
from dotenv import load_dotenv
import asyncio
from eth_typing import ChecksumAddress

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from web3 import Web3

from chain_indexer import ChainIndexer
from common_types import Chain
from constants import ALL_CHAINS_CONFIGS
from eth_utils.address import to_checksum_address
from eth_abi.abi import encode


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

indexers: dict[Chain, ChainIndexer] = {}
for config in ALL_CHAINS_CONFIGS:
    indexers[config.chain] = ChainIndexer(
        chain=config.chain,
        router_address=config.router_address,
        rpc=config.rpc,
        db=db,
        min_block=config.min_block,
        initiator_private_key=os.environ['INITIATOR_PRIVATE_KEY'],
        priority_fee_wei=config.priority_fee_wei,
    )

async def check_subscriptions():
    for indexer in indexers.values():
        await indexer.discover_new_subscriptions()
        await indexer.discover_new_payments()
        await indexer.discover_new_terminations()
        await indexer.pay_payable_subscriptions()

async def loop():
    await asyncio.sleep(0.1)  # Allow the rest of the server to start
    while True:
        try:
            await check_subscriptions()
        except Exception:
            logging.error(f"Error while checking subscriptions: {traceback.format_exc()}")
        
        await asyncio.sleep(12)  # Almost no delay in the loop since we want to be checking subscriptions continuously


@app.get('/healthcheck')
async def healthcheck():
    return 'OK'


@app.get('/subscriptions/all')
async def get_all_subscriptions():
    subs = db.get_all_subscriptions()
    return [sub.to_json() for sub in subs]


@app.get("/subscriptions/user/{address}")
async def get_subscriptions_by_address(address: str):
    try:
        validated_address = to_checksum_address(address)
    except Exception:
        raise HTTPException(status_code=400, detail=f'{address} is not a valid address')

    subs = db.get_subscriptions_by_address(validated_address)
    return [sub.to_json() for sub in subs]


@app.get("/subscription/{subscription_hash}")
async def get_subscription_by_hash(subscription_hash: str):
    sub = db.get_subscription_by_hash(subscription_hash)
    if sub is None:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return sub.to_json()


@app.get("/subscription/{subscription_hash}/logs")
async def get_subscription_logs(subscription_hash: str):
    logs = db.get_subscription_logs(subscription_hash)
    return [log.to_json() for log in logs]


class HashSubscriptionData(BaseModel):
    merchant_address: str
    userid: str
    merchant_domain: str
    product: str
    nonce: str
    token_address: str
    uint_amount: int
    period: int
    free_trial_length: int
    payment_period: int
    initiator: str


@app.post("/subscription/hash")
async def hash_subscription(data: HashSubscriptionData):
    try:
        validated_merchant_address = to_checksum_address(data.merchant_address)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Merchant address must be a valid crypto address. {str(e)}')
    
    if len(data.userid) > 32:
        raise HTTPException(status_code=400, detail="User id length must not exceed 32 symbols")
    
    if len(data.merchant_domain) > 32:
        raise HTTPException(status_code=400, detail="Merchant domain length must not exceed 32 symbols")
    
    if len(data.product) > 32:
        raise HTTPException(status_code=400, detail="Product length must not exceed 32 symbols")
    
    if len(data.nonce) > 32:
        raise HTTPException(status_code=400, detail="Nonce length must not exceed 32 symbols")
    
    try:
        validated_token_address = to_checksum_address(data.token_address)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Token address must be a valid crypto address. {str(e)}')
    
    if data.uint_amount < 0 or data.period < 0 or data.free_trial_length < 0 or data.payment_period < 0:
        raise HTTPException(status_code=400, detail="uint_amount, period, free_trial_length, payment_period must be greater than zero")

    try:
        validated_initiator_address = to_checksum_address(data.token_address)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Initiator address must be a valid crypto address. {str(e)}')
    
    encoded_packed_data = encode([
        'address',
        'byte32',
        'bytes32',
        'bytes32',
        'bytes32',
        'address',
        'uint256',
        'uint256',
        'uint256',
        'uint256',
        'address',
    ], [
        validated_merchant_address,
        data.userid.encode(encoding='ascii', errors='replace'),
        data.merchant_domain.encode(encoding='ascii', errors='replace'),
        data.product.encode(encoding='ascii', errors='replace'),
        data.nonce.encode(encoding='ascii', errors='replace'),
        validated_token_address,
        data.uint_amount,
        data.period,
        data.free_trial_length,
        data.payment_period,
        validated_initiator_address
    ])

    keccak = Web3().solidity_keccak('bytes[]', encoded_packed_data)
    return keccak


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(loop())
