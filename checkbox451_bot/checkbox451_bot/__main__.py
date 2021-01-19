import logging

from aiogram.utils import executor

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    from .handlers import dp

    executor.start_polling(dp, skip_updates=True)
