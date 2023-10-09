from typing import cast
from eth_typing import ChecksumAddress
from common_types import Chain, ChainConfig


SEPOLIA_CONFIG = ChainConfig(
  chain=Chain.SEPOLIA,
  router_address=cast(ChecksumAddress, '0x249b13D5d31cdF4a6EB536F1B94B497dF9238f2d'),
  min_block=4455613,
  rpc='https://eth-sepolia-public.unifra.io',
)

MUMBAI_CONFIG = ChainConfig(
  chain=Chain.MUMBAI,
  router_address=cast(ChecksumAddress, '0x9f86fAb93F14B98EFe68786606CcF4113C7c1A0b'),
  min_block=41008770,
  rpc='https://rpc.ankr.com/polygon_mumbai',
)

ALL_CHAINS_CONFIGS = [
  SEPOLIA_CONFIG,
  MUMBAI_CONFIG,
]
