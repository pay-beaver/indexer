import json
import traceback
from eth_typing import ChecksumAddress
from requests import HTTPError
from common_types import Chain, Subscription
from database import Database
from web3 import AsyncWeb3, AsyncHTTPProvider
import logging

MAX_BLOCK_RANGE = 100

with open("abi/beaver_router.json", 'r') as f:
    BEAVER_ROUTER_ABI = json.loads(f.read())

with open("abi/erc20.json", 'r') as f:
    ERC20_ABI = json.loads(f.read())


class ChainIndexer:
    def __init__(self, chain: Chain, router_address: ChecksumAddress, rpc: str, db: Database, min_block: int):
        self.chain = chain
        self.web3 = AsyncWeb3(AsyncHTTPProvider(rpc))
        self.db = db
        self.min_block = min_block
        self.router = self.web3.eth.contract(address=router_address, abi=BEAVER_ROUTER_ABI)

    async def discover_new_subscriptions(self):
        last_checked_block = self.db.get_last_checked_subscriptions_block(self.chain, self.min_block)
        latest_block = await self.web3.eth.block_number
        logging.info(f"Starting a loop to check new subscription logs for chain {self.chain.name} and router {self.router.address} from block {last_checked_block + 1} to {latest_block}")
        try:
            for from_block in range(last_checked_block + 1, latest_block + 1, MAX_BLOCK_RANGE):
                to_block = min(from_block + MAX_BLOCK_RANGE - 1, latest_block)
                logging.info(f"Checking new subscription logs for chain {self.chain.name} and router {self.router.address} from block {from_block} to {to_block}")
                new_logs = await self.router.events.SubscriptionStarted().get_logs(  # type: ignore
                    fromBlock=from_block,
                    toBlock=to_block,
                )
                for log in new_logs:
                    logging.info(f"Found new subscription log for chain {self.chain.name} and router {self.router.address} at block {log.blockNumber}")
                    token_contract = self.web3.eth.contract(address=log.args.token, abi=ERC20_ABI)
                    decimals = await token_contract.functions.decimals().call()

                    subscription = Subscription(
                        subscription_hash=log.args.subscriptionHash.hex(),
                        chain=self.chain,
                        user_address=log.args.user,
                        merchant_address=log.args.merchant,
                        merchant_domain=log.args.merchantDomain,
                        nonce=log.args.nonce.hex(),
                        token_address=log.args.token,
                        uint_amount=log.args.amount,
                        human_amount=log.args.amount / 10 ** decimals,
                        period=log.args.period,
                        start_ts=log.args.start,
                        payment_period=log.args.paymentPeriod,
                        payments_made=0,
                        terminated=False,
                    )
                    self.db.add_subscription(subscription)
                    logging.info(f"Added new subscription {subscription} for chain {self.chain.name} and router {self.router.address} at block {log.blockNumber}")

                self.db.set_last_checked_subscriptions_block(self.chain, to_block)
                logging.info(f"Finished checking new subscription logs for chain {self.chain.name} and router {self.router.address}")
        except HTTPError:
            # If we got an HTTP error - it's okay, we will check again later
            logging.warning(f"Haven't checked all new subscription logs for chain {self.chain.name} and router {self.router.address} because of an HTTP error: {traceback.format_exc()}")

    async def discover_new_payments(self):
        last_checked_block = self.db.get_last_checked_payments_block(self.chain, self.min_block)
        latest_block = await self.web3.eth.block_number
        logging.info(f"Starting a loop to check new payment logs for chain {self.chain.name} and router {self.router.address} from block {last_checked_block + 1} to {latest_block}")
        try:
            for from_block in range(last_checked_block + 1, latest_block + 1, MAX_BLOCK_RANGE):
                to_block = min(from_block + MAX_BLOCK_RANGE - 1, latest_block)
                logging.info(f"Checking new payment logs for chain {self.chain.name} and router {self.router.address} from block {from_block} to {to_block}")
                new_logs = await self.router.events.PaymentMade().get_logs(  # type: ignore
                    fromBlock=from_block,
                    toBlock=to_block,
                )
                for log in new_logs:
                    self.db.update_payments_made(
                        subscription_hash=log.args.subscriptionHash.hex(),
                        new_payments_made=log.args.paymentNumber,
                    )
                    logging.info(f"Updated payments made for subscription {log.args.subscriptionHash.hex()} to {log.args.paymentNumber} for chain {self.chain.name} and router {self.router.address} at block {log.blockNumber}")
                
                self.db.set_last_checked_payments_block(self.chain, to_block)
            
            logging.info(f"Finished checking new payment logs for chain {self.chain.name} and router {self.router.address}")
        except HTTPError:
            # If we got an HTTP error - it's okay, we will check again later
            logging.warning(f"Haven't checked all new payment logs for chain {self.chain.name} and router {self.router.address} because of an HTTP error: {traceback.format_exc()}")
