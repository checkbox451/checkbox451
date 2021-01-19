from logging import getLogger

from . import checkbox_api

log = getLogger(__name__)

goods = {
    f"{good['name']} {good['price']/100:.2f} грн": {
        "code": good["code"],
        "name": good["name"],
        "price": good["price"],
    }
    for good in checkbox_api.goods()
}

log.info(f"{goods=}")
