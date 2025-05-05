import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import ccxt
from concurrent.futures import ThreadPoolExecutor
import time
import requests
from flask_caching import Cache

# Configuration
TIMEFRAME = '4h'
RSI_PERIOD = 14
REFRESH_INTERVAL = 10  # Seconds
MAX_WORKERS = 12
MIN_VOLUME = 2500000
SYMBOL_LIMIT = 100
CACHE_TIMEOUT = 55  # Slightly less than refresh interval

# Initialize Dash app with caching
app = dash.Dash(__name__)
cache = Cache(app.server, config={'CACHE_TYPE': 'SimpleCache'})
app.config.suppress_callback_exceptions = True

# Exchange configuration
exchange = ccxt.binance({
    'enableRateLimit': True,
    'rateLimit': 1200,
    'options': {'defaultType': 'spot'}
})


# Enhanced data fetching with retries
def fetch_with_retry(method, max_retries=3, delay=1):
    for i in range(max_retries):
        try:
            return method()
        except (ccxt.NetworkError, ccxt.ExchangeError, requests.exceptions.RequestException):
            if i < max_retries - 1:
                time.sleep(delay * (i + 1))
                continue
            raise
    return None


# Cached symbol fetching
@cache.memoize(timeout=CACHE_TIMEOUT)
def get_active_symbols():
    try:
        markets = fetch_with_retry(lambda: exchange.load_markets())
        tickers = fetch_with_retry(lambda: exchange.fetch_tickers())
        
        usdt_tickers = [t for t in tickers.values() 
                       if t['symbol'].endswith('/USDT') and markets[t['symbol']]['active']]
        
        volume_filtered = sorted(
            [t for t in usdt_tickers if t.get('quoteVolume', 0) > MIN_VOLUME],
            key=lambda x: x['quoteVolume'], reverse=True
        )[:SYMBOL_LIMIT]
        
        return [t['symbol'] for t in volume_filtered]
    
    except Exception as e:
        print(f"Symbol fetch error: {e}")
        return []



# Vectorized RSI calculation
def vectorized_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


# ... (keep all initial imports and configuration unchanged)

def analyze_symbol(symbol):
    try:
        ohlcv = fetch_with_retry(lambda: exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=168))
        if len(ohlcv) < 50:
            return None

        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['close'] = pd.to_numeric(df['close'])
        df['volume'] = pd.to_numeric(df['volume'])
        
        closes = df['close']
        volumes = df['volume']
        
        return {
            'symbol': symbol.replace('/USDT', ''),
            'price': closes.iloc[-1],
            'rsi': vectorized_rsi(closes).iloc[-1],
            'change_24h': (closes.iloc[-1] - closes.iloc[-24]) / closes.iloc[-24] * 100,
            'change_7d': (closes.iloc[-1] - closes.iloc[-42*4]) / closes.iloc[-42*4] * 100,  # 42*4h=7 days
            'volatility': closes.pct_change().std() * np.sqrt(365),
            'volume_24h': volumes.tail(24).sum(),
            'support': closes.rolling(24).min().iloc[-1],
            'resistance': closes.rolling(24).max().iloc[-1],
            'vwap': (closes * volumes).sum() / volumes.sum()
        }
    except Exception as e:
        print(f"Analysis failed for {symbol}: {e}")
        return None

def create_dashboard(data):
    df = pd.DataFrame([d for d in data if d is not None])
    if df.empty:
        return go.Figure()
    
    # Calculate market overview stats
    stats = {
        'total_volume': df['volume_24h'].sum(),
        'overbought': (df['rsi'] > 70).sum(),
        'oversold': (df['rsi'] < 30).sum(),
        'avg_volatility': df['volatility'].mean(),
        'top_gainer_24h': df.loc[df['change_24h'].idxmax()]['symbol'],
        'top_loser_24h': df.loc[df['change_24h'].idxmin()]['symbol'],
        'top_gainer_7d': df.loc[df['change_7d'].idxmax()]['symbol'],
        'top_loser_7d': df.loc[df['change_7d'].idxmin()]['symbol']
    }
    
    # Create main figure with subplots
    fig = go.Figure().set_subplots(
        rows=2, cols=2,
        specs=[[{"type": "scatter"}, {"type": "histogram"}],
               [{"type": "scatter", "colspan": 2}, None]],
        vertical_spacing=0.1,
        subplot_titles=(
            'RSI Overview', 
            'Price Change Distribution',
            'Volatility vs Price Changes'
        )
    )
    
    # RSI Scatter plot
    fig.add_trace(
        go.Scatter(
            x=df['symbol'],
            y=df['rsi'],
            mode='markers+text',
            marker=dict(
                size=np.log(df['volume_24h']) * 0.6,
                color=df['rsi'],
                colorscale='RdYlGn',
                reversescale=True,
                showscale=True,
                colorbar=dict(title='RSI'),
                line=dict(width=1, color='DarkSlateGrey')
            ),
            text=df['symbol'],
            textposition='top center',
            hovertext=df.apply(lambda x: (
                f"<b>{x['symbol']}</b><br>"
                f"Price: ${x['price']:,.2f}<br>"
                f"RSI: {x['rsi']:.1f}<br>"
                f"24h Δ: {x['change_24h']:+.1f}%<br>"
                f"7d Δ: {x['change_7d']:+.1f}%<br>"               
                f"Volume: ${x['volume_24h']:,.0f}"
            ), axis=1),
            hoverinfo='text'
        ), row=1, col=1
    )
    
    # Combined Histogram
    fig.add_trace(
        go.Histogram(
            x=df['change_24h'],
            name='24h Change',
            nbinsx=30,
            marker_color='#636EFA',
            opacity=0.5
        ), row=1, col=2
    )
    fig.add_trace(
        go.Histogram(
            x=df['change_7d'],
            name='7d Change',
            nbinsx=30,
            marker_color='#EF553B',
            opacity=0.5
        ), row=1, col=2
    )
    
    # Volatility vs Changes Scatter
    fig.add_trace(
        go.Scatter(
            x=df['volatility'],
            y=df['change_24h'],
            mode='markers',
            name='24h Change',
            marker=dict(
                size=12,
                color=df['rsi'],
                colorscale='RdYlGn',
                showscale=False
            ),
            text=df['symbol'],
            hoverinfo='text+x+y'
        ), row=2, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df['volatility'],
            y=df['change_7d'],
            mode='markers',
            name='7d Change',
            marker=dict(
                size=12,
                color=df['rsi'],
                colorscale='RdYlGn',
                showscale=False,
                symbol='diamond'
            ),
            text=df['symbol'],
            hoverinfo='text+x+y'
        ), row=2, col=1
    )
    
    # Update layout
    fig.update_layout(
        template='plotly_dark',
        height=1200,
        title_text=f"Crypto Market Dashboard • {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        showlegend=True,
        margin=dict(t=100, b=50),
        hoverlabel=dict(
            bgcolor='rgba(0,0,0,0.8)',
            font_size=14
        )
    )
    
    # Update axes
    fig.update_xaxes(title_text="Assets", row=1, col=1)
    fig.update_yaxes(title_text="RSI", row=1, col=1)
    fig.update_xaxes(title_text="Price Change (%)", row=1, col=2)
    fig.update_yaxes(title_text="Count", row=1, col=2)
    fig.update_xaxes(title_text="Volatility", row=2, col=1)
    fig.update_yaxes(title_text="Price Change (%)", row=2, col=1)
    
    # Stats cards
    stats_cards = [
        html.Div([
            html.Div([
                html.H3(f"${stats['total_volume']/1e9:.1f}B", className='stats-value'),
                html.P("24h Volume", className='stats-label')
            ], className='stats-card')
        ], className='stats-column'),
        html.Div([
            html.Div([
                html.H3(stats['overbought'], className='stats-value', style={'color': '#FF4676'}),
                html.P("Overbought (RSI >70)", className='stats-label')
            ], className='stats-card')
        ], className='stats-column'),
        html.Div([
            html.Div([
                html.H3(stats['oversold'], className='stats-value', style={'color': '#00FF88'}),
                html.P("Oversold (RSI <30)", className='stats-label')
            ], className='stats-card')
        ], className='stats-column'),
        html.Div([
            html.Div([
                html.H3(f"{stats['avg_volatility']:.2f}", className='stats-value'),
                html.P("Avg Volatility", className='stats-label')
            ], className='stats-card')
        ], className='stats-column'),
        html.Div([
            html.Div([
                html.H3(stats['top_gainer_7d'], className='stats-value', style={'color': '#00FF88'}),
                html.P("7d Top Gainer", className='stats-label')
            ], className='stats-card')
        ], className='stats-column'),
        html.Div([
            html.Div([
                html.H3(stats['top_loser_7d'], className='stats-value', style={'color': '#FF4676'}),
                html.P("7d Top Loser", className='stats-label')
            ], className='stats-card')
        ], className='stats-column')
    ]
    
    # Data table
    table = dash_table.DataTable(
        id='main-table',
        columns=[
            {'name': 'Symbol', 'id': 'symbol'},
            {'name': 'Price', 'id': 'price', 'type': 'numeric', 'format': {'specifier': '$,.2f'}},
            {'name': '24h Δ%', 'id': 'change_24h', 'type': 'numeric', 'format': {'specifier': '+.1f'}},
            {'name': '7d Δ%', 'id': 'change_7d', 'type': 'numeric', 'format': {'specifier': '+.1f'}},
            {'name': 'RSI', 'id': 'rsi', 'type': 'numeric', 'format': {'specifier': '.1f'}},
            {'name': 'Volume (24h)', 'id': 'volume_24h', 'type': 'numeric', 'format': {'specifier': '$,.0f'}},
            {'name': 'Volatility', 'id': 'volatility', 'type': 'numeric', 'format': {'specifier': '.2f'}},
            {'name': 'Support', 'id': 'support', 'type': 'numeric', 'format': {'specifier': '$,.2f'}},
            {'name': 'Resistance', 'id': 'resistance', 'type': 'numeric', 'format': {'specifier': '$,.2f'}}
        ],
        data=df.sort_values('volume_24h', ascending=False).to_dict('records'),
        sort_action='native',
        filter_action='native',
        style_table={'overflowX': 'auto'},
        style_header={
            'backgroundColor': '#2a2a2a',
            'fontWeight': 'bold'
        },
        style_data_conditional=[
            {
                'if': {
                    'filter_query': '{rsi} > 70',
                    'column_id': 'rsi'
                },
                'backgroundColor': '#FF4676',
                'color': 'white'
            },
            {
                'if': {
                    'filter_query': '{rsi} < 30',
                    'column_id': 'rsi'
                },
                'backgroundColor': '#00FF88',
                'color': 'black'
            }
        ]
    )
    
    return html.Div([
        html.Div(stats_cards, className='stats-row'),
        dcc.Graph(figure=fig),
        html.Div(table, className='data-table-container')
    ])

# ... (keep the rest of the app layout and callbacks unchanged)

# App layout
app.layout = html.Div([
    html.Div([
        html.H1("Crypto Market Dashboard", className='header-title'),
        html.Div([
            html.Span("Last Update: ", className='update-text'),
            html.Span(id='update-time', className='update-time')
        ], className='header-update')
    ], className='header'),
    html.Div(id='dashboard-content'),
    dcc.Interval(id='refresh-interval', interval=REFRESH_INTERVAL*1000)
], className='main-container')

@app.callback(
    [Output('dashboard-content', 'children'),
     Output('update-time', 'children')],
    [Input('refresh-interval', 'n_intervals')]
)
def update_dashboard(_):
    symbols = get_active_symbols()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = list(executor.map(analyze_symbol, symbols))
    valid_data = [r for r in results if r is not None]
    update_time = datetime.utcnow().strftime('%H:%M:%S UTC')
    return create_dashboard(valid_data), update_time

# CSS styles
app.css.append_css({
    'external_url': [
        'https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap'
    ]
})

app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Crypto Market Dashboard</title>
        <style>
            :root {
                --primary-color: #636EFA;
                --background-color: #0a0a0a;
                --card-background: #1a1a1a;
                --text-color: #ffffff;
            }
            
            body {
                font-family: 'Inter', sans-serif;
                background-color: var(--background-color);
                color: var(--text-color);
                margin: 0;
                padding: 20px;
            }
            
            .main-container {
                max-width: 1400px;
                margin: 0 auto;
            }
            
            .header {
                text-align: center;
                margin-bottom: 30px;
            }
            
            .header-title {
                font-size: 2.5rem;
                margin-bottom: 10px;
                color: var(--primary-color);
            }
            
            .stats-row {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 30px;
            }
            
            .stats-card {
                background: var(--card-background);
                padding: 20px;
                border-radius: 10px;
                text-align: center;
            }
            
            .stats-value {
                font-size: 1.8rem;
                margin: 0;
                font-weight: 600;
            }
            
            .stats-label {
                color: #cccccc;
                margin: 5px 0 0;
            }
            
            .data-table-container {
                margin-top: 30px;
                border-radius: 10px;
                overflow: hidden;
            }
            
            .dash-table {
                background-color: var(--card-background) !important;
            }
            
            .dash-table th {
                background-color: #2a2a2a !important;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

#if __name__ == '__main__':
    #app.run_server(debug=True, threaded=True)

if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=8080, debug=True)
