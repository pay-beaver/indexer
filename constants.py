from typing import cast
from eth_typing import ChecksumAddress
from common_types import Chain, ChainConfig
from web3.types import Wei


SEPOLIA_CONFIG = ChainConfig(
  chain=Chain.SEPOLIA,
  router_address=cast(ChecksumAddress, '0xcfA22C9BF50F200F07482b6176bC306f7f9e5aA5'),
  min_block=4545984,
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
