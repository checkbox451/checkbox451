from functools import lru_cache
from pathlib import Path

import yaml


@lru_cache(maxsize=1)
class Config:
    def __init__(self):
        with Path("config.yaml").open() as f:
            self.__data = yaml.safe_load(f)

    @lru_cache
    def get(self, *items, required=False, default=None):
        r = self.__data
        for item in items:
            r = r.get(item, {})
        if r:
            return r
        elif not required:
            return default
        raise KeyError(items)
