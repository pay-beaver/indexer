from enum import Enum
from typing import Any, Literal, NamedTuple
import logging
import sys
from eth_typing import ChecksumAddress, HexStr
from web3.types import Wei
from api_models import SerializedSubscription

from utils import ts_now

# Setup logging here, so that it's available in tests
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


class Subscription(NamedTuple):
    subscription_hash: HexStr
    chain: Chain
    user_address: ChecksumAddress
    merchant_address: ChecksumAddress
    subscription_id: str | None
    user_id: str | None
    merchant_domain: str
    product: str
    token_address: ChecksumAddress
    token_symbol: str
    token_decimals: int
    uint_amount: int
    human_amount: float
    period: int
    start_ts: int
    payment_period: int
    payments_made: int
    terminated: bool
    initiator: ChecksumAddress
        
    @property
    def next_payment_at(self) -> int:
        return self.start_ts + self.period * self.payments_made

    @property
    def status(self) -> str:
        if self.terminated:
            return 'terminated'
        
        current_timestamp = ts_now()
        next_payment_ts = self.next_payment_at
        if current_timestamp > next_payment_ts + self.payment_period:
            return 'expired'
        
        if current_timestamp > next_payment_ts:
            return 'pending'
        
        return 'paid'
    
    @property
    def is_active(self) -> bool:
        # If subscription was terminated, but the billing cycle has not passed yet,
        # we consider it active.
        current_timestamp = ts_now()
        next_payment_ts = self.next_payment_at

        if current_timestamp > next_payment_ts + self.payment_period:
            return False

        return True
        
    def to_json(self) -> SerializedSubscription:
        return SerializedSubscription(
            subscription_hash=self.subscription_hash,
            chain=self.chain.name.lower(),
            user_address=self.user_address,
            merchant_address=self.merchant_address,
            subscription_id=self.subscription_id,
            merchant_domain=self.merchant_domain,
            product=self.product,
            token_address=self.token_address,
            token_symbol=self.token_symbol,
            token_decimals=self.token_decimals,
            uint_amount=self.uint_amount,
            human_amount=self.human_amount,
            period=self.period,
            start_ts=self.start_ts,
            payment_period=self.payment_period,
            payments_made=self.payments_made,
            terminated=self.terminated,
            initiator=self.initiator,
            status=self.status,
            is_active=self.is_active,
            next_payment_at=self.next_payment_at,
        )

    def to_db(self) -> tuple:
        return (
            self.subscription_hash,
            self.chain.name.lower(),
            self.user_address,
            self.merchant_address,
            self.subscription_id,
            self.user_id,
            self.merchant_domain,
            self.product,
            self.token_address,
            self.token_symbol,
            self.token_decimals,
            self.uint_amount,
            self.human_amount,
            self.period,
            self.start_ts,
            self.payment_period,
            self.payments_made,
            self.terminated,
            self.initiator,
        )

    @staticmethod
    def from_db(row: tuple) -> 'Subscription':
        return Subscription(
            subscription_hash=row[0],
            chain=Chain[row[1].upper()],
            user_address=row[2],
            merchant_address=row[3],
            subscription_id=row[4],
            user_id=row[5],
            merchant_domain=row[6],
            product=row[7],
            token_address=row[8],
            token_symbol=row[9],
            token_decimals=row[10],
            uint_amount=row[11],
            human_amount=row[12],
            period=row[13],
            start_ts=row[14],
            payment_period=row[15],
            payments_made=row[16],
            terminated=row[17],
            initiator=row[18],
        )


class ChainConfig(NamedTuple):
    chain: Chain
    router_address: ChecksumAddress
    rpc: str
    min_block: int
    priority_fee_wei: Wei


SubscriptionActionType = Literal["payment-issue", "payment-made"]

class SubscriptionLog(NamedTuple):
    log_id: int
    log_type: SubscriptionActionType
    subscription_hash: HexStr
    payment_number: int
    message: str
    timestamp: int

    def to_db(self) -> tuple:
        return (
            self.log_type,
            self.subscription_hash,
            self.payment_number,
            self.message,
            self.timestamp,
        )
    
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
