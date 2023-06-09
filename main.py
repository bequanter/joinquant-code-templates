# 导入函数库
from jqdata import *


# 初始化函数，设定基准等等
def initialize(context):
    # 设定回测相关的参数
    set_backtest(context)

    # 股票类每笔交易时的手续费
    set_slip_fee(context)

    # 设定起始参数
    set_params(context)

    # 开盘前运行
    run_daily(before_market_open, time='before_open', reference_security='000300.XSHG')
    # 开盘时运行
    run_daily(market_open, time='open', reference_security='000300.XSHG')
    # 收盘后运行
    run_daily(after_market_close, time='after_close', reference_security='000300.XSHG')


## 开盘前运行函数
def before_market_open(context):
    # 根据策略选出股票池
    g.stock_pool = get_stock_pool_by_strategy(context)


def trading_now(context):
    return True


def should_buy(context, stock):
    return True

def should_sell(context, stock):
    return True


def should_hold(context):
    return True


## 开盘时运行函数
def market_open(context):
    suggested_buy_list = []
    hold_list = []

    if trading_now(context):
        for stock in g.stock_pool:
            if should_buy(context, stock):
                suggested_buy_list.append(stock)

    current_stock_set = list(context.portfolio.positions.keys())

    if trading_now(context):
        for stock in current_stock_set:
            if should_sell(context, stock):
                order_target_value(stock, 0)
            else:
                hold_list.append(stock)

    buy_list = []
    if trading_now(context):
        for stock in suggested_buy_list:
            if stock not in hold_list:
                buy_list.append(stock)

        if len(buy_list) != 0:
            cash = context.portfolio.available_cash / len(buy_list)
            for stock in buy_list:
                order_target_value(stock, cash)


## 收盘后运行函数
def after_market_close(context):
    # 得到当天所有成交记录
    trades = get_trades()
    for _trade in trades.values():
        log.info('成交记录：' + str(_trade))


def get_stock_pool_by_strategy(context):
    selected_stocks = get_fundamentals(
        query(valuation.code,
              valuation.pe_ratio,
              valuation.pb_ratio,
              valuation.market_cap,
              indicator.eps,
              indicator.inc_net_profit_annual)
        .filter(valuation.pe_ratio < 40,
                valuation.pe_ratio > 10,
                indicator.eps > 0.3,
                indicator.inc_net_profit_annual > 0.30,
                indicator.roe > 15)
        .order_by(valuation.pb_ratio.asc())
        .limit(50),
        date=None)

    stock_pool = list(selected_stocks['code'])
    stock_pool = paused_filter(stock_pool)
    stock_pool = delisted_filter(stock_pool)
    stock_pool = st_filter(stock_pool)
    return stock_pool


def set_params(context):
    # 设定起始日期为0
    g.days = 0
    # 设定调仓周期为10天
    g.refresh_rate = 10


def set_backtest(context):
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')

    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)


def set_slip_fee(context):
    ### 股票相关设定 ###
    # 股票类每笔交易时的手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5),
                   type='stock')


def paused_filter(security_list):
    # 获取当前单位时间（当天/当前分钟）的涨跌停价, 是否停牌，当天的开盘价等
    current_data = get_current_data()
    security_list = [stock for stock in security_list if not current_data[stock].paused]
    return security_list


def delisted_filter(security_list):
    # 获取当前单位时间（当天/当前分钟）的涨跌停价, 是否停牌，当天的开盘价等
    current_data = get_current_data()
    security_list = [stock for stock in security_list if not '退' in current_data[stock].name]
    return security_list


def st_filter(security_list):
    # 获取当前单位时间（当天/当前分钟）的涨跌停价, 是否停牌，当天的开盘价等
    current_data = get_current_data()
    security_list = [stock for stock in security_list if not current_data[stock].is_st]
    return security_list
