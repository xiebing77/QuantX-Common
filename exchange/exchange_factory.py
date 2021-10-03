#!/usr/bin/python
"""exchange factory"""

from exchange.binance.binance_spot import BinanceSpot
from exchange.bitrue.bitrue_spot import BitrueSpot


exchangeClasses = [BinanceSpot, BitrueSpot]


def get_exchange_names():
    return [ ec.name for ec in exchangeClasses]


def create_exchange(exchange_name):
    for ec in exchangeClasses:
        if ec.name == exchange_name:
            return ec(debug=True)
    return None

