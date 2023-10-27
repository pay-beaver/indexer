from eth_typing import ChecksumAddress
import psycopg2
from contextlib import contextmanager
from threading import Lock

from common_types import Chain, Product, Subscription, SubscriptionLog

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
            name = f'{str(chain)}_last_checked_subscriptions_block'
            cursor.execute('SELECT value FROM setting WHERE name = %s', (name,))
            result = cursor.fetchone()
            if result is None:
                return min_block
            else:
                return max(min_block, int(result[0]))
    
    def set_last_checked_subscriptions_block(self, chain: Chain, block: int) -> None:
        with self.context() as cursor:
            name = f'{str(chain)}_last_checked_subscriptions_block'
            cursor.execute('INSERT INTO setting (name, value) VALUES (%s, %s) ON CONFLICT(name) DO UPDATE SET name=EXCLUDED.name, value=EXCLUDED.value', (name, block))

    def get_last_checked_payments_block(self, chain: Chain, min_block: int) -> int:
        with self.context() as cursor:
            name = f'{str(chain)}_last_checked_payments_block'
            cursor.execute('SELECT value FROM setting WHERE name = %s', (name,))
            result = cursor.fetchone()
            if result is None:
                return min_block
            else:
                return max(min_block, int(result[0]))
    
    def set_last_checked_payments_block(self, chain: Chain, block: int) -> None:
        with self.context() as cursor:
            name = f'{str(chain)}_last_checked_payments_block'
            cursor.execute('INSERT INTO setting (name, value) VALUES (%s, %s) ON CONFLICT(name) DO UPDATE SET name=EXCLUDED.name, value=EXCLUDED.value', (name, block))

    def get_last_checked_terminations_block(self, chain: Chain, min_block: int) -> int:
        with self.context() as cursor:
            name = f'{str(chain)}_last_checked_terminations_block'
            cursor.execute('SELECT value FROM setting WHERE name = %s', (name,))
            result = cursor.fetchone()
            if result is None:
                return min_block
            else:
                return max(min_block, int(result[0]))
    
    def set_last_checked_terminations_block(self, chain: Chain, block: int) -> None:
        with self.context() as cursor:
            name = f'{str(chain)}_last_checked_terminations_block'
            cursor.execute('INSERT INTO setting (name, value) VALUES (%s, %s) ON CONFLICT(name) DO UPDATE SET name=EXCLUDED.name, value=EXCLUDED.value', (name, block))
    
    def get_last_checked_initiators_block(self, chain: Chain, min_block: int) -> int:
        with self.context() as cursor:
            name = f'{str(chain)}_last_checked_initiators_block'
            cursor.execute('SELECT value FROM setting WHERE name = %s', (name,))
            result = cursor.fetchone()
            if result is None:
                return min_block
            else:
                return max(min_block, int(result[0]))

    def set_last_checked_initiators_block(self, chain: Chain, block: int) -> None:
        with self.context() as cursor:
            name = f'{str(chain)}_last_checked_initiators_block'
            cursor.execute('INSERT INTO setting (name, value) VALUES (%s, %s) ON CONFLICT(name) DO UPDATE SET name=EXCLUDED.name, value=EXCLUDED.value', (name, block))

    def get_initiator_available(self, chain: Chain) -> bool:
        with self.context() as cursor:
            name = f'{str(chain)}_initiator_available'
            cursor.execute('SELECT value FROM setting WHERE name = %s', (name,))
            return cursor.fetchone() is None  # If there is no setting set -- the initiator is NOT stuck and good to go!

    def disable_initiator(self, chain: Chain) -> None:
        with self.context() as cursor:
            name = f'{str(chain)}_initiator_available'
            cursor.execute('INSERT INTO setting (name, value) VALUES (%s, %s) ON CONFLICT(name) DO UPDATE SET name=EXCLUDED.name, value=EXCLUDED.value', (name, 'stuck!!!!!'))

    def add_product(self, product: Product) -> None:
        with self.context() as cursor:
            product_db_dict = product.to_db()
            columns = list(product_db_dict.keys())
            values = list(product_db_dict.values())
            cursor.execute(
                f'INSERT INTO product({",".join(columns)}) VALUES ({",".join(["%s"] * len(values))}) ON CONFLICT (hash) DO NOTHING',
                values,
            )
    
    def get_product_by_hash(self, product_hash: str) -> Product | None:
        with self.context() as cursor:
            cursor.execute('SELECT * FROM product WHERE hash = %s', (product_hash,))
            result = cursor.fetchone()
            if result is None:
                return None
            
            return Product.from_db(result)
    
    def add_subscription(self, subscription: Subscription) -> None:
        with self.context() as cursor:
            subscription_db_dict = subscription.to_db()
            columns = list(subscription_db_dict.keys())
            values = list(subscription_db_dict.values())
            cursor.execute(
                f'INSERT INTO subscription({",".join(columns)}) VALUES ({",".join(["%s"] * len(values))}) ON CONFLICT (hash) DO NOTHING',
                values,
            )

    def update_payments_made(self, subscription_hash: str, new_payments_made: int):
        with self.context() as cursor:
            cursor.execute('UPDATE subscription SET payments_made = GREATEST(payments_made, %s) WHERE hash = %s', (new_payments_made, subscription_hash))
    
    def terminate_subscription(self, subscription_hash: str):
        with self.context() as cursor:
            cursor.execute('UPDATE subscription SET terminated = TRUE WHERE hash = %s', (subscription_hash,))
    
    def load_single_subscription(self, row: tuple) -> Subscription:
        # TODO: change. All subscription-related fields should be read in a single db query and loaded all at once.
        product = self.get_product_by_hash(row[1])
        if product is None:
            raise AssertionError(f'No corresponding product was found for subscription row {row}!!!!!!!')
        
        row_with_product = (row[0], product, *row[2:])
        return Subscription.from_db(row_with_product)

    def get_all_subscriptions(self) -> list[Subscription]:
        with self.context() as cursor:
            cursor.execute('SELECT * FROM subscription')
            rows = cursor.fetchall()
        
        return [self.load_single_subscription(row) for row in rows]

    def get_subscriptions_by_user(self, address: ChecksumAddress) -> list[Subscription]:
        with self.context() as cursor:
            cursor.execute('SELECT * FROM subscription WHERE user_address = %s', (address,))
            rows = cursor.fetchall()
        
        return [self.load_single_subscription(row) for row in rows]
    
    def get_subscriptions_by_merchant(self, merchant_domain: str) -> list[Subscription]:
        with self.context() as cursor:
            cursor.execute('SELECT * FROM subscription INNER JOIN product ON subscription.product_hash = product.hash WHERE merchant_domain = %s', (merchant_domain,))
            rows = cursor.fetchall()
        
        return [self.load_single_subscription(row) for row in rows]
    
    def get_subscriptions_by_merchant_and_user(self, merchant_domain: str, userid: str) -> list[Subscription]:
        with self.context() as cursor:
            cursor.execute("SELECT * FROM subscription INNER JOIN product ON subscription.product_hash = product.hash WHERE merchant_domain = %s AND user_id = %s", (merchant_domain, userid))
            rows = cursor.fetchall()

        return [self.load_single_subscription(row) for row in rows]
    
    def get_subscription_by_merchant_and_subscriptionid(self, merchant_domain: str, subscription_id: str) -> Subscription | None:
        with self.context() as cursor:
            cursor.execute('SELECT * FROM subscription WHERE merchant_domain = %s AND subscription_id=%s ORDER BY start_ts LIMIT 1', (merchant_domain, subscription_id))
            result = cursor.fetchone()

        if result is None:
            return None
            
        return self.load_single_subscription(result)
    
    def get_subscription_by_hash(self, subscription_hash: str) -> Subscription | None:
        with self.context() as cursor:
            cursor.execute('SELECT * FROM subscription WHERE hash = %s', (subscription_hash,))
            result = cursor.fetchone()

        if result is None:
            return None

        return self.load_single_subscription(result)

    def get_payable_subscriptions(self, chain: Chain, timestamp: int, initiator: ChecksumAddress) -> list[Subscription]:
        with self.context() as cursor:
            cursor.execute(
                '''SELECT * FROM subscription INNER JOIN product ON subscription.product_hash = product.hash INNER JOIN merchant ON product.merchant_address = merchant.address AND product.chain = merchant.chain WHERE
                product.chain = %s AND terminated = FALSE AND
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
                    str(chain),
                    timestamp,
                    timestamp,
                    initiator,
                    timestamp,
                    60 * 60 * 24, # Attempt payments every 24 hours in case of issues 
                ),
            )
            rows = cursor.fetchall()
        
        return [self.load_single_subscription(row) for row in rows]

    def add_subscription_log(self, log: SubscriptionLog):
        with self.context() as cursor:
            log_db_dict = log.to_db()
            columns = list(log_db_dict.keys())
            values = list(log_db_dict.values())
            cursor.execute(
                f'INSERT INTO subscription_log({",".join(columns)}) VALUES ({",".join(["%s"] * len(values))})',
                values,
            )

    def get_subscription_logs(self, subscription_hash: str) -> list[SubscriptionLog]:
        with self.context() as cursor:
            cursor.execute('SELECT * FROM subscription_log WHERE subscription_hash=%s', (subscription_hash,))
            return [SubscriptionLog.from_db(row) for row in cursor.fetchall()]

    def store_metadata(self, ipfs_cid: str, content: str):
        with self.context() as cursor:
            cursor.execute('INSERT INTO metadata(ipfs_cid, content) VALUES(%s, %s) ON CONFLICT (ipfs_cid) DO NOTHING', (ipfs_cid, content))

    def get_metadata_by_ipfs_cid(self, ipfs_cid_hex: str) -> str | None:
        with self.context() as cursor:
            cursor.execute('SELECT content FROM metadata WHERE ipfs_cid = %s', (ipfs_cid_hex,))
            result = cursor.fetchone()
            if result is None:
                return None

            return result[0]
    
    def get_metadata_ipfs_cid_by_content(self, content: str) -> str | None:
        with self.context() as cursor:
            cursor.execute('SELECT ipfs_cid FROM metadata WHERE content = %s', (content,))
            result = cursor.fetchone()
            if result is None:
                return None
            
            return result[0]

    def get_merchant_initiator(self, merchant_address: ChecksumAddress, chain: Chain) -> ChecksumAddress | None:
        with self.context() as cursor:
            cursor.execute('SELECT initiator FROM merchant WHERE chain = %s AND address = %s', (str(chain), merchant_address))
            result = cursor.fetchone()
            if result is None:
                return None
            
            return result[0]

    def set_merchant_initiator(self, merchant_address: ChecksumAddress, chain: Chain, initiator: ChecksumAddress) -> None:
        with self.context() as cursor:
            cursor.execute('INSERT INTO merchant(address, chain, initiator) VALUES(%s, %s, %s) ON CONFLICT(address, chain) DO UPDATE SET initiator=EXCLUDED.initiator', (merchant_address, str(chain), initiator))
