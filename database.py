from eth_typing import ChecksumAddress
import psycopg2
import os
from contextlib import contextmanager
from threading import Lock

from common_types import Chain, Subscription

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
                cursor.execute(f'DROP TABLE {table_name[0]}')

    def get_last_checked_subscriptions_block(self, chain: Chain, min_block: int) -> int:
        with self.context() as cursor:
            name = f'{chain.name.lower()}_last_checked_subscriptions_block'
            cursor.execute('SELECT value FROM settings WHERE name = %s', (name,))
            result = cursor.fetchone()
            if result is None:
                return min_block
            else:
                return max(min_block, int(result[0]))
    
    def set_last_checked_subscriptions_block(self, chain: Chain, block: int) -> None:
        with self.context() as cursor:
            name = f'{chain.name.lower()}_last_checked_subscriptions_block'
            cursor.execute('INSERT INTO settings (name, value) VALUES (%s, %s) ON CONFLICT(name) DO UPDATE SET name=EXCLUDED.name, value=EXCLUDED.value', (name, block))

    def get_last_checked_payments_block(self, chain: Chain, min_block: int) -> int:
        with self.context() as cursor:
            name = f'{chain.name.lower()}_last_checked_payments_block'
            cursor.execute('SELECT value FROM settings WHERE name = %s', (name,))
            result = cursor.fetchone()
            if result is None:
                return min_block
            else:
                return max(min_block, int(result[0]))
    
    def set_last_checked_payments_block(self, chain: Chain, block: int) -> None:
        with self.context() as cursor:
            name = f'{chain.name.lower()}_last_checked_payments_block'
            cursor.execute('INSERT INTO settings (name, value) VALUES (%s, %s) ON CONFLICT(name) DO UPDATE SET name=EXCLUDED.name, value=EXCLUDED.value', (name, block))

    def add_subscription(self, subscription: Subscription) -> None:
        with self.context() as cursor:
            cursor.execute(
                'INSERT INTO subscription(hash, chain, user_address, merchant_address, merchant_domain, nonce, token_address, uint_amount, human_amount, period, start_ts, payment_period, payments_made, terminated) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (hash) DO NOTHING',
                (
                    subscription.subscription_hash,
                    subscription.chain.name.lower(),
                    subscription.user_address,
                    subscription.merchant_address,
                    subscription.merchant_domain,
                    subscription.nonce,
                    subscription.token_address,
                    subscription.uint_amount,
                    subscription.human_amount,
                    subscription.period,
                    subscription.start_ts,
                    subscription.payment_period,
                    subscription.payments_made,
                    subscription.terminated,
                ),
            )

    def update_payments_made(self, subscription_hash: str, new_payments_made: int):
        with self.context() as cursor:
            cursor.execute('UPDATE subscription SET payments_made = %s WHERE hash = %s', (new_payments_made, subscription_hash))
    
    def get_all_subscriptions(self) -> list[Subscription]:
        with self.context() as cursor:
            cursor.execute('SELECT * FROM subscription')
            return [Subscription(*row) for row in cursor.fetchall()]

    def get_subscriptions_by_address(self, address: ChecksumAddress) -> list[Subscription]:
        with self.context() as cursor:
            cursor.execute('SELECT * FROM subscription WHERE user_address = %s', (address,))
            return [Subscription(*row) for row in cursor.fetchall()]
    
    def get_subscription_by_hash(self, subscription_hash: str) -> Subscription | None:
        with self.context() as cursor:
            cursor.execute('SELECT * FROM subscription WHERE hash = %s', (subscription_hash,))
            result = cursor.fetchone()
            if result is None:
                return None
            return Subscription(*result)