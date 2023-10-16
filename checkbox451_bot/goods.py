from functools import lru_cache
from logging import getLogger

from checkbox451_bot import checkbox_api

log = getLogger(__name__)


@lru_cache(maxsize=1)
def get_items():
    items = {
        f"{good['name'].strip()} {good['price']/100:.2f} грн": {
            "code": good["code"],
            "name": good["name"],
            "price": good["price"],
        }
        for good in checkbox_api.goods.goods()
    }

    log.info(f"{items=}")
    return items
