import os
from typing import cast
from eth_typing import ChecksumAddress
from common_types import Chain, ChainConfig
from web3.types import Wei


SEPOLIA_CONFIG = ChainConfig(
  chain=Chain.SEPOLIA,
  router_address=cast(ChecksumAddress, '0x97a64798E1CB5B34c5868aA1F19758831F13eBf4'),
  min_block=4572689,
  rpc='https://eth-sepolia-public.unifra.io',
  priority_fee_wei=Wei(int(1.5 * 10**9)),  # 1.5 gwei
  needs_poa_middleware=False,
)

MUMBAI_CONFIG = ChainConfig(
  chain=Chain.MUMBAI,
  router_address=cast(ChecksumAddress, '0x9CdB06a9689C07a8834B3B5E1209C3cF1E7fC5E4'),
  min_block=41702880,
  rpc='https://rpc.ankr.com/polygon_mumbai',
  priority_fee_wei=Wei(int(1.5 * 10**9)),  # 1.5 gwei
  needs_poa_middleware=True,
)

ALL_CHAINS_CONFIGS = [
  SEPOLIA_CONFIG,
  MUMBAI_CONFIG,
]

GAS_PER_PAYMENT = 92000
PINATA_BASE_URL = os.environ['PINATA_BASE_URL']
