from typing import cast
from eth_typing import ChecksumAddress
from common_types import Chain, ChainConfig
from web3.types import Wei


SEPOLIA_CONFIG = ChainConfig(
  chain=Chain.SEPOLIA,
  router_address=cast(ChecksumAddress, '0x5C66B780240987e5864FE78D5370c0D0De3e8EE0'),
  min_block=4483261,
  rpc='https://eth-sepolia-public.unifra.io',
  priority_fee_wei=Wei(int(1.5 * 10**9)),
)

MUMBAI_CONFIG = ChainConfig(
  chain=Chain.MUMBAI,
  router_address=cast(ChecksumAddress, '0x9f86fAb93F14B98EFe68786606CcF4113C7c1A0b'),
  min_block=41190555,
  rpc='https://rpc.ankr.com/polygon_mumbai',
  priority_fee_wei=Wei(1)
)

ALL_CHAINS_CONFIGS = [
  SEPOLIA_CONFIG,
  MUMBAI_CONFIG,
]

GAS_PER_PAYMENT = 92000
