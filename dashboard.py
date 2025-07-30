"""
Performance Dashboard for Crypto Alert Bot
Web-based dashboard to visualize trading performance and system status
"""
import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

import dash
from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import plotly.express as px

# Local modules
from portfolio_manager import PortfolioManager
from trader import Trader

logger = logging.getLogger(__name__)

class Dashboard:
    """Web-based dashboard for cryptocurrency trading performance"""
    
    def __init__(self, data_dir='data', port=8050):
        """Initialize the dashboard.
        
        Args:
            data_dir (str): Directory containing portfolio data
            port (int): Port to run the dashboard on
        """
        self.data_dir = data_dir
        self.port = port
        
        # Initialize portfolio manager
        self.portfolio = PortfolioManager(data_dir=data_dir)
        
        # Initialize trader
        self.trader = Trader(dry_run=True)
        
        # Initialize Dash app
        self.app = dash.Dash(
            __name__,
            external_stylesheets=[dbc.themes.DARKLY],
            meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}]
        )
        
        # Define app layout
        self._setup_layout()
        
        # Define callbacks
        self._setup_callbacks()
        
        logger.info(f"Dashboard initialized on port {port}")
    
    def _setup_layout(self):
        """Setup the dashboard layout."""
        self.app.layout = dbc.Container([
            # Header
            dbc.Row([
                dbc.Col([
                    html.H1("Crypto Alert Bot Dashboard", className="text-center mt-4 mb-4"),
                    html.Hr()
                ])
            ]),
            
            # Tabs
            dcc.Tabs([
                # Performance Tab
                dcc.Tab(label="Performance", children=[
                    dbc.Row([
                        # Portfolio Summary Cards
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H4("Portfolio Value", className="card-title"),
                                    html.H2(id="portfolio-value", className="card-text text-success")
                                ])
                            ], className="mb-4"),
                            dbc.Card([
                                dbc.CardBody([
                                    html.H4("Total Return", className="card-title"),
                                    html.H2(id="total-return", className="card-text")
                                ])
                            ], className="mb-4"),
                            dbc.Card([
                                dbc.CardBody([
                                    html.H4("Win Rate", className="card-title"),
                                    html.H2(id="win-rate", className="card-text text-info")
                                ])
                            ], className="mb-4"),
                            dbc.Card([
                                dbc.CardBody([
                                    html.H4("Profit Factor", className="card-title"),
                                    html.H2(id="profit-factor", className="card-text text-warning")
                                ])
                            ], className="mb-4"),
                        ], width=3),
                        
                        # Charts
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H4("Equity Curve", className="card-title"),
                                    dcc.Graph(id="equity-curve")
                                ])
                            ], className="mb-4"),
                            dbc.Card([
                                dbc.CardBody([
                                    html.H4("Monthly Returns", className="card-title"),
                                    dcc.Graph(id="monthly-returns")
                                ])
                            ], className="mb-4")
                        ], width=9)
                    ], className="mt-4"),
                    
                    # Trade History
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H4("Recent Trades", className="card-title"),
                                    dash_table.DataTable(
                                        id="trades-table",
                                        style_header={
                                            'backgroundColor': '#30363d',
                                            'color': 'white',
                                            'fontWeight': 'bold'
                                        },
                                        style_cell={
                                            'backgroundColor': '#1e2228',
                                            'color': 'white',
                                            'border': '1px solid #30363d'
                                        },
                                        style_data_conditional=[
                                            {
                                                'if': {'filter_query': '{realized_pnl} > 0'},
                                                'color': '#77dd77'
                                            },
                                            {
                                                'if': {'filter_query': '{realized_pnl} <= 0'},
                                                'color': '#ff6961'
                                            }
                                        ]
                                    )
                                ])
                            ], className="mb-4")
                        ], width=12)
                    ])
                ]),
                
                # Positions Tab
                dcc.Tab(label="Positions", children=[
                    dbc.Row([
                        # Position Summary
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H4("Open Positions", className="card-title"),
                                    html.H2(id="open-positions", className="card-text")
                                ])
                            ], className="mb-4"),
                            dbc.Card([
                                dbc.CardBody([
                                    html.H4("Unrealized P&L", className="card-title"),
                                    html.H2(id="unrealized-pnl", className="card-text")
                                ])
                            ], className="mb-4"),
                        ], width=3),
                        
                        # Position Details
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H4("Current Positions", className="card-title"),
                                    dash_table.DataTable(
                                        id="positions-table",
                                        style_header={
                                            'backgroundColor': '#30363d',
                                            'color': 'white',
                                            'fontWeight': 'bold'
                                        },
                                        style_cell={
                                            'backgroundColor': '#1e2228',
                                            'color': 'white',
                                            'border': '1px solid #30363d'
                                        },
                                        style_data_conditional=[
                                            {
                                                'if': {'filter_query': '{unrealized_pnl} > 0'},
                                                'color': '#77dd77'
                                            },
                                            {
                                                'if': {'filter_query': '{unrealized_pnl} <= 0'},
                                                'color': '#ff6961'
                                            }
                                        ]
                                    )
                                ])
                            ], className="mb-4")
                        ], width=9)
                    ], className="mt-4")
                ]),
                
                # Signals Tab
                dcc.Tab(label="Signals", children=[
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H4("Recent Signals", className="card-title"),
                                    dash_table.DataTable(
                                        id="signals-table",
                                        style_header={
                                            'backgroundColor': '#30363d',
                                            'color': 'white',
                                            'fontWeight': 'bold'
                                        },
                                        style_cell={
                                            'backgroundColor': '#1e2228',
                                            'color': 'white',
                                            'border': '1px solid #30363d'
                                        }
                                    )
                                ])
                            ], className="mb-4")
                        ], width=12)
                    ], className="mt-4")
                ]),
                
                # Settings Tab
                dcc.Tab(label="Settings", children=[
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H4("System Settings", className="card-title"),
                                    html.Div([
                                        dbc.FormGroup([
                                            dbc.Label("Volume Threshold"),
                                            dcc.Slider(
                                                id="volume-threshold",
                                                min=1,
                                                max=5,
                                                step=0.1,
                                                value=2.0,
                                                marks={i: str(i) for i in range(1, 6)},
                                                className="mb-4"
                                            )
                                        ]),
                                        dbc.FormGroup([
                                            dbc.Label("Price Change Threshold"),
                                            dcc.Slider(
                                                id="price-change-threshold",
                                                min=0.5,
                                                max=3,
                                                step=0.1,
                                                value=1.5,
                                                marks={i/2: str(i/2) for i in range(1, 7)},
                                                className="mb-4"
                                            )
                                        ]),
                                        dbc.FormGroup([
                                            dbc.Label("Risk/Reward Ratio"),
                                            dcc.Slider(
                                                id="risk-reward-ratio",
                                                min=1,
                                                max=4,
                                                step=0.1,
                                                value=2.0,
                                                marks={i: str(i) for i in range(1, 5)},
                                                className="mb-4"
                                            )
                                        ]),
                                    ]),
                                    dbc.Button(
                                        "Save Settings",
                                        id="save-settings",
                                        color="primary",
                                        className="mt-3"
                                    ),
                                    html.Div(id="settings-saved", className="mt-2")
                                ])
                            ], className="mb-4")
                        ], width=6),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H4("Strategy Settings", className="card-title"),
                                    dbc.Checklist(
                                        options=[
                                            {"label": "Volume + Price Spike", "value": "volume_spike"},
                                            {"label": "Moving Average Cross", "value": "ma_cross"},
                                            {"label": "Breakout", "value": "breakout"}
                                        ],
                                        value=["volume_spike", "ma_cross", "breakout"],
                                        id="strategy-checklist",
                                        switch=True,
                                        className="mb-4"
                                    ),
                                    html.H5("Watchlist", className="mt-4"),
                                    dbc.InputGroup([
                                        dbc.Input(id="symbol-input", placeholder="Add symbol (e.g., BTC/USDT)"),
                                        dbc.InputGroupAddon(
                                            dbc.Button("Add", id="add-symbol", color="success"),
                                            addon_type="append"
                                        )
                                    ], className="mb-3"),
                                    html.Div(id="watchlist-display")
                                ])
                            ], className="mb-4")
                        ], width=6)
                    ], className="mt-4")
                ])
            ]),
            
            # Footer
            dbc.Row([
                dbc.Col([
                    html.Hr(),
                    html.P(
                        "Crypto Alert Bot Dashboard - Refresh interval: 60 seconds",
                        className="text-center text-muted"
                    ),
                    dcc.Interval(
                        id="interval-component",
                        interval=60 * 1000,  # 60 seconds
                        n_intervals=0
                    )
                ])
            ])
        ], fluid=True)
    
    def _setup_callbacks(self):
        """Setup dashboard callbacks."""
        # Update portfolio metrics
        @self.app.callback(
            [
                Output("portfolio-value", "children"),
                Output("total-return", "children"),
                Output("total-return", "className"),
                Output("win-rate", "children"),
                Output("profit-factor", "children"),
                Output("open-positions", "children"),
                Output("unrealized-pnl", "children"),
                Output("unrealized-pnl", "className")
            ],
            [Input("interval-component", "n_intervals")]
        )
        def update_metrics(n_intervals):
            """Update portfolio metrics."""
            try:
                # Get portfolio stats
                stats = self.portfolio.get_portfolio_stats()
                position_summary = self.portfolio.get_position_summary()
                
                # Format metrics
                portfolio_value = f"${stats['current_value']:,.2f}"
                
                total_return = f"{stats['overall_return_percent']:+.2f}%"
                total_return_class = "card-text text-success" if stats['overall_return'] >= 0 else "card-text text-danger"
                
                win_rate = f"{stats['win_rate']:.1f}%"
                profit_factor = f"{stats['profit_factor']:.2f}"
                
                open_positions = str(position_summary['total_positions'])
                
                unrealized_pnl = f"{position_summary['total_pnl']:+,.2f} USDT"
                unrealized_pnl_class = "card-text text-success" if position_summary['total_pnl'] >= 0 else "card-text text-danger"
                
                return (
                    portfolio_value,
                    total_return,
                    total_return_class,
                    win_rate,
                    profit_factor,
                    open_positions,
                    unrealized_pnl,
                    unrealized_pnl_class
                )
            except Exception as e:
                logger.error(f"Error updating metrics: {str(e)}")
                return (
                    "$0.00",
                    "0.00%",
                    "card-text",
                    "0.0%",
                    "0.00",
                    "0",
                    "$0.00",
                    "card-text"
                )
        
        # Update equity curve chart
        @self.app.callback(
            Output("equity-curve", "figure"),
            [Input("interval-component", "n_intervals")]
        )
        def update_equity_curve(n_intervals):
            """Update equity curve chart."""
            try:
                # Load daily performance
                daily_perf_path = os.path.join(self.data_dir, 'daily_performance.json')
                
                if not os.path.exists(daily_perf_path):
                    # Return empty chart
                    return {
                        "data": [go.Scatter(x=[], y=[], mode="lines")],
                        "layout": go.Layout(
                            title="Equity Curve",
                            xaxis={"title": "Date"},
                            yaxis={"title": "Portfolio Value (USDT)"},
                            template="plotly_dark"
                        )
                    }
                
                with open(daily_perf_path, 'r') as f:
                    daily_perf = json.load(f)
                
                # Convert to DataFrame
                df = pd.DataFrame.from_dict(daily_perf, orient='index')
                df.index = pd.to_datetime(df.index)
                df = df.sort_index()
                
                # Create figure
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=df.index,
                    y=df['closing_value'],
                    mode='lines',
                    name='Portfolio Value',
                    line=dict(color='#00b3ff', width=2)
                ))
                
                fig.update_layout(
                    title="Equity Curve",
                    xaxis_title="Date",
                    yaxis_title="Portfolio Value (USDT)",
                    template="plotly_dark",
                    height=400
                )
                
                return fig
            
            except Exception as e:
                logger.error(f"Error updating equity curve: {str(e)}")
                return {
                    "data": [go.Scatter(x=[], y=[], mode="lines")],
                    "layout": go.Layout(
                        title="Equity Curve",
                        xaxis={"title": "Date"},
                        yaxis={"title": "Portfolio Value (USDT)"},
                        template="plotly_dark"
                    )
                }
        
        # Update monthly returns chart
        @self.app.callback(
            Output("monthly-returns", "figure"),
            [Input("interval-component", "n_intervals")]
        )
        def update_monthly_returns(n_intervals):
            """Update monthly returns chart."""
            try:
                # Load monthly performance
                monthly_perf_path = os.path.join(self.data_dir, 'monthly_performance.json')
                
                if not os.path.exists(monthly_perf_path):
                    # Return empty chart
                    return {
                        "data": [go.Bar(x=[], y=[])],
                        "layout": go.Layout(
                            title="Monthly Returns",
                            xaxis={"title": "Month"},
                            yaxis={"title": "Return (%)"},
                            template="plotly_dark"
                        )
                    }
                
                with open(monthly_perf_path, 'r') as f:
                    monthly_perf = json.load(f)
                
                # Extract months and returns
                months = list(monthly_perf.keys())
                returns = [monthly_perf[m]['change_percent'] for m in months]
                
                # Create color list
                colors = ['#77dd77' if r >= 0 else '#ff6961' for r in returns]
                
                # Create figure
                fig = go.Figure()
                
                fig.add_trace(go.Bar(
                    x=months,
                    y=returns,
                    marker_color=colors,
                    name='Monthly Return'
                ))
                
                fig.update_layout(
                    title="Monthly Returns",
                    xaxis_title="Month",
                    yaxis_title="Return (%)",
                    template="plotly_dark",
                    height=400
                )
                
                return fig
            
            except Exception as e:
                logger.error(f"Error updating monthly returns: {str(e)}")
                return {
                    "data": [go.Bar(x=[], y=[])],
                    "layout": go.Layout(
                        title="Monthly Returns",
                        xaxis={"title": "Month"},
                        yaxis={"title": "Return (%)"},
                        template="plotly_dark"
                    )
                }
        
        # Update trades table
        @self.app.callback(
            Output("trades-table", "data"),
            Output("trades-table", "columns"),
            [Input("interval-component", "n_intervals")]
        )
        def update_trades_table(n_intervals):
            """Update trades table."""
            try:
                # Load trades
                trades_path = os.path.join(self.data_dir, 'trades.json')
                
                if not os.path.exists(trades_path):
                    # Return empty table
                    columns = [
                        {"name": "Symbol", "id": "symbol"},
                        {"name": "Entry Price", "id": "entry_price"},
                        {"name": "Exit Price", "id": "exit_price"},
                        {"name": "P&L", "id": "realized_pnl"},
                        {"name": "P&L %", "id": "realized_pnl_percent"},
                        {"name": "Exit Time", "id": "exit_time"},
                        {"name": "Strategy", "id": "strategy"}
                    ]
                    return [], columns
                
                with open(trades_path, 'r') as f:
                    trades = json.load(f)
                
                # Sort trades by exit time (newest first)
                trades = sorted(trades, key=lambda x: x['exit_time'], reverse=True)
                
                # Limit to last 20 trades
                trades = trades[:20]
                
                # Format trades for display
                for trade in trades:
                    trade['realized_pnl'] = f"{trade['realized_pnl']:.2f}"
                    trade['realized_pnl_percent'] = f"{trade['realized_pnl_percent']:.2f}%"
                    trade['entry_price'] = f"{trade['entry_price']:.2f}"
                    trade['exit_price'] = f"{trade['exit_price']:.2f}"
                
                # Define columns
                columns = [
                    {"name": "Symbol", "id": "symbol"},
                    {"name": "Entry Price", "id": "entry_price"},
                    {"name": "Exit Price", "id": "exit_price"},
                    {"name": "P&L", "id": "realized_pnl"},
                    {"name": "P&L %", "id": "realized_pnl_percent"},
                    {"name": "Exit Time", "id": "exit_time"},
                    {"name": "Strategy", "id": "strategy"}
                ]
                
                return trades, columns
            
            except Exception as e:
                logger.error(f"Error updating trades table: {str(e)}")
                columns = [
                    {"name": "Symbol", "id": "symbol"},
                    {"name": "Entry Price", "id": "entry_price"},
                    {"name": "Exit Price", "id": "exit_price"},
                    {"name": "P&L", "id": "realized_pnl"},
                    {"name": "P&L %", "id": "realized_pnl_percent"},
                    {"name": "Exit Time", "id": "exit_time"},
                    {"name": "Strategy", "id": "strategy"}
                ]
                return [], columns
        
        # Update positions table
        @self.app.callback(
            Output("positions-table", "data"),
            Output("positions-table", "columns"),
            [Input("interval-component", "n_intervals")]
        )
        def update_positions_table(n_intervals):
            """Update positions table."""
            try:
                # Load positions
                positions_path = os.path.join(self.data_dir, 'positions.json')
                
                if not os.path.exists(positions_path):
                    # Return empty table
                    columns = [
                        {"name": "Symbol", "id": "symbol"},
                        {"name": "Entry Price", "id": "entry_price"},
                        {"name": "Current Price", "id": "current_price"},
                        {"name": "Quantity", "id": "quantity"},
                        {"name": "Current Value", "id": "current_value"},
                        {"name": "Unrealized P&L", "id": "unrealized_pnl"},
                        {"name": "Unrealized P&L %", "id": "unrealized_pnl_percent"}
                    ]
                    return [], columns
                
                with open(positions_path, 'r') as f:
                    positions = json.load(f)
                
                # Convert to list
                positions_list = list(positions.values())
                
                # Format positions for display
                for position in positions_list:
                    position['entry_price'] = f"{position['entry_price']:.2f}"
                    position['current_price'] = f"{position['current_price']:.2f}"
                    position['current_value'] = f"{position['current_value']:.2f}"
                    position['unrealized_pnl'] = f"{position['unrealized_pnl']:.2f}"
                    position['unrealized_pnl_percent'] = f"{position['unrealized_pnl_percent']:.2f}%"
                
                # Define columns
                columns = [
                    {"name": "Symbol", "id": "symbol"},
                    {"name": "Entry Price", "id": "entry_price"},
                    {"name": "Current Price", "id": "current_price"},
                    {"name": "Quantity", "id": "quantity"},
                    {"name": "Current Value", "id": "current_value"},
                    {"name": "Unrealized P&L", "id": "unrealized_pnl"},
                    {"name": "Unrealized P&L %", "id": "unrealized_pnl_percent"}
                ]
                
                return positions_list, columns
            
            except Exception as e:
                logger.error(f"Error updating positions table: {str(e)}")
                columns = [
                    {"name": "Symbol", "id": "symbol"},
                    {"name": "Entry Price", "id": "entry_price"},
                    {"name": "Current Price", "id": "current_price"},
                    {"name": "Quantity", "id": "quantity"},
                    {"name": "Current Value", "id": "current_value"},
                    {"name": "Unrealized P&L", "id": "unrealized_pnl"},
                    {"name": "Unrealized P&L %", "id": "unrealized_pnl_percent"}
                ]
                return [], columns
    
    def run(self):
        """Run the dashboard server."""
        self.app.run_server(debug=False, host='0.0.0.0', port=self.port)


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run dashboard
    dashboard = Dashboard()
    dashboard.run()
