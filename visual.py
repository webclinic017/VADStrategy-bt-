import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import os
from config import *

app = dash.Dash(__name__)

# 定义数据目录
DATA_DIR = CONFIG['df_dir']

def load_data(strategy, timeframe, target):
    filename = f"{strategy}_{timeframe}_{target}_all_trades.csv"
    file_path = os.path.join(DATA_DIR, filename)
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        df['时间'] = pd.to_datetime(df['时间'])
        return df
    else:
        return pd.DataFrame()  # 返回空DataFrame如果文件不存在

def create_figure(strategy_df, benchmark_df, timeframe, strategy, benchmark, target):
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        vertical_spacing=0.1, 
                        row_heights=[0.5, 0.25, 0.25],
                        subplot_titles=('交易信号图', '总资金曲线', '资金利用率'))

    fig.add_trace(go.Candlestick(x=strategy_df['时间'],
                                 open=strategy_df['open'],
                                 high=strategy_df['high'],
                                 low=strategy_df['low'],
                                 close=strategy_df['close'],
                                 name='交易曲线'),
                  row=1, col=1)

    buy_signals = strategy_df[strategy_df['交易状态'] == '买']
    add_signals = strategy_df[strategy_df['交易状态'] == '加']
    sell_signals = strategy_df[strategy_df['交易状态'] == '卖']

    fig.add_trace(go.Scatter(x=buy_signals['时间'], y=buy_signals['low'], mode='markers',
                             marker=dict(symbol='triangle-up', size=15, color='lime', line=dict(color='green', width=2)),
                             name='开仓信号'), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=add_signals['时间'], y=add_signals['low'], mode='markers',
                             marker=dict(symbol='triangle-up', size=15, color='lime', line=dict(color='green', width=2)),
                             name='加仓信号'), row=1, col=1)

    fig.add_trace(go.Scatter(x=sell_signals['时间'], y=sell_signals['high'], mode='markers',
                             marker=dict(symbol='triangle-down', size=15, color='red', line=dict(color='darkred', width=2)),
                             name='平仓信号'), row=1, col=1)

    fig.add_trace(go.Scatter(x=strategy_df['时间'], y=strategy_df['总资产'], mode='lines+markers', 
                             name=f'{strategy} 总资产曲线', marker=dict(color='red', size=1)),
                  row=2, col=1)

    fig.add_trace(go.Scatter(x=benchmark_df['时间'], y=benchmark_df['总资产'], mode='lines+markers', 
                             name=f'{benchmark} 总资产曲线', marker=dict(color='grey', size=1)),
                  row=2, col=1)

    fig.add_trace(go.Scatter(x=strategy_df['时间'], y=strategy_df['资金利用率'], mode='markers', 
                         name='资金利用率', marker=dict(color='orange', size=1)),
                  row=3, col=1)

    fig.update_layout(
        height=1200,
        xaxis_rangeslider_visible=False,
        hovermode='x unified',
        legend=dict(x=1.05, y=0.5),
        margin=dict(l=50, r=50, t=50, b=50), 
        autosize=True
    )

    fig.update_yaxes(title_text="价格", row=1, col=1)
    fig.update_yaxes(title_text="资产", row=2, col=1)
    fig.update_yaxes(title_text="资金利用率", row=3, col=1)

    fig.update_xaxes(title_text="时间", row=3, col=1)

    return fig

app.layout = html.Div([
    html.H1(id='strategy-title', style={'textAlign': 'center'}),
    
    # 将所有下拉菜单放在一个 Div 中，并设置 flex 布局
    html.Div([
        html.Div([
            html.Label('策略:', style={'marginRight': '5px'}),
            dcc.Dropdown(
                id='strategy-dropdown',
                options=[
                    {'label': 'VAD策略', 'value': 'vad'},
                    {'label': '其他策略1', 'value': 'strategy1'},
                    {'label': '其他策略2', 'value': 'strategy2'}
                ],
                value='vad',
                style={'width': '150px'}
            )
        ], style={'display': 'inline-block', 'marginRight': '20px'}),
        
        html.Div([
            html.Label('标的:', style={'marginRight': '5px'}),
            dcc.Dropdown(
                id='target-dropdown',
                options=[
                    {'label': 'QQQ', 'value': 'QQQ'},
                    {'label': 'BTC', 'value': 'BTC'},
                    {'label': '600519', 'value': '600519'}
                ],
                value='QQQ',
                style={'width': '120px'}
            )
        ], style={'display': 'inline-block', 'marginRight': '20px'}),

        html.Div([
            html.Label('时间框架:', style={'marginRight': '5px'}),
            dcc.Dropdown(
                id='timeframe-dropdown',
                options=[
                    {'label': '5分钟', 'value': '5min'},
                    {'label': '240分钟', 'value': '240min'}
                ],
                value='240min',
                style={'width': '120px'}
            )
        ], style={'display': 'inline-block', 'marginRight': '20px'}),
                
        html.Div([
            html.Label('基准:', style={'marginRight': '5px'}),
            dcc.Dropdown(
                id='benchmark-dropdown',
                options=[
                    {'label': '买入并持有', 'value': 'buyandhold'},
                    {'label': '国债', 'value': 'treasury'},
                    {'label': 'BTC', 'value': 'btc'}
                ],
                value='buyandhold',
                style={'width': '150px'}
            )
        ], style={'display': 'inline-block'}),
    ], style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center', 'marginBottom': '20px'}),
    
    html.Div([
        dcc.Graph(id='strategy-graph', style={'width': '100%', 'height': '100%'})
    ], style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center'})

], style={'padding': '20px', 'maxWidth': '1200px', 'margin': '0 auto'})

@app.callback(
    [Output('strategy-graph', 'figure'),
     Output('strategy-title', 'children')],
    [Input('strategy-dropdown', 'value'),
     Input('timeframe-dropdown', 'value'),
     Input('benchmark-dropdown', 'value'),
     Input('target-dropdown', 'value')]
)
def update_graph_and_title(strategy, timeframe, benchmark, target):
    strategy_df = load_data(strategy, timeframe, target)
    benchmark_df = load_data(benchmark, timeframe, target)
    
    if strategy_df.empty or benchmark_df.empty:
        print("No data available for the selected parameters")
        return go.Figure().add_annotation(text="No data available", showarrow=False, font=dict(size=20)), "No Data Available"
    
    figure = create_figure(strategy_df, benchmark_df, timeframe, strategy, benchmark, target)
    title = f'Visualisation - {strategy} vs {benchmark} - {timeframe} - {target}'
    
    return figure, title

if __name__ == '__main__':
    app.run_server(debug=True)