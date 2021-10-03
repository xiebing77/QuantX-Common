#!/usr/bin/python
"""binance spot"""
import os
from datetime import datetime
from .bitrue import Bitrue
from .spot import Spot
from common import create_balance


class BitrueSpot(Bitrue):
    name = Bitrue.name + '_spot'
    start_time = datetime(2017, 8, 17, 8)

    def __init__(self, debug=False):
        return

    def connect(self):
        self.__api = Spot(user_agent=Bitrue.name+'/python')

    def ping(self):
        return self.__api.ping()

    def time(self):
        return self.get_time_from_data_ts(self.__api.time()['serverTime'])

    def _get_price(self, exchange_symbol):
        return float(self.__api.ticker_price(exchange_symbol)['price'])

    def _get_klines(self, exchange_symbol, interval, size, since):
        if since is None:
            klines = self.__api.get_klines(symbol=exchange_symbol, interval=interval, limit=size)
        else:
            klines = self.__api.get_klines(symbol=exchange_symbol, interval=interval, limit=size, startTime=since)

        return klines

    def get_account(self):
        """获取账户信息"""
        account = self.__api.get_account()
        nb = []
        balances = account['balances']
        for item in balances:
            if float(item['free'])==0 and float(item['locked'])==0:
                continue
            nb.append(item)
        account['balances'] = nb
        return account


    def get_all_balances(self):
        """获取余额"""
        balances = []
        account = self.get_account()
        for item in account['balances']:
            balance = create_balance(item['asset'], item['free'], item['locked'])
            balances.append(balance)
        return balances


    def get_balances(self, *coins):
        """获取余额"""
        coin_balances = []
        account = self.__api.get_account()
        balances = account['balances']
        for coin in coins:
            coinKey = self.__get_coinkey(coin)
            for item in balances:
                if coinKey == item['asset']:
                    balance = create_balance(coin, item['free'], item['locked'])
                    coin_balances.append(balance)
                    break
        if len(coin_balances) <= 0:
            return
        elif len(coin_balances) == 1:
            return coin_balances[0]
        else:
            return tuple(coin_balances)

    def _get_trades(self, exchange_symbol):
        trades = self.__api.get_my_trades(symbol=exchange_symbol)
        return trades

    def _create_order(self, binance_side, binance_type, exchange_symbol, price, amount, client_order_id=None):
        ret = self.__api.create_order(symbol=exchange_symbol, side=binance_side, type=binance_type,
            timeInForce=TIME_IN_FORCE_GTC, price=price, quantity=amount)
        log.debug(ret)
        try:
            if ret['orderId']:

                #if ret['fills']:

                # self.debug('Return buy order ID: %s' % ret['orderId'])
                return ret['orderId']
            else:
                # self.debug('Place order failed')
                return None
        except Exception:
            # self.debug('Error result: %s' % ret)
            return None

    def _get_open_orders(self, exchange_symbol):
        orders = self.__api.get_open_orders(symbol=exchange_symbol)
        return orders

    def _get_order(self, exchange_symbol, order_id):
        return self.__api.get_order(symbol=exchange_symbol, orderId=order_id)

    def _cancel_order(self, exchange_symbol, order_id):
        self.__api.cancel_order(symbol=exchange_symbol, orderId=order_id)

    def _get_order_book(self, exchange_symbol, limit=100):
        return self.__api.depth(symbol=exchange_symbol, limit=limit)

