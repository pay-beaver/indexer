from typing import cast
from eth_typing import ChecksumAddress
from common_types import Chain, ChainConfig
from web3.types import Wei


SEPOLIA_CONFIG = ChainConfig(
  chain=Chain.SEPOLIA,
  router_address=cast(ChecksumAddress, '0xe9265fa920552fE26DffCe55C5606B27eceE9c89'),
  min_block=4528086,
  rpc='https://eth-sepolia-public.unifra.io',
  priority_fee_wei=Wei(int(1.5 * 10**9)),
)

MUMBAI_CONFIG = ChainConfig(
  chain=Chain.MUMBAI,
  router_address=cast(ChecksumAddress, '0x9f86fAb93F14B98EFe68786606CcF4113C7c1A0b'),
  min_block=411905550000,
  rpc='https://rpc.ankr.com/polygon_mumbai',
  priority_fee_wei=Wei(1)
)

ALL_CHAINS_CONFIGS = [
  SEPOLIA_CONFIG,
  MUMBAI_CONFIG,
]

GAS_PER_PAYMENT = 92000
