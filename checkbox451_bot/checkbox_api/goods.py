from operator import itemgetter

import requests

from checkbox451_bot.checkbox_api.helpers import endpoint, headers


def goods():
    url = endpoint("/goods")
    r = requests.get(url, headers=headers())
    r.raise_for_status()
    j = r.json()
    return sorted(j["results"], key=itemgetter("code"))
