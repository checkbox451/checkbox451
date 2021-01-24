from logging import getLogger

from checkbox451_bot import checkbox_api

log = getLogger(__name__)

items = {}


def init():
    items.update(
        {
            f"{good['name'].strip()} {good['price']/100:.2f} грн": {
                "code": good["code"],
                "name": good["name"],
                "price": good["price"],
            }
            for good in checkbox_api.goods.goods()
        }
    )

    log.info(f"{items=}")
