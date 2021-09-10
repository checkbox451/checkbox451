import os

import cachetools.func
import requests


@cachetools.func.ttl_cache(ttl=86400)
def sign_in():
    from checkbox451_bot.checkbox_api.helpers import endpoint, headers

    pin_code = os.environ["CHECKBOX_PIN"]

    url = endpoint("/cashier/signinPinCode")
    r = requests.post(
        url,
        headers=headers(auth=False, lic=True),
        json=dict(pin_code=pin_code),
    )
    r.raise_for_status()
    data = r.json()

    return f"{data['token_type']} {data['access_token']}"


def sign_out():
    sign_in.cache_clear()
