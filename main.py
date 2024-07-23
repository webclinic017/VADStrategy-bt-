# main.py
import os
import pandas as pd
import backtrader as bt
import numpy as np
from config import CONFIG
from strategy import StrategyFactory

# 确保输出目录存在
def ensure_dir(file_path):
    directory = os.path.dirname(file_path) 
    if not os.path.exists(directory): 
        os.makedirs(directory)

# 加载数据
def load_data(file_path):
    data = pd.read_csv(file_path, index_col='datetime', parse_dates=True)
    print(data.head())
    return data

def run_strategy(data_file, strategy_name, strategy_params):
    # 创建新的 Cerebro 实例
    cerebro = bt.Cerebro()

    # 设置初始现金、佣金率、滑点
    cerebro.broker.setcash(CONFIG['initial_cash'])
    cerebro.broker.setcommission(CONFIG['commission_rate'])
    cerebro.broker.set_slippage_perc(CONFIG['slippage'])

    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

    # 加载数据
    data = load_data(data_file)
    start_date = data.index[0].date()
    end_date = data.index[-1].date()
    num_years = (end_date - start_date).days / 365.25  # 使用实际的日期范围
    print(f"交易年数: {num_years:.2f}")
    
    data_feed = bt.feeds.PandasData(dataname=data)
    cerebro.adddata(data_feed)

    # 加载策略
    strategy_class = StrategyFactory.get_strategy(strategy_name)
    print(f"Using strategy class: {strategy_class.__name__}")
    cerebro.addstrategy(strategy_class, **strategy_params)

    # 运行回测
    print(f"初始资金: {cerebro.broker.getvalue():.2f}")
    results = cerebro.run()
    print(f"回测结束后的资金: {cerebro.broker.getvalue():.2f}")

    return cerebro, results, num_years

# 打印策略结果
def print_analysis(results, num_years, strategy_name, data_name):
    results = results[0]
    num_years = num_years

    # 获取分析结果
    sharpe_ratio = results.analyzers.sharpe.get_analysis().get('sharperatio', 0)
    drawdown = results.analyzers.drawdown.get_analysis()
    returns = results.analyzers.returns.get_analysis()
    trade_analysis = results.analyzers.trades.get_analysis()
    
    # 计算年化收益率
    total_return = returns.get('rtot', 0)
    annual_return = (np.log(1 + total_return) / num_years) if total_return > -1 else -1

    # 计算其他指标
    total_trades = trade_analysis.get('total', {}).get('total', 0)
    winning_trades = trade_analysis.get('won', {}).get('total', 0)
    losing_trades = trade_analysis.get('lost', {}).get('total', 0)
    win_rate = winning_trades / total_trades if total_trades > 0 else 0
    try:
        profit_factor = abs(trade_analysis['won']['pnl']['total'] / trade_analysis['lost']['pnl']['total'])
    except (KeyError, ZeroDivisionError):
        profit_factor = float('inf') if winning_trades > 0 else 0

    max_drawdown = drawdown.get('max', {}).get('drawdown', 0)
    max_drawdown_duration = drawdown.get('max', {}).get('len', 0)

    # 计算最大连续盈利和亏损次数
    try:
        max_win_streak = trade_analysis['streak']['won']['longest']
        max_loss_streak = trade_analysis['streak']['lost']['longest']
    except KeyError:
        max_win_streak = max_loss_streak = 0

    # 创建结果字典
    analysis_results = {
        "策略": strategy_name,
        "数据": data_name,
        "夏普比率": f"{sharpe_ratio:.2f}",
        "总收益率": f"{total_return:.2%}",
        "年化收益率": f"{annual_return:.2%}",
        "最大回撤": f"{max_drawdown:.2%}",
        "最大回撤持续期": max_drawdown_duration,
        "总交易次数": total_trades,
        "盈利交易次数": winning_trades,
        "亏损交易次数": losing_trades,
        "交易胜率": f"{win_rate:.2%}",
        "盈亏比": f"{profit_factor:.2f}",
        "平均交易盈亏": f"${trade_analysis.get('pnl', {}).get('average', 0):.2f}",
        "最大连续盈利次数": max_win_streak,
        "最大连续亏损次数": max_loss_streak
    }

    # 打印结果
    for key, value in analysis_results.items():
        print(f"{key}: {value}")

    # 保存结果到文件
    output_file = f"{CONFIG['output_dir']}{strategy_name}_{data_name}_analysis.csv"
    pd.DataFrame([analysis_results]).to_csv(output_file, index=False)
    print(f"分析结果已保存到: {output_file}")

    return analysis_results

def main():
    # 运行所有策略组合
    for strategy_name, strategy_params in CONFIG['strategy_params'].items():
        for data_name, data_file in CONFIG['data_files'].items():
            print(f"\n运行策略: {strategy_name} 数据: {data_name}")
            cerebro, results, num_years = run_strategy(data_file, strategy_name, strategy_params)
            
            # 输出结果
            analysis_results = print_analysis(results, num_years, strategy_name, data_name)

            # 导出交易记录
            strategy = results[0]
            df = strategy.trade_recorder.get_analysis()
            
            output_file = f"{CONFIG['output_dir']}{strategy_name}_{data_name}.csv"
            ensure_dir(output_file)
            df.to_csv(output_file)
            print(f"交易记录已保存到: {output_file}")

if __name__ == '__main__':
    main()