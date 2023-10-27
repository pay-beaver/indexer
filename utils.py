import time
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from common_types import Subscription


def ts_now():
    return int(time.time())

def sort_subscriptions(subscriptions: Iterable['Subscription']) -> list['Subscription']:
    return sorted(
        subscriptions,
        key=lambda sub: sub.start_ts,
        reverse=True,
    )
