from eth_typing import ChecksumAddress
import requests
from common_types import Chain
from exceptions import UnsupportedToken

TOKEN_TO_BINANCE_SYMBOL = {
  Chain.SEPOLIA: {
    '0xaA8E23Fb1079EA71e0a56F48a2aA51851D8433D0': 'ETHUSDT'
  },
  Chain.MUMBAI: {
    '0x1fdE0eCc619726f4cD597887C9F3b4c8740e19e2': 'MATICUSDT'
  },
  Chain.BASE_GOERLI: {
    # TODO: there is no direct pair for COMP-ETH. Need to handle such cases.
  },
  Chain.POLYGON: {
    '0xc2132D05D31c914a87C6611C10748AEb04B58e8F': 'MATICUSDT',
  },
  Chain.BASE: {
    '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913': 'ETHUSDC',
  }
}


def get_token_to_eth_price(chain: Chain, token_address: ChecksumAddress) -> float:
  try:
    binance_symbol = TOKEN_TO_BINANCE_SYMBOL[chain][token_address]
  except KeyError as e:
    raise UnsupportedToken(f'Unsupported token {token_address} on chain {str(chain)}') from e
  
  response = requests.get(f'https://api.binance.com/api/v3/avgPrice?symbol={binance_symbol}').json()
  price = float(response['price'])
  return price