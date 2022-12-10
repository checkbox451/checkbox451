from logging import getLogger

import cachetools.func
import requests

from checkbox451_bot.config import Config

log = getLogger(__name__)


@cachetools.func.ttl_cache(ttl=86400)
def sign_in():
    from checkbox451_bot.checkbox_api.helpers import endpoint, headers

    pin_code = Config().get("checkbox", "pin", required=True)

    url = endpoint("/cashier/signinPinCode")
    r = requests.post(
        url,
        headers=headers(auth=False, lic=True),
        json=dict(pin_code=pin_code),
    )
    r.raise_for_status()
    data = r.json()

    authorization = f"{data['token_type']} {data['access_token']}"

    me_url = endpoint("/cashier/me")
    me_headers = headers(auth=False)
    me_headers["Authorization"] = authorization
    me_req = requests.get(me_url, headers=me_headers)
    me_req.raise_for_status()
    me = me_req.json()

    log.info("signed in: %s (%s)", me["full_name"], me["signature_type"])

    return authorization


def sign_out():
    sign_in.cache_clear()
