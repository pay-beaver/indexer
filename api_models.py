from pydantic import BaseModel

class SerializedSubscription(BaseModel):
    subscription_hash: str
    chain: str
    user_address: str
    merchant_address: str
    subscription_id: str | None
    merchant_domain: str
    product: str
    token_address: str
    token_symbol: str
    token_decimals: int
    uint_amount: int
    human_amount: float
    # TODO: there is a discrepancy. Gateway accepts period as a human string and here we return it in seconds.
    period: int
    start_ts: int
    payment_period: int
    payments_made: int
    terminated: bool
    initiator: str
    status: str
    is_active: bool
    next_payment_at: int
