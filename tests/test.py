import os
from unittest.mock import patch
import pytest
from common_types import Chain
from constants import SEPOLIA_CONFIG
from database import Database
from chain_indexer import ChainIndexer
from dotenv import load_dotenv

from utils import ts_now

load_dotenv()

# Not owned by anybody
RANDOM_PRIVATE_KEY = 'af638f6032676be0068cd44e713c28fc5d4c984e77e24943b9cde1defcd57a9b'

async def mock_and_discover_subscriptions(sepolia_indexer: ChainIndexer):
    # Mock from_block and to_block
    from_block = 4483278
    to_block = from_block + 537  # 537 us just some random number to have some range and multiple calls to get_logs

    sepolia_indexer.db.set_last_checked_subscriptions_block(chain=Chain.SEPOLIA, block=from_block)

    async def to_block_mock():
        return to_block
    
    to_block_patch = patch('web3.eth.AsyncEth.block_number', new_callable=to_block_mock)

    with to_block_patch:
        await sepolia_indexer.discover_new_subscriptions()


async def mock_and_siscover_payments(sepolia_indexer: ChainIndexer):
    # Mock from_block and to_block
    from_block = 4483278
    to_block = from_block + 537  # 537 us just some random number to have some range and multiple calls to get_logs
    sepolia_indexer.db.set_last_checked_payments_block(chain=Chain.SEPOLIA, block=from_block)

    async def to_block_mock():
        return to_block
    
    to_block_patch = patch('web3.eth.AsyncEth.block_number', new_callable=to_block_mock)

    with to_block_patch:
        await sepolia_indexer.discover_new_payments()


@pytest.mark.asyncio
async def test_discover_new_subscriptions():
    db = Database(
        name='indexer_test', 
        user='beaver', 
        host='localhost',
        password='password',
        port=5432,
    )
    db.drop_all_tables()

    db = Database(  # Re-initialize to create tables
        name='indexer_test', 
        user='beaver', 
        host='localhost',
        password='password',
        port=5432,
    )

    sepolia_indexer = ChainIndexer(
        chain=Chain.SEPOLIA,
        rpc=SEPOLIA_CONFIG.rpc,
        min_block=0,
        router_address=SEPOLIA_CONFIG.router_address,
        db=db,
        initiator_private_key=RANDOM_PRIVATE_KEY,
        priority_fee_wei=SEPOLIA_CONFIG.priority_fee_wei,
    )
    await mock_and_discover_subscriptions(sepolia_indexer)

    

@pytest.mark.asyncio
async def test_discover_new_payments():
    db = Database(
        name='indexer_test', 
        user='beaver', 
        host='localhost',
        password='password',
        port=5432,
    )
    db.drop_all_tables()

    db = Database(  # Re-initialize to create tables
        name='indexer_test', 
        user='beaver', 
        host='localhost',
        password='password',
        port=5432,
    )

    sepolia_indexer = ChainIndexer(
        chain=Chain.SEPOLIA,
        rpc=SEPOLIA_CONFIG.rpc,
        min_block=0,
        router_address=SEPOLIA_CONFIG.router_address,
        db=db,
        initiator_private_key=RANDOM_PRIVATE_KEY,
        priority_fee_wei=SEPOLIA_CONFIG.priority_fee_wei,
    )
    await mock_and_discover_subscriptions(sepolia_indexer)
    await mock_and_siscover_payments(sepolia_indexer)


@pytest.mark.asyncio
async def test_pay():
    db = Database(
        name='indexer_test', 
        user='beaver', 
        host='localhost',
        password='password',
        port=5432,
    )
    db.drop_all_tables()

    db = Database(  # Re-initialize to create tables
        name='indexer_test', 
        user='beaver', 
        host='localhost',
        password='password',
        port=5432,
    )
    sepolia_indexer = ChainIndexer(
        chain=Chain.SEPOLIA,
        rpc=SEPOLIA_CONFIG.rpc,
        min_block=0,
        router_address=SEPOLIA_CONFIG.router_address,
        db=db,
        initiator_private_key=os.environ['INITIATOR_PRIVATE_KEY'],
        priority_fee_wei=SEPOLIA_CONFIG.priority_fee_wei,
    )
    await mock_and_discover_subscriptions(sepolia_indexer)
    await mock_and_siscover_payments(sepolia_indexer)
    await sepolia_indexer.pay_payable_subscriptions()
