from datetime import datetime
from unittest.mock import patch

import pytest

from checkbox451_bot import gsheet
from checkbox451_bot.gsheet.common import (
    TransactionBase,
    TransactionProcessorBase,
)


@pytest.mark.parametrize(
    ["osnd", "sender"],
    [
        (
            "Плата за послуги, Шевченко Тарас Григорович",
            "Шевченко Тарас Григорович",
        ),
        (
            "1234 **** **** 5678 24.01.2019 12:34:56 Переказ вiд JANE DOE",
            "JANE DOE",
        ),
        (
            "1234 **** **** 5678 24.01.2019 12:34:56 Вiд JANE DOE",
            "JANE DOE",
        ),
    ],
)
def test_sender_pat(osnd, sender):
    assert gsheet.privat24.sender_pat.match(osnd).group(1) == sender


@pytest.mark.parametrize(
    "osnd",
    [
        "Переказ (Кредитна частина) 01.02.2018 00:00:00 по картці "
        "1234567890123456",
        "1234 **** **** 5678 Зарахування переказу на картку",
    ],
)
def test_sender_pat_no_match(osnd):
    assert gsheet.privat24.sender_pat.match(osnd) is None


@pytest.mark.parametrize(
    ["goods", "transaction", "receipt_goods"],
    [
        (
            {},
            TransactionBase(
                ts=datetime.now(),
                code="c0de",
                name="Carrot",
                sum=1000.0,
            ),
            [
                {
                    "code": "c0de",
                    "name": "Carrot",
                    "price": 100000,
                    "quantity": 1000,
                },
            ],
        ),
        (
            {
                "Cabbage 200.00": {
                    "code": "cbg200",
                    "name": "Cabbage",
                    "price": 20000,
                },
            },
            TransactionBase(
                ts=datetime.now(),
                code="c0de",
                name="Order_100000",
                sum=1000.0,
            ),
            [
                {
                    "code": "cbg200",
                    "name": "Cabbage",
                    "price": 20000,
                    "quantity": 5000,
                },
            ],
        ),
        (
            {
                "Cabbage 200.00": {
                    "code": "cbg200",
                    "name": "Cabbage",
                    "price": 20000,
                },
            },
            TransactionBase(
                ts=datetime.now(),
                code="c0d3",
                name="Order_182123",
                sum=1821.23,
            ),
            [
                {
                    "code": "c0d3",
                    "name": "Order_182123",
                    "price": 182123,
                    "quantity": 1000,
                },
            ],
        ),
        (
            {
                "Cabbage 200.00": {
                    "code": "cbg200",
                    "name": "Cabbage",
                    "price": 20000,
                },
                "Onion 500.00": {
                    "code": "oni500",
                    "name": "Onion",
                    "price": 50000,
                },
            },
            TransactionBase(
                ts=datetime.now(),
                code="c0d3",
                name="Order_100000",
                sum=1000.0,
            ),
            [
                {
                    "code": "oni500",
                    "name": "Onion",
                    "price": 50000,
                    "quantity": 2000,
                },
            ],
        ),
    ],
)
def test_transaction_to_goods(goods, transaction, receipt_goods):
    with patch("checkbox451_bot.goods.get_items", return_value=goods):
        transaction_to_goods = TransactionProcessorBase.transaction_to_goods
        assert transaction_to_goods(transaction) == receipt_goods
