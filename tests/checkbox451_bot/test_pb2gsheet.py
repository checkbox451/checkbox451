import pytest

from checkbox451_bot import pb2gsheet


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
    assert pb2gsheet.sender_pat.match(osnd).group(1) == sender


@pytest.mark.parametrize(
    "osnd",
    [
        "Переказ (Кредитна частина) 01.02.2018 00:00:00 по картці "
        "1234567890123456",
        "1234 **** **** 5678 Зарахування переказу на картку",
    ],
)
def test_sender_pat_no_match(osnd):
    assert pb2gsheet.sender_pat.match(osnd) is None
