import os
from typing import cast
from eth_typing import ChecksumAddress
from common_types import Chain, ChainConfig
from web3.types import Wei


SEPOLIA_CONFIG = ChainConfig(
  chain=Chain.SEPOLIA,
  router_address=cast(ChecksumAddress, '0x748FC43a4218f28CB6CD99F60c30Fcc09eA4E5f9'),
  min_block=4642995,
  rpc='https://eth-sepolia-public.unifra.io',
  needs_poa_middleware=False,
)

MUMBAI_CONFIG = ChainConfig(
  chain=Chain.MUMBAI,
  router_address=cast(ChecksumAddress, '0x748FC43a4218f28CB6CD99F60c30Fcc09eA4E5f9'),
  min_block=42085814,
  rpc='https://rpc.ankr.com/polygon_mumbai',
  needs_poa_middleware=True,
)

BASE_GOERLI_CONFIG = ChainConfig(
  chain=Chain.BASE_GOERLI,
  router_address=cast(ChecksumAddress, '0x748FC43a4218f28CB6CD99F60c30Fcc09eA4E5f9'),
  min_block=12051590,
  rpc='https://goerli.base.org',
  needs_poa_middleware=True,
)

POLYGON_CONFIG = ChainConfig(
  chain=Chain.POLYGON,
  router_address=cast(ChecksumAddress, '0x748FC43a4218f28CB6CD99F60c30Fcc09eA4E5f9'),
  min_block=49624479,
  rpc='https://polygon.llamarpc.com',
  needs_poa_middleware=True,
)

BASE_CONFIG = ChainConfig(
  chain=Chain.BASE,
  router_address=cast(ChecksumAddress, '0x27bFF737b405a4C540001BDF9CC184c3392b1733'),
  min_block=6255026,
  rpc='https://mainnet.base.org',
  needs_poa_middleware=True,
)


ALL_CHAINS_CONFIGS = [
  SEPOLIA_CONFIG,
  MUMBAI_CONFIG,
  BASE_GOERLI_CONFIG,
  POLYGON_CONFIG,
  BASE_CONFIG
]

GAS_PER_PAYMENT = 92000
IPFS_VERSION = bytes.fromhex('1220')  # Current and only IPFS version

PINATA_API_KEY = os.environ['PINATA_API_KEY']
PINATA_BASE_URL = os.environ['PINATA_BASE_URL']
