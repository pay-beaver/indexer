CREATE TABLE setting(
  name TEXT NOT NULL PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE subscription(
  hash TEXT NOT NULL PRIMARY KEY,
  chain TEXT NOT NULL,
  user_address TEXT NOT NULL,
  merchant_address TEXT NOT NULL,
  merchant_domain TEXT NOT NULL,
  product TEXT NOT NULL,
  nonce TEXT NOT NULL,
  token_address TEXT NOT NULL,
  token_symbol TEXT NOT NULL,
  token_decimals INTEGER NOT NULL,
  uint_amount INTEGER NOT NULL,
  human_amount FLOAT NOT NULL,
  period INTEGER NOT NULL,
  start_ts INTEGER NOT NULL,
  payment_period INTEGER NOT NULL,
  payments_made INTEGER NOT NULL,
  terminated BOOLEAN NOT NULL,
  initiator TEXT NOT NULL
);

CREATE TABLE subscription_log(
  log_id SERIAL PRIMARY KEY,
  log_type TEXT NOT NULL,
  subscription_hash TEXT NOT NULL REFERENCES subscription(hash) ON DELETE CASCADE,
  payment_number INTEGER NOT NULL,
  message TEXT NOT NULL,
  timestamp INTEGER NOT NULL
);
