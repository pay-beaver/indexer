from enum import Enum
from typing import Any, NamedTuple
import logging
import sys
from eth_typing import ChecksumAddress, HexStr

# Setup logging here, so that it's available in tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(pathname)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler("beaver-watcher.log"),
        logging.StreamHandler(sys.stdout),
    ],
    force=True,
)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.info('Starting beaver watcher')

class Chain(Enum):
    SEPOLIA = 11155111
    MUMBAI = 80001


class Subscription(NamedTuple):
    subscription_hash: HexStr
    chain: Chain
    user_address: ChecksumAddress
    merchant_address: ChecksumAddress
    merchant_domain: str
    nonce: HexStr
    token_address: ChecksumAddress
    uint_amount: int
    human_amount: float
    period: int
    start_ts: int
    payment_period: int
    payments_made: int
    terminated: bool

    def to_json(self) -> dict[str, Any]:
        return {
            'subscription_hash': self.subscription_hash,
            'chain': self.chain.name.lower(),
            'user_address': self.user_address,
            'merchant_address': self.merchant_address,
            'merchant_domain': self.merchant_domain,
            'nonce': self.nonce,
            'token_address': self.token_address,
            'uint_amount': self.uint_amount,
            'human_amount': self.human_amount,
            'period': self.period,
            'start_ts': self.start_ts,
            'payment_period': self.payment_period,
            'payments_made': self.payments_made,
            'terminated': self.terminated,
        }


class ChainConfig(NamedTuple):
    chain: Chain
    router_address: ChecksumAddress
    rpc: str
    min_block: int
