import os

import aiohttp
import requests

debug = bool(os.environ.get("DEBUG"))
api_url = "https://{}api.checkbox.in.ua/".format("dev-" if debug else "")
api_url = os.environ.get("API_URL", api_url)
print(f"{api_url=}")


def _init():
    login = os.environ["LOGIN"]
    password = os.environ["PASSWORD"]

    url = api_url + "api/v1/cashier/signin"
    r = requests.post(url, json=dict(login=login, password=password))
    r.raise_for_status()
    data = r.json()

    return f"{data['token_type']} {data['access_token']}"


_auth = _init()
del _init


_headers = {
    "X-Client-Name": "checkbox451",
    "X-Client-Version": "0.1",
    "Authorization": _auth,
}


async def get(path, **params):
    url = api_url + path
    async with aiohttp.ClientSession() as s:
        async with s.get(url, headers=_headers, params=params) as r:
            return await r.json()


def goods():
    url = api_url + "api/v1/goods"
    r = requests.get(url, headers=_headers)
    r.raise_for_status()
    j = r.json()
    return j["results"]
