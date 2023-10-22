from eth_typing import ChecksumAddress
import psycopg2
from contextlib import contextmanager
from threading import Lock

from common_types import Chain, Subscription, SubscriptionLog

with open('db_schema.sql') as f:
    DB_SCHEMA = f.read()


class Database:
    def __init__(self, name: str, user: str, host: str, password: str, port: int):
        self._conn = psycopg2.connect(
            database=name, 
            user=user, 
            host=host,
            password=password,
            port=port,
        )
        self._db_lock = Lock()

        with self.context() as cursor:
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';")
            tables = cursor.fetchall()
            print('tables', tables)
            if len(tables) == 0:
                cursor.execute(DB_SCHEMA)

    @contextmanager
    def context(self):
        with self._db_lock:
            try:
                yield self._conn.cursor()
            except Exception:
                self._conn.rollback()
                raise
            else:
                self._conn.commit()
    
    def drop_all_tables(self):
        with self.context() as cursor:
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';")
            tables = cursor.fetchall()
            for table_name in tables:
                cursor.execute(f'DROP TABLE {table_name[0]} CASCADE')

    def get_last_checked_subscriptions_block(self, chain: Chain, min_block: int) -> int:
        with self.context() as cursor:
            name = f'{chain.name.lower()}_last_checked_subscriptions_block'
            cursor.execute('SELECT value FROM setting WHERE name = %s', (name,))
            result = cursor.fetchone()
            if result is None:
                return min_block
            else:
                return max(min_block, int(result[0]))
    
    def set_last_checked_subscriptions_block(self, chain: Chain, block: int) -> None:
        with self.context() as cursor:
            name = f'{chain.name.lower()}_last_checked_subscriptions_block'
            cursor.execute('INSERT INTO setting (name, value) VALUES (%s, %s) ON CONFLICT(name) DO UPDATE SET name=EXCLUDED.name, value=EXCLUDED.value', (name, block))

    def get_last_checked_payments_block(self, chain: Chain, min_block: int) -> int:
        with self.context() as cursor:
            name = f'{chain.name.lower()}_last_checked_payments_block'
            cursor.execute('SELECT value FROM setting WHERE name = %s', (name,))
            result = cursor.fetchone()
            if result is None:
                return min_block
            else:
                return max(min_block, int(result[0]))
    
    def set_last_checked_payments_block(self, chain: Chain, block: int) -> None:
        with self.context() as cursor:
            name = f'{chain.name.lower()}_last_checked_payments_block'
            cursor.execute('INSERT INTO setting (name, value) VALUES (%s, %s) ON CONFLICT(name) DO UPDATE SET name=EXCLUDED.name, value=EXCLUDED.value', (name, block))

    def get_last_checked_terminations_block(self, chain: Chain, min_block: int) -> int:
        with self.context() as cursor:
            name = f'{chain.name.lower()}_last_checked_terminations_block'
            cursor.execute('SELECT value FROM setting WHERE name = %s', (name,))
            result = cursor.fetchone()
            if result is None:
                return min_block
            else:
                return max(min_block, int(result[0]))
    
    def set_last_checked_terminations_block(self, chain: Chain, block: int) -> None:
        with self.context() as cursor:
            name = f'{chain.name.lower()}_last_checked_terminations_block'
            cursor.execute('INSERT INTO setting (name, value) VALUES (%s, %s) ON CONFLICT(name) DO UPDATE SET name=EXCLUDED.name, value=EXCLUDED.value', (name, block))
    
    def get_initiator_available(self, chain: Chain) -> bool:
        with self.context() as cursor:
            name = f'{chain.name.lower()}_initiator_available'
            cursor.execute('SELECT value FROM setting WHERE name = %s', (name,))
            return cursor.fetchone() is None  # If there is no setting set -- the initiator is NOT stuck and good to go!

    def disable_initiator(self, chain: Chain) -> None:
        with self.context() as cursor:
            name = f'{chain.name.lower()}_initiator_available'
            cursor.execute('INSERT INTO setting (name, value) VALUES (%s, %s) ON CONFLICT(name) DO UPDATE SET name=EXCLUDED.name, value=EXCLUDED.value', (name, 'stuck!!!!!'))

    def add_subscription(self, subscription: Subscription) -> None:
        with self.context() as cursor:
            cursor.execute(
                '''INSERT INTO subscription(
                    hash,
                    chain,
                    user_address,
                    merchant_address,
                    subscription_id,
                    user_id,
                    merchant_domain,
                    product,
                    token_address,
                    token_symbol,
                    token_decimals,
                    uint_amount,
                    human_amount,
                    period,
                    start_ts,
                    payment_period,
                    payments_made,
                    terminated,
                    initiator
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (hash) DO NOTHING''',
                subscription.to_db(),
            )

    def update_payments_made(self, subscription_hash: str, new_payments_made: int):
        with self.context() as cursor:
            cursor.execute('UPDATE subscription SET payments_made = GREATEST(payments_made, %s) WHERE hash = %s', (new_payments_made, subscription_hash))
    
    def terminate_subscription(self, subscription_hash: str):
        with self.context() as cursor:
            cursor.execute('UPDATE subscription SET terminated = TRUE WHERE hash = %s', (subscription_hash,))
    
    def get_all_subscriptions(self) -> list[Subscription]:
        with self.context() as cursor:
            cursor.execute('SELECT * FROM subscription')
            return [Subscription.from_db(row) for row in cursor.fetchall()]

    def get_subscriptions_by_user(self, address: ChecksumAddress) -> list[Subscription]:
        with self.context() as cursor:
            cursor.execute('SELECT * FROM subscription WHERE user_address = %s', (address,))
            return [Subscription.from_db(row) for row in cursor.fetchall()]
    
    def get_subscriptions_by_merchant(self, merchant_domain: str) -> list[Subscription]:
        with self.context() as cursor:
            cursor.execute('SELECT * FROM subscription WHERE merchant_domain = %s', (merchant_domain,))
            return [Subscription.from_db(row) for row in cursor.fetchall()]
    
    def get_subscriptions_by_merchant_and_user(self, merchant_domain: str, userid: str) -> list[Subscription]:
        with self.context() as cursor:
            cursor.execute("SELECT * FROM subscription WHERE merchant_domain = %s AND user_id = %s", (merchant_domain, userid))
            return [Subscription.from_db(row) for row in cursor.fetchall()]
    
    def get_subscription_by_merchant_and_subscriptionid(self, merchant_domain: str, subscription_id: str) -> Subscription | None:
        with self.context() as cursor:
            cursor.execute('SELECT * FROM subscription WHERE merchant_domain = %s AND subscription_id=%s ORDER BY start_ts LIMIT 1', (merchant_domain, subscription_id))
            result = cursor.fetchone()
            if result is None:
                return None
            
            return Subscription.from_db(result)
    
    def get_subscription_by_hash(self, subscription_hash: str) -> Subscription | None:
        with self.context() as cursor:
            cursor.execute('SELECT * FROM subscription WHERE hash = %s', (subscription_hash,))
            row = cursor.fetchone()
            if row is None:
                return None
            return Subscription.from_db(row)
    
    def get_payable_subscriptions(self, chain: Chain, timestamp: int, initiator: ChecksumAddress) -> list[Subscription]:
        with self.context() as cursor:
            cursor.execute(
                '''SELECT * FROM subscription WHERE
                chain = %s AND terminated = FALSE AND
                %s > start_ts + period * payments_made AND
                %s < start_ts + period * payments_made + payment_period AND
                initiator = %s AND
                %s >= (SELECT GREATEST(MAX(timestamp), 0) FROM subscription_log WHERE
                    subscription_hash = subscription.hash AND
                    log_type = 'payment-issue' AND
                    payment_number = subscription.payments_made + 1
                ) + %s
                ''',
                (
                    chain.name.lower(),
                    timestamp,
                    timestamp,
                    initiator,
                    timestamp,
                    60 * 60 * 24, # Attempt payments every 24 hours in case of issues 
                ),
            )
            return [Subscription.from_db(row) for row in cursor.fetchall()]

    def add_subscription_log(self, log: SubscriptionLog):
        with self.context() as cursor:
            cursor.execute(
                'INSERT INTO subscription_log(log_type, subscription_hash, payment_number, message, timestamp) VALUES (%s, %s, %s, %s, %s)',
                log.to_db(),
            )

    def get_subscription_logs(self, subscription_hash: str) -> list[SubscriptionLog]:
        with self.context() as cursor:
            cursor.execute('SELECT * FROM subscription_log WHERE subscription_hash=%s', (subscription_hash,))
            return [SubscriptionLog.from_db(row) for row in cursor.fetchall()]
