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

    ## 运行函数（reference_security为运行时间的参考标的；传入的标的只做种类区分，因此传入'000300.XSHG'或'510300.XSHG'是一样的）
    # 开盘前运行
    run_daily(before_market_open, time='before_open', reference_security='000300.XSHG')
    # 开盘时运行
    run_daily(market_open, time='open', reference_security='000300.XSHG')
    # 收盘后运行
    run_daily(after_market_close, time='after_close', reference_security='000300.XSHG')


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

    # 输出内容到日志 log.info()
    log.info('初始函数开始运行且全局只运行一次')
    # 过滤掉order系列API产生的比error级别低的log
    # log.set_level('order', 'error')


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


def get_stocks(context):
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


## 开盘前运行函数
def before_market_open(context):
    # 输出运行时间
    log.info('函数运行时间(before_market_open)：' + str(context.current_dt.time()))

    # 给微信发送消息（添加模拟交易，并绑定微信生效）
    # send_message('美好的一天~')

    # 根据策略选出股票池
    stock_pool = get_stocks(context)

    if (len(stock_pool) > 0):
        g.security = stock_pool[0]
    else:
        g.security = '000001.XSHE'


## 开盘时运行函数
def market_open(context):
    log.info('函数运行时间(market_open):' + str(context.current_dt.time()))
    security = g.security
    # 获取股票的收盘价
    close_data = get_bars(security, count=5, unit='1d', fields=['close'])
    # 取得过去五天的平均价格
    MA5 = close_data['close'].mean()
    # 取得上一时间点价格
    current_price = close_data['close'][-1]
    # 取得当前的现金
    cash = context.portfolio.available_cash

    # 如果上一时间点价格高出五天平均价1%, 则全仓买入
    if (current_price > 1.01 * MA5) and (cash > 0):
        # 记录这次买入
        log.info("价格高于均价 1%%, 买入 %s" % (security))
        # 用所有 cash 买入股票
        order_value(security, cash)
    # 如果上一时间点价格低于五天平均价, 则空仓卖出
    elif current_price < MA5 and context.portfolio.positions[security].closeable_amount > 0:
        # 记录这次卖出
        log.info("价格低于均价, 卖出 %s" % (security))
        # 卖出所有股票,使这只股票的最终持有量为0
        order_target(security, 0)


## 收盘后运行函数
def after_market_close(context):
    log.info(str('函数运行时间(after_market_close):' + str(context.current_dt.time())))
    # 得到当天所有成交记录
    trades = get_trades()
    for _trade in trades.values():
        log.info('成交记录：' + str(_trade))
    log.info('一天结束')
    log.info('##############################################################')
