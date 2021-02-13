import pytest

from checkbox451_bot.handlers.helpers import text_to_goods


@pytest.mark.parametrize(
    "text, expected",
    (
        (
            "Консультація дитини 300.00 грн",
            [
                {
                    "name": "Консультація дитини",
                    "price": 30000,
                    "quantity": 1000,
                    "code": "Консультація дитини 300.00",
                }
            ],
        ),
        (
            "Консультація 400 грн",
            [
                {
                    "name": "Консультація",
                    "price": 40000,
                    "quantity": 1000,
                    "code": "Консультація 400.00",
                },
            ],
        ),
        (
            "Цукор 24,99 грн 1,25",
            [
                {
                    "name": "Цукор",
                    "price": 2499,
                    "quantity": 1250,
                    "code": "Цукор 24.99",
                },
            ],
        ),
        (
            "Цукор 25 грн 0.4  \n"
            "Сир кисломолочний 5% жиру 45.49 грн 2\n"
            "Борошно пшеничне, в/ґ 18.2 грн 0,500",
            [
                {
                    "name": "Цукор",
                    "price": 2500,
                    "quantity": 400,
                    "code": "Цукор 25.00",
                },
                {
                    "name": "Сир кисломолочний 5% жиру",
                    "price": 4549,
                    "quantity": 2000,
                    "code": "Сир кисломолочний 5% жиру 45.49",
                },
                {
                    "name": "Борошно пшеничне, в/ґ",
                    "price": 1820,
                    "quantity": 500,
                    "code": "Борошно пшеничне, в/ґ 18.20",
                },
            ],
        ),
    ),
)
def test_text_to_goods(text, expected):
    goods = text_to_goods(text)
    assert goods == expected
