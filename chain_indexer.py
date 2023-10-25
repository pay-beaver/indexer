import json
import traceback
from typing import Any, cast
from eth_typing import ChecksumAddress
from requests import HTTPError
from common_types import Chain, Product, Subscription, SubscriptionLog
from database import Database
from web3 import AsyncWeb3, AsyncHTTPProvider
from web3.types import Wei
from eth_account.signers.local import LocalAccount
import logging
from web3.exceptions import TimeExhausted
from price_oracle import get_token_to_eth_price


from utils import ts_now

MAX_LOGS_BLOCK_RANGE = 100

FIRST_PAYMENT_GAS = 110000
GAS_PER_PAYMENT = 92000


with open("abi/beaver_router.json", 'r') as f:
    BEAVER_ROUTER_ABI = json.loads(f.read())

with open("abi/erc20.json", 'r') as f:
    ERC20_ABI = json.loads(f.read())


class ChainIndexer:
    def __init__(
            self,
            chain: Chain,
            router_address: ChecksumAddress,
            rpc: str,
            db: Database,
            min_block: int,
            initiator_private_key: str,
            priority_fee_wei: Wei
    ) -> None:
        self.chain = chain
        self.web3 = AsyncWeb3(AsyncHTTPProvider(rpc))
        self.db = db
        self.min_block = min_block
        self.router = self.web3.eth.contract(address=router_address, abi=BEAVER_ROUTER_ABI)
        self.account: LocalAccount = self.web3.eth.account.from_key(initiator_private_key)
        self.priority_fee_wei = priority_fee_wei
    
    def get_metadata_by_raw_metadata(self, metadata_raw: bytes, description: str) -> dict[str, Any] | None:
        # First byte is the version of metadata encoding. Currently
        # there is only one encoding, so we skip it.
        metadata_partial_hash = metadata_raw[1:].hex()
        product_metadata = self.db.get_metadata_by_partial_hash(metadata_partial_hash)
        if product_metadata is None:
            logging.error(f"No metadata was found in the database for metadata partial hash {metadata_partial_hash} for {description} for chain {self.chain.name} and router {self.router.address}")
            return None

        try:
            metadata_dict: dict = json.loads(product_metadata)
        except Exception:
            logging.error(f"Could not load json metadata {product_metadata} for {description} for chain {self.chain.name} and router {self.router.address}. {traceback.format_exc()}")
            return None

        return metadata_dict

    async def discover_new_subscriptions(self):
        last_checked_block = self.db.get_last_checked_subscriptions_block(self.chain, self.min_block)
        latest_block = await self.web3.eth.block_number
        logging.info(f"Starting a loop to check new subscription logs for chain {self.chain.name} and router {self.router.address} from block {last_checked_block + 1} to {latest_block}")
        try:
            for from_block in range(last_checked_block + 1, latest_block + 1, MAX_LOGS_BLOCK_RANGE):
                to_block = min(from_block + MAX_LOGS_BLOCK_RANGE - 1, latest_block)
                logging.info(f"Checking new subscription logs for chain {self.chain.name} and router {self.router.address} from block {from_block} to {to_block}")
                new_logs = await self.router.events.SubscriptionStarted().get_logs(  # type: ignore
                    fromBlock=from_block,
                    toBlock=to_block,
                )
                for log in new_logs:
                    logging.info(f"Found new subscription log for chain {self.chain.name} and router {self.router.address} at block {log.blockNumber}")
                    subscription_hash = log.args.subscriptionHash.hex()
                    product_hash_bytes = log.args.productHash
                    product_hash_hex = product_hash_bytes.hex()
                    user_address = log.args.user
                    start_ts = log.args.start
                    subscription_metadata_raw = log.args.subscriptionMetadata

                    product = self.db.get_product_by_hash(product_hash_hex)
                    if product is None:
                        product_raw = await self.router.functions.products(product_hash_bytes).call()
                        (
                            merchant_address,
                            token_address,
                            uint_amount,
                            period,
                            free_trial_length,
                            payment_period,
                            product_metadata_raw,
                        ) = product_raw

                        token_contract = self.web3.eth.contract(address=token_address, abi=ERC20_ABI)
                        token_decimals = await token_contract.functions.decimals().call()
                        token_symbol = await token_contract.functions.symbol().call()
                        
                        
                        product_metadata_dict = self.get_metadata_by_raw_metadata(
                            metadata_raw=product_metadata_raw,
                            description=str(product_raw),
                        )
                        if product_metadata_dict is None:
                            continue  # Error was already logged in get_metadata_by_raw_metadata

                        try:
                            merchant_domain = product_metadata_dict['merchantDomain']
                            product_name = product_metadata_dict['productName']
                        except KeyError as e:
                            logging.error(f"No {str(e)} was specified in metadata {product_metadata_dict} for new subscription log {log} for chain {self.chain.name} and router {self.router.address}")
                            continue

                        product = Product(
                            product_hash=product_hash_hex,
                            chain=self.chain,
                            merchant_address=merchant_address,
                            token_address=token_address,
                            token_symbol=token_symbol,
                            token_decimals=token_decimals,
                            uint_amount=uint_amount,
                            human_amount=uint_amount / 10 ** token_decimals,
                            period=period,
                            free_trial_length=free_trial_length,
                            payment_period=payment_period,
                            metadata_hash=product_metadata_raw.hex(),
                            merchant_domain=merchant_domain,
                            product_name=product_name,
                        )

                        self.db.add_product(product)
                        logging.info(f"Added product {product} for chain {self.chain.name} and router {self.router.address}")

                    subscription_metadata_dict = self.get_metadata_by_raw_metadata(
                        metadata_raw=subscription_metadata_raw,
                        description=f'Subscription {str(subscription_hash)}',
                    ) or {}  # subscription metadata is optional
   
                    subscription = Subscription(
                        subscription_hash=subscription_hash,
                        product=product,
                        user_address=user_address,
                        start_ts=start_ts,
                        payments_made=0,
                        terminated=False,
                        metadata_hash=subscription_metadata_raw.hex(),
                        subscription_id=subscription_metadata_dict.get('subscriptionId'),
                        user_id=subscription_metadata_dict.get('userId'),
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
            for from_block in range(last_checked_block + 1, latest_block + 1, MAX_LOGS_BLOCK_RANGE):
                to_block = min(from_block + MAX_LOGS_BLOCK_RANGE - 1, latest_block)
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

    async def discover_new_terminations(self):
        last_checked_block = self.db.get_last_checked_terminations_block(self.chain, self.min_block)
        latest_block = await self.web3.eth.block_number
        logging.info(f"Starting a loop to check new termination logs for chain {self.chain.name} and router {self.router.address} from block {last_checked_block + 1} to {latest_block}")
        try:
            for from_block in range(last_checked_block + 1, latest_block + 1, MAX_LOGS_BLOCK_RANGE):
                to_block = min(from_block + MAX_LOGS_BLOCK_RANGE - 1, latest_block)
                logging.info(f"Checking new termination logs for chain {self.chain.name} and router {self.router.address} from block {from_block} to {to_block}")
                new_logs = await self.router.events.SubscriptionTerminated().get_logs(  # type: ignore
                    fromBlock=from_block,
                    toBlock=to_block,
                )
                for log in new_logs:
                    self.db.terminate_subscription(
                        subscription_hash=log.args.subscriptionHash.hex(),
                    )
                    logging.info(f"Marked subscription {log.args.subscriptionHash.hex()} as terminated for chain {self.chain.name} and router {self.router.address} at block {log.blockNumber}")
                
                self.db.set_last_checked_terminations_block(self.chain, to_block)
            
            logging.info(f"Finished checking new termination logs for chain {self.chain.name} and router {self.router.address}")
        except HTTPError:
            # If we got an HTTP error - it's okay, we will check again later
            logging.warning(f"Haven't checked all new termination logs for chain {self.chain.name} and router {self.router.address} because of an HTTP error: {traceback.format_exc()}")
    
    async def calculate_compensation_amount_human(self, token_address: ChecksumAddress, gas: int) -> tuple[Wei, float]:
        token_to_eth_price = get_token_to_eth_price(chain=self.chain, token_address=token_address)
        base_fee_wei = await self.web3.eth.gas_price
        # multiplying by 1.2 to get some reserve against base fee fluctionations
        max_fee_wei = (base_fee_wei * 1.2) + self.priority_fee_wei
        eth_fee = gas * max_fee_wei / 1e18
        token_fee = eth_fee * token_to_eth_price
        return Wei(int(max_fee_wei)), token_fee

    async def pay_payable_subscriptions(self):
        logging.info(f'Checking payable subscriptions on chain {self.chain.name} and router {self.router.address}')
        if not self.db.get_initiator_available(self.chain):
            logging.critical(f'The initiator is stuck on chain {self.chain.name} and router {self.router.address}!')
            return  # The initiator is stuck. Needs to be resolved manually ASAP!!!

        payable_subscriptions = self.db.get_payable_subscriptions(self.chain, ts_now(), self.account.address)
        logging.info(f'Got {len(payable_subscriptions)} subscriptions to attempt payments for  on chain {self.chain.name} and router {self.router.address}')
        for subscription in payable_subscriptions:
            payment_number = subscription.payments_made + 1
            logging.info(f'Attempting payment {payment_number} for subscription {subscription} on chain {self.chain.name} and router {self.router.address}')

            token_contract = self.web3.eth.contract(address=subscription.product.token_address, abi=ERC20_ABI)
            user_balance_uint = await token_contract.functions.balanceOf(subscription.user_address).call()
            if user_balance_uint < subscription.product.uint_amount:
                logging.error(f"Error while attempting payment for subscription {subscription.subscription_hash} for chain {self.chain.name} and router {self.router.address}: user only has {user_balance_uint / 10 ** subscription.product.token_decimals} tokens while {subscription.product.human_amount} is required to make a payment.")
                # TODO: notify merchant and user about the problem.
                self.db.add_subscription_log(SubscriptionLog(
                    log_id=-1,  # assigned at the db level
                    log_type='payment-issue',
                    subscription_hash=subscription.subscription_hash,
                    payment_number=payment_number,
                    message=f'Could not pay the subscription due to: user only has {user_balance_uint / 10 ** subscription.product.token_decimals} tokens while {subscription.product.human_amount} is required to make a payment.',
                    timestamp=ts_now(),
                ))
                continue

            allowance_uint = await token_contract.functions.allowance(subscription.user_address, self.router.address).call()
            if allowance_uint < subscription.product.uint_amount:
                logging.error(f"Error while attempting payment for subscription {subscription.subscription_hash} for chain {self.chain.name} and router {self.router.address}: allowance is onlt {user_balance_uint / 10 ** subscription.product.token_decimals} tokens while {subscription.product.human_amount} is required to make a payment.")
                # TODO: notify merchant and user about the problem.
                self.db.add_subscription_log(SubscriptionLog(
                    log_id=-1,  # assigned at the db level
                    log_type='payment-issue',
                    subscription_hash=subscription.subscription_hash,
                    payment_number=payment_number,
                    message=f'Could not pay the subscription due to: allowance is only {user_balance_uint / 10 ** subscription.product.token_decimals} tokens while {subscription.product.human_amount} is required to make a payment.',
                    timestamp=ts_now(),
                ))
                continue
            
            if payment_number == 1:
                gas = FIRST_PAYMENT_GAS
            else:
                gas = GAS_PER_PAYMENT
            max_fee_wei, compensation_amount = await self.calculate_compensation_amount_human(
                token_address=subscription.product.token_address,
                gas=gas,
            )
            try:
                nonce = await self.web3.eth.get_transaction_count(self.account.address)
                tx_data = await self.router.functions.makePayment(
                    bytes.fromhex(subscription.subscription_hash),
                    int(compensation_amount * 10 ** subscription.product.token_decimals),
                ).build_transaction({
                    'from': self.account.address,
                    'nonce': nonce,
                    'maxPriorityFeePerGas': self.priority_fee_wei,
                    'maxFeePerGas': max_fee_wei,
                    'gas': gas,
                })
                print('tx_data', tx_data)
                signed_txn = self.account.sign_transaction(tx_data)
                tx_hash = await self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)
                logging.info(f'Sent the payment tx with hash {tx_hash} to pay for subscription {subscription.subscription_hash} on chain {self.chain.name} and router {self.router.address}')
            except Exception:
                logging.error(f"Error while attempting payment for subscription {subscription.subscription_hash} for chain {self.chain.name} and router {self.router.address}: {traceback.format_exc()}")
                # TODO: notify merchant and user about the problem.
                self.db.add_subscription_log(SubscriptionLog(
                    log_id=-1,  # assigned at the db level
                    log_type='payment-issue',
                    subscription_hash=subscription.subscription_hash,
                    payment_number=payment_number,
                    message=f'Could not pay the subscription due to: {traceback.format_exc()}',
                    timestamp=ts_now(),
                ))
                continue

            try:
                await self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            except TimeExhausted:
                logging.critical(f"Payment tx {tx_hash} for chain {self.chain.name} and router {self.router.address} has not been added to a block yet. We are stuck!!! Need to resolve this ASAP to continue making payments!!!!!")
                self.db.disable_initiator(self.chain)
            else:
                logging.info(f"Payment tx {tx_hash} for chain {self.chain.name} and router {self.router.address} has been added to a block! We are good to go to make further payments!")
                self.db.update_payments_made(subscription.subscription_hash, payment_number)
                self.db.add_subscription_log(SubscriptionLog(
                    log_id=-1,  # assigned at the db level
                    log_type='payment-made',
                    subscription_hash=subscription.subscription_hash,
                    payment_number=payment_number,
                    message='',  # No need to put anything
                    timestamp=ts_now(),
                ))
