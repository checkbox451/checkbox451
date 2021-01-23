from logging import getLogger

from . import checkbox_api

log = getLogger(__name__)

items = {}


def init():
    global items

    items = {
        f"{good['name'].strip()} {good['price']/100:.2f} грн": {
            "code": good["code"],
            "name": good["name"],
            "price": good["price"],
        }
        for good in checkbox_api.goods()
    }

    log.info(f"{items=}")
