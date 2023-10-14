from eth_typing import ChecksumAddress
import requests
from common_types import Chain
from exceptions import UnsupportedToken

TOKEN_TO_BINANCE_SYMBOL = {
  Chain.SEPOLIA: {
    '0xaA8E23Fb1079EA71e0a56F48a2aA51851D8433D0': 'ETHUSDT'
  }
}


def get_token_to_eth_price(chain: Chain, token_address: ChecksumAddress) -> float:
  try:
    binance_symbol = TOKEN_TO_BINANCE_SYMBOL[chain][token_address]
  except KeyError as e:
    raise UnsupportedToken(f'Unsupported token {token_address} on chain {chain.name.lower()}') from e
  
  response = requests.get(f'https://api.binance.com/api/v3/avgPrice?symbol={binance_symbol}').json()
  price = float(response['price'])
  return price