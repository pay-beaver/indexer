from pydantic import BaseModel

class SerializedProduct(BaseModel):
    product_hash: str
    chain: str
    merchant_address: str
    token_address: str
    token_symbol: str
    token_decimals: int
    uint_amount: int
    human_amount: float
    period: int
    free_trial_length: int
    payment_period: int
    metadata_hash: str
    merchant_domain: str
    product_name: str

class SerializedSubscription(BaseModel):
    subscription_hash: str
    product: SerializedProduct
    user_address: str
    start_ts: int
    payments_made: int
    terminated: bool
    metadata_hash: str
    subscription_id: str | None
    user_id: str | None
    status: str
    is_active: bool
    next_payment_at: int
