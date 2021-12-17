import argparse
import datetime, time
import os
import common
import common.log as log
from common import SIDE_BUY, SIDE_SELL
from common import ORDER_TYPE_LIMIT
from common.instance import INSTANCE_COLLECTION_NAME, INSTANCE_STATUS_START, INSTANCE_STATUS_STOP, instance_statuses, add_instance, delete_instance, update_instance
from exchange.exchange_factory import get_exchange_names, create_exchange
from engine.trade_engine import TradeEngine
from db.mongodb import get_mongodb
import setup


td_db = get_mongodb(setup.trade_db_name)


def real_run(args):
    config = common.get_json_config(args.config)
    module_name = config["module_name"].replace("/", ".")
    class_name = config["class_name"]
    log.info("strategy name: %s;  config: %s" % (class_name, config))

    instance_id = args.iid
    exchange_name = args.exchange
    if args.print:
        log.print_switch = True
    if args.log:
        log.log_switch = True
        logfilename = instance_id + ".log"
        print(logfilename)
        log.init('real', logfilename)
        info = 'instance_id: %s,  exchange_name: %s' % (instance_id, exchange_name)
        log.info("%s" % (info))

    exchange = create_exchange(exchange_name)
    if not exchange:
        print("exchange name error!")
        exit(1)
    exchange.connect()
    exchange.ping()
    trade_engine = TradeEngine(instance_id, exchange)

    strategy = common.createInstance(module_name, class_name, instance_id, config, exchange, trade_engine)
    if not args.loop:
        strategy.on_tick()
        exit(1)

    prefix = '.'*10
    while(True):
        tick_start = datetime.datetime.now()
        log.info("%s  %s tick start  %s" % (prefix, tick_start, '.'*72))

        if args.debug:
            strategy.on_tick()
        else:
            try:
                strategy.on_tick()
            except Exception as ept:
                log.critical(ept)

        tick_end = datetime.datetime.now()
        log.info("%s  %s tick end, cost: %s\n\n" % (prefix, tick_end, tick_end - tick_start))

        time.sleep(config["loop_sec"])


def real_hand(args):
    instance_id = args.iid
    ss = td_db.find(INSTANCE_COLLECTION_NAME, {"instance_id": instance_id})
    if not ss:
        print('%s not exist')
        exit(1)
    s = ss[0]
    symbol = s['symbol']
    exchange_name = s['exchange']
    if args.print:
        log.print_switch = True
    if args.log:
        log.log_switch = True
        logfilename = instance_id + ".log"
        print(logfilename)
        log.init('real', logfilename)
        info = 'instance_id: %s,  exchange_name: %s' % (instance_id, exchange_name)
        log.info("%s" % (info))

    exchange = create_exchange(exchange_name)
    if not exchange:
        print("exchange name error!")
        exit(1)
    exchange.connect()
    exchange.ping()
    trade_engine = TradeEngine(instance_id, exchange)
    order_id = trade_engine.new_bill(
        side=args.side,
        type=ORDER_TYPE_LIMIT,
        symbol=symbol,
        price=args.price,
        qty=args.qty)


def real_list(args):
    query = {"user": args.user}
    if args.status:
        query["status"] = args.status
    ss = td_db.find(INSTANCE_COLLECTION_NAME, query)
    #print(ss)
    all_value = 0
    all_his_profit = 0
    all_flo_profit = 0
    all_commission = 0

    title_head_fmt = "%-30s  %12s"
    head_fmt       = "%-30s  %12s"

    title_pst_fmt = "%18s  %18s  %18s  %12s"
    pst_fmt       = title_pst_fmt#"%18s  %18f  %18f  %12f"

    title_tail_fmt = "    %-20s  %-10s  %-s"

    print(title_head_fmt % ("instance_id", "symbol") +
        title_pst_fmt % ('pst_base_qty', 'deal_quote_qty', "profit", "commission") +
        title_tail_fmt % ("exchange", "status", "config_path"))
    for s in ss:
        instance_id = s["instance_id"]
        exchange_name = s["exchange"]
        if "status" in s:
            status = s["status"]
        else:
            status = ""
        #if status != args.status and status != "":
        #    continue

        config_path = s["config_path"]
        #all_value += value
        profit_info = ""
        try:
            exchange = create_exchange(exchange_name)
            if not exchange:
                print("exchange name error!")
                exit(1)
            exchange.connect()
            exchange.ping()

            if config_path:
                config = common.get_json_config(config_path)
                symbol = config['symbol']
            else:
                symbol = s['symbol']

            ticker_price = exchange.ticker_price(symbol)
            trade_engine = TradeEngine(instance_id, exchange)
            pst_base_qty, deal_quote_qty, gross_profit = trade_engine.get_position(symbol, ticker_price)

            commission = deal_quote_qty * 0.001
            all_commission += commission
            b_prec, q_prec = trade_engine.get_symbol_prec(symbol)
            profit_info = pst_fmt % (round(pst_base_qty, b_prec),
                round(deal_quote_qty, q_prec), round(gross_profit, q_prec), round(commission, q_prec))

        except Exception as ept:
            profit_info = "error:  %s" % (ept)

        print(head_fmt % (instance_id, symbol) +
            profit_info +
            title_tail_fmt % (exchange_name, status, config_path))

    if args.stat:
        print(head_fmt % ("all", '', all_profit) +
            pst_fmt % (all_his_profit, all_his_profit/all_value*100, all_flo_profit, all_flo_profit/all_value*100, all_commission))


def real_add(args):
    add_instance({
        "user": args.user,
        "instance_id": args.iid,
        "symbol": args.symbol,
        "config_path": args.config_path,
        "exchange": args.exchange,
        "status": args.status,
    })


def real_delete(args):
    delete_instance({"instance_id": args.iid})


def real_update(args):
    record = {}
    if args.user:
        record["user"] = args.user
    if args.new_iid:
        record["instance_id"] = args.new_iid
    if args.symbol:
        record["symbol"] = args.symbol
    if args.config_path:
        record["config_path"] = args.config_path
    if args.exchange:
        record["exchange"] = args.exchange
    if args.status:
        record["status"] = args.status

    if record:
        update_instance({"instance_id": args.iid}, record)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='real run one')
    subparsers = parser.add_subparsers(help='sub-command help')

    parser_run = subparsers.add_parser('run', help='run instance')
    parser_run.add_argument('-iid', required=True, help='instance id')
    parser_run.add_argument('-loop', action="store_true", help='run loop')
    parser_run.add_argument('-debug', action="store_true", help='run debug')
    parser_run.add_argument('--log', action="store_true", help='log info')
    parser_run.add_argument('--print', action="store_true", help='print info')
    parser_run.set_defaults(func=real_run)

    parser_hand = subparsers.add_parser('hand', help='handmade instance')
    parser_hand.add_argument('-iid', required=True, help='instance id')
    parser_hand.add_argument('-side', required=True, choices=[SIDE_BUY, SIDE_SELL], help='')
    parser_hand.add_argument('-price', required=True, type=float, help='price')
    parser_hand.add_argument('-qty', required=True, type=float, help='quantity')
    parser_hand.add_argument('--log', action="store_true", help='log info')
    parser_hand.add_argument('--print', action="store_true", help='print info')
    parser_hand.set_defaults(func=real_hand)


    parser_list = subparsers.add_parser('list', help='list of instance')
    parser_list.add_argument('-user', help='user name')
    parser_list.add_argument('--status', choices=instance_statuses, help='instance status')
    parser_list.add_argument('--stat', help='stat all', action="store_true")
    parser_list.set_defaults(func=real_list)

    parser_add = subparsers.add_parser('add', help='add new instance')
    parser_add.add_argument('-user', required=True, help='user name')
    parser_add.add_argument('-exchange', choices=get_exchange_names(), help='exchange name')
    parser_add.add_argument('-iid', required=True, help='instance id')
    parser_add.add_argument('-symbol', help='bymbol')
    parser_add.add_argument('-config_path', help='config path')
    parser_add.add_argument('-status', choices=instance_statuses, default=INSTANCE_STATUS_START, help='instance status')
    parser_add.set_defaults(func=real_add)

    parser_delete = subparsers.add_parser('delete', help='delete instance')
    parser_delete.add_argument('-iid', required=True, help='instance id')
    parser_delete.set_defaults(func=real_delete)

    parser_update = subparsers.add_parser('update', help='update instance')
    parser_update.add_argument('-iid', required=True, help='instance id')
    parser_update.add_argument('--user', help='user name')
    parser_update.add_argument('--new_iid', help='new instance id')
    parser_update.add_argument('--symbol', help='symbol')
    parser_update.add_argument('--config_path', help='config path')
    parser_update.add_argument('--exchange', help='instance exchange')
    parser_update.add_argument('--status', choices=instance_statuses, help='instance status')
    parser_update.set_defaults(func=real_update)

    args = parser.parse_args()

    if hasattr(args, 'func'):
        args.func(args)

