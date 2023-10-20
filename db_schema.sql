CREATE TABLE setting(
  name TEXT NOT NULL PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE subscription(
  hash TEXT NOT NULL PRIMARY KEY,
  chain TEXT NOT NULL,
  user_address TEXT NOT NULL,
  merchant_address TEXT NOT NULL,
  subscription_id TEXT, -- nullable
  user_id TEXT, -- nullable
  merchant_domain TEXT, -- nullable
  product TEXT, -- nullable
  token_address TEXT NOT NULL,
  token_symbol TEXT NOT NULL,
  token_decimals BIGINT NOT NULL,
  uint_amount NUMERIC(32, 0) NOT NULL, -- 10^18 * token amount = a big number of digits can happen
  human_amount FLOAT NOT NULL,
  period BIGINT NOT NULL,
  start_ts BIGINT NOT NULL,
  payment_period BIGINT NOT NULL,
  payments_made BIGINT NOT NULL,
  terminated BOOLEAN NOT NULL,
  initiator TEXT NOT NULL
);

CREATE TABLE subscription_log(
  log_id SERIAL PRIMARY KEY,
  log_type TEXT NOT NULL,
  subscription_hash TEXT NOT NULL REFERENCES subscription(hash) ON DELETE CASCADE,
  payment_number BIGINT NOT NULL,
  message TEXT NOT NULL,
  timestamp BIGINT NOT NULL
);
