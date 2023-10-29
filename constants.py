import os
from typing import cast
from eth_typing import ChecksumAddress
from common_types import Chain, ChainConfig
from web3.types import Wei


SEPOLIA_CONFIG = ChainConfig(
  chain=Chain.SEPOLIA,
  router_address=cast(ChecksumAddress, '0x46a432Ee69881Af9067C23AE7680912245A7fF52'),
  min_block=4588724,
  rpc='https://eth-sepolia-public.unifra.io',
  priority_fee_wei=Wei(int(1.5 * 10**9)),  # 1.5 gwei
  needs_poa_middleware=False,
)

MUMBAI_CONFIG = ChainConfig(
  chain=Chain.MUMBAI,
  router_address=cast(ChecksumAddress, '0xbE247668C131b913baDa67E76f9cb219EBa8764c'),
  min_block=41793971,
  rpc='https://rpc.ankr.com/polygon_mumbai',
  priority_fee_wei=Wei(int(1.5 * 10**9)),  # 1.5 gwei
  needs_poa_middleware=True,
)

ALL_CHAINS_CONFIGS = [
  SEPOLIA_CONFIG,
  MUMBAI_CONFIG,
]

GAS_PER_PAYMENT = 92000
IPFS_VERSION = bytes.fromhex('1220')  # Current and only IPFS version

PINATA_API_KEY = os.environ['PINATA_API_KEY']
PINATA_BASE_URL = os.environ['PINATA_BASE_URL']
