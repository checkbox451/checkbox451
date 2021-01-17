from . import checkbox_api

goods = {
    f"{good['name']} {good['price']/100:.2f} грн": good["id"]
    for good in checkbox_api.goods()
}

print(f"{goods=}")
