_goods = [
    {
        "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
        "name": "Консультація",
        "price": 20000,
    },
    {
        "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
        "name": "Консультація",
        "price": 25000,
    },
    {
        "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
        "name": "Консультація",
        "price": 30000,
    },
    {
        "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
        "name": "Консультація",
        "price": 35000,
    },
    {
        "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
        "name": "Консультація",
        "price": 40000,
    },
]


goods = {
    f"{good['name']} {good['price']/100:.2f} грн": good["id"]
    for good in _goods
}
del _goods

print(f"{goods=}")
