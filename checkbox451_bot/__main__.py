import logging

fmt = (
    "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - "
    "%(message)s"
)
logging.basicConfig(format=fmt, level=logging.INFO)


def main():
    from checkbox451_bot import run

    run.main()


main()
