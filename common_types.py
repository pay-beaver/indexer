from enum import Enum
from typing import Any, Literal, NamedTuple
import logging
import sys
from dotenv import load_dotenv
from eth_typing import ChecksumAddress, HexStr
from web3.types import Wei
from api_models import SerializedProduct, SerializedSubscription

from utils import ts_now

# Load env variables and setup logging here, so that it's available everywhere
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(pathname)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler("beaver-indexer.log"),
        logging.StreamHandler(sys.stdout),
    ],
    force=True,
)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.info('Starting beaver indexer')

class Chain(Enum):
    SEPOLIA = 11155111
    MUMBAI = 80001
    BASE_GOERLI = 84531
    POLYGON = 137
    BASE = 8453

    def __str__(self) -> str:
        if self == Chain.SEPOLIA:
            return 'sepolia'
        
        if self == Chain.MUMBAI:
            return 'polygon-mumbai'
        
        if self == Chain.BASE_GOERLI:
            return 'base-goerli'
        
        if self == Chain.POLYGON:
            return 'polygon'

        if self == Chain.BASE:
            return 'base'

        raise AssertionError(f'Unknown chain {self}')
    
    @staticmethod
    def load(serialized_chain: str) -> 'Chain':
        for chain in Chain:
            if serialized_chain == str(chain):
                return chain

        raise AssertionError(f'Unknown chain {serialized_chain}')

class Product(NamedTuple):
    product_hash: HexStr
    chain: Chain
    merchant_address: ChecksumAddress
    token_address: ChecksumAddress
    token_symbol: str
    token_decimals: int
    uint_amount: int
    human_amount: float
    period: int
    free_trial_length: int
    payment_period: int
    metadata_cid: str
    merchant_domain: str
    product_name: str

    def to_json(self) -> SerializedProduct:
        return SerializedProduct(
            product_hash=self.product_hash,
            chain=str(self.chain),
            merchant_address=self.merchant_address,
            token_address=self.token_address,
            token_symbol=self.token_symbol,
            token_decimals=self.token_decimals,
            uint_amount=self.uint_amount,
            human_amount=self.human_amount,
            period=self.period,
            free_trial_length=self.free_trial_length,
            payment_period=self.payment_period,
            metadata_cid=self.metadata_cid,
            merchant_domain=self.merchant_domain,
            product_name=self.product_name,
        )
    
    def to_db(self) -> dict[str, Any]:
        return {
            'hash': self.product_hash,
            'chain': str(self.chain),
            'merchant_address': self.merchant_address,
            'token_address': self.token_address,
            'token_symbol': self.token_symbol,
            'token_decimals': self.token_decimals,
            'uint_amount': self.uint_amount,
            'human_amount': self.human_amount,
            'period': self.period,
            'free_trial_length': self.free_trial_length,
            'payment_period': self.payment_period,
            'metadata_cid': self.metadata_cid,
            'merchant_domain': self.merchant_domain,
            'product_name': self.product_name,
        }
    
    @staticmethod
    def from_db(row: tuple) -> 'Product':
        return Product(
            product_hash=row[0],
            chain=Chain.load(row[1]),
            merchant_address=row[2],
            token_address=row[3],
            token_symbol=row[4],
            token_decimals=row[5],
            uint_amount=row[6],
            human_amount=row[7],
            period=row[8],
            free_trial_length=row[9],
            payment_period=row[10],
            metadata_cid=row[11],
            merchant_domain=row[12],
            product_name=row[13],
        )


class Subscription(NamedTuple):
    subscription_hash: HexStr
    product: Product
    user_address: ChecksumAddress
    start_ts: int
    payments_made: int
    terminated: bool
    metadata_cid: str
    subscription_id: str | None
    user_id: str | None
        
    @property
    def next_payment_at(self) -> int:
        return self.start_ts + self.product.period * self.payments_made

    @property
    def status(self) -> str:
        if self.terminated:
            return 'terminated'
        
        current_timestamp = ts_now()
        next_payment_ts = self.next_payment_at
        if current_timestamp > next_payment_ts + self.product.payment_period:
            return 'expired'
        
        if current_timestamp > next_payment_ts:
            return 'pending'
        
        return 'paid'
    
    @property
    def is_active(self) -> bool:
        # If subscription was terminated, but the billing period has not passed yet,
        # we consider it active.
        current_timestamp = ts_now()
        next_payment_ts = self.next_payment_at

        if current_timestamp > next_payment_ts + self.product.payment_period:
            return False

        return True
        
    def to_json(self) -> SerializedSubscription:
        return SerializedSubscription(
            subscription_hash=self.subscription_hash,
            product=self.product.to_json(),
            user_address=self.user_address,
            start_ts=self.start_ts,
            payments_made=self.payments_made,
            terminated=self.terminated,
            metadata_cid=self.metadata_cid,
            subscription_id=self.subscription_id,
            user_id=self.user_id,
            status=self.status,
            is_active=self.is_active,
            next_payment_at=self.next_payment_at,
        )

    def to_db(self) -> dict[str, Any]:
        return {
            'hash': self.subscription_hash,
            'product_hash': self.product.product_hash,
            'user_address': self.user_address,
            'start_ts': self.start_ts,
            'payments_made': self.payments_made,
            'terminated': self.terminated,
            'metadata_cid': self.metadata_cid,
            'subscription_id': self.subscription_id,
            'user_id': self.user_id,
        }

    @staticmethod
    def from_db(row: tuple) -> 'Subscription':
        return Subscription(
            subscription_hash=row[0],
            product=row[1],
            user_address=row[2],
            start_ts=row[3],
            payments_made=row[4],
            terminated=row[5],
            metadata_cid=row[6],
            subscription_id=row[7],
            user_id=row[8],
        )


class ChainConfig(NamedTuple):
    chain: Chain
    router_address: ChecksumAddress
    rpc: str
    min_block: int
    priority_fee_wei: Wei
    needs_poa_middleware: bool


SubscriptionActionType = Literal["payment-issue", "payment-made"]

class SubscriptionLog(NamedTuple):
    log_id: int
    log_type: SubscriptionActionType
    subscription_hash: HexStr
    payment_number: int
    message: str
    timestamp: int

    def to_db(self) -> dict[str, Any]:
        return {
            'log_type': self.log_type,
            'subscription_hash': self.subscription_hash,
            'payment_number': self.payment_number,
            'message': self.message,
            'timestamp': self.timestamp,
        }
    
    @staticmethod
    def from_db(row: tuple) -> 'SubscriptionLog':
        return SubscriptionLog(
            log_id=row[0],
            log_type=row[1],
            subscription_hash=row[2],
            payment_number=row[3],
            message=row[4],
            timestamp=row[5],
        )
    
    def to_json(self) -> dict[str, Any]:
        return {
            'log_type': self.log_type,
            'subscription_hash': self.subscription_hash,
            'payment_number': self.payment_number,
            'message': self.message,
            'timestamp': self.timestamp,
        }
