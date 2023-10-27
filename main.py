import io
import logging
import os
import traceback
from dotenv import load_dotenv
import asyncio

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import requests
from api_models import SerializedSubscription

from chain_indexer import ChainIndexer
from common_types import Chain
from constants import ALL_CHAINS_CONFIGS, PINATA_API_KEY
from eth_utils.address import to_checksum_address

from database import Database
from utils import sort_subscriptions


db = Database(
    name=os.environ['DB_NAME'],
    user=os.environ['DB_USER'],
    host=os.environ['DB_HOST'],
    password=os.environ['DB_PASSWORD'],
    port=int(os.environ['DB_PORT']),
)

app_description = '''
For `merchant_domain` use your domain. For example `paybeaver.xyz`.

The most useful for you is probably the `/is_active` endpoint. Using it you can check whether a certain user has an active subscription or not.
'''

app = FastAPI(
    title='Beaver Crypto Subscriptions',
    summary='A simple service to accept crypto payments for subscriptions.',
    description=app_description,
    version='0.1',
    contact={
        'name': 'Alexey Nebolsin',
        'email': 'alexey@nebols.in',
        'X/Twitter': '@nebolax',
    }
)

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
        needs_poa_middleware=config.needs_poa_middleware,
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


@app.get("/is_active/merchant/{merchant_domain}/userid/{userid}")
async def does_user_have_an_active_subscription(merchant_domain: str, userid: str) -> bool:
    subs = db.get_subscriptions_by_merchant_and_user(merchant_domain=merchant_domain, userid=userid)
    return any([s.is_active for s in subs])


@app.get("/subscriptions/merchant/{merchant_domain}")
async def get_subscriptions_by_merchant(merchant_domain: str) -> list[SerializedSubscription]:
    subs = db.get_subscriptions_by_merchant(merchant_domain=merchant_domain)
    return [sub.to_json() for sub in sort_subscriptions(subs)]


@app.get("/subscriptions/merchant/{merchant_domain}/userid/{userid}")
async def get_subscriptions_by_merchant_and_userid(merchant_domain: str, userid: str) -> list[SerializedSubscription]:
    subs = db.get_subscriptions_by_merchant_and_user(merchant_domain=merchant_domain, userid=userid)
    return [sub.to_json() for sub in sort_subscriptions(subs)]


@app.get("/subscription/merchant/{merchant_domain}/id/{subscription_id}")
async def get_subscription_by_merchant_and_subscriptionid(merchant_domain: str, subsciption_id: str) -> SerializedSubscription:
    sub = db.get_subscription_by_merchant_and_subscriptionid(
        merchant_domain=merchant_domain,
        subscription_id=subsciption_id,
    )

    if sub is None:
        raise HTTPException(status_code=404, detail='No such subscription')

    return sub.to_json()


@app.get("/subscription/{subscription_hash}")
async def get_subscription_by_hash(subscription_hash: str) -> SerializedSubscription:
    sub = db.get_subscription_by_hash(subscription_hash)
    if sub is None:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return sub.to_json()


@app.get("/subscriptions/user/{address}")
async def get_subscriptions_by_user(address: str) -> list[SerializedSubscription]:
    try:
        validated_address = to_checksum_address(address)
    except Exception:
        raise HTTPException(status_code=400, detail=f'{address} is not a valid address')

    subs = db.get_subscriptions_by_user(validated_address)
    return [sub.to_json() for sub in sort_subscriptions(subs)]


@app.get('/subscriptions/all')
async def get_all_subscriptions() -> list[SerializedSubscription]:
    subs = db.get_all_subscriptions()
    return [sub.to_json() for sub in sort_subscriptions(subs)]


@app.get("/subscription/{subscription_hash}/logs")
async def get_subscription_logs(subscription_hash: str):
    logs = db.get_subscription_logs(subscription_hash)
    return [log.to_json() for log in logs]


@app.post('/save_metadata')
async def save_metadata(request: Request) -> str:
    metadata_bytes = await request.body()
    
    # Check if the metadata is already cached in our database
    decoded_metadata = metadata_bytes.decode(encoding='utf-8', errors='replace')
    cached_ipfs_cid = db.get_metadata_ipfs_cid_by_content(decoded_metadata)
    if cached_ipfs_cid is not None:
        return cached_ipfs_cid
    
    # Otherwise save the data on IPFS
    metadata_stream = io.BytesIO(metadata_bytes)
    response = requests.post(
        url='https://api.pinata.cloud/pinning/pinFileToIPFS',
        headers={
            'Authorization': f'Bearer {PINATA_API_KEY}'
        },
        files={'file': metadata_stream}
    )
    ipfs_cid: str = response.json()['IpfsHash']
    db.store_metadata(
        ipfs_cid=ipfs_cid,
        content=decoded_metadata,
    )
    return ipfs_cid


@app.get('/healthcheck')
async def healthcheck():
    return 'OK'


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(loop())
