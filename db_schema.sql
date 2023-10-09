CREATE TABLE settings(
  name TEXT NOT NULL PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE subscription(
  hash TEXT NOT NULL PRIMARY KEY,
  chain TEXT NOT NULL,
  user_address TEXT NOT NULL,
  merchant_address TEXT NOT NULL,
  merchant_domain TEXT NOT NULL,
  nonce TEXT NOT NULL,
  token_address TEXT NOT NULL,
  uint_amount INTEGER NOT NULL,
  human_amount FLOAT NOT NULL,
  period INTEGER NOT NULL,
  start_ts INTEGER NOT NULL,
  payment_period INTEGER NOT NULL,
  payments_made INTEGER NOT NULL,
  terminated BOOLEAN NOT NULL
);