"""
Chart Generator Module for Cryptocurrency Trading Alerts
Creates visual charts with technical indicators for Telegram alerts
"""
import os
import logging
import numpy as np
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from mplfinance.original_flavor import candlestick_ohlc

logger = logging.getLogger(__name__)

class ChartGenerator:
    """Creates technical analysis charts for trading alerts"""
    
    def __init__(self, output_dir='charts'):
        """Initialize the chart generator.
        
        Args:
            output_dir (str): Directory to save chart images
        """
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        logger.info(f"Chart generator initialized with output directory: {output_dir}")
        
    def generate_chart(self, df, symbol, timeframe, indicators=None, 
                      entry_price=None, stop_loss=None, take_profit=None):
        """Generate a technical analysis chart.
        
        Args:
            df (DataFrame): OHLCV data
            symbol (str): Symbol name (e.g., 'BTC/USDT')
            timeframe (str): Timeframe (e.g., '1h', '4h')
            indicators (dict): Dictionary of indicators to plot
            entry_price (float, optional): Entry price to mark on chart
            stop_loss (float, optional): Stop loss price to mark on chart
            take_profit (float, optional): Take profit price to mark on chart
            
        Returns:
            str: Path to the generated chart image
        """
        # Convert timestamp to matplotlib date format
        df = df.copy()
        df['date'] = df['timestamp'].map(mdates.date2num)
        
        # Setup the figure
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Plot candlesticks
        ohlc_data = df[['date', 'open', 'high', 'low', 'close']].values
        candlestick_ohlc(ax, ohlc_data, width=0.6, colorup='green', colordown='red', alpha=0.8)
        
        # Plot volume as bars on a secondary axis
        ax_volume = ax.twinx()
        colors = np.where(df['close'] > df['open'], 'green', 'red')
        ax_volume.bar(df['date'], df['volume'], color=colors, alpha=0.3)
        ax_volume.set_ylim(0, df['volume'].max() * 3)
        ax_volume.set_ylabel('Volume')
        
        # Add indicators if provided
        if indicators:
            # Moving Averages
            if 'ma' in indicators:
                for period, color in indicators['ma']:
                    if f'ma_{period}' not in df.columns:
                        df[f'ma_{period}'] = df['close'].rolling(window=period).mean()
                    ax.plot(df['date'], df[f'ma_{period}'], 
                            label=f'MA ({period})', color=color, linewidth=1.5)
            
            # Bollinger Bands
            if 'bollinger' in indicators:
                period, std_dev = indicators['bollinger']
                if f'ma_{period}' not in df.columns:
                    df[f'ma_{period}'] = df['close'].rolling(window=period).mean()
                df['bb_upper'] = df[f'ma_{period}'] + (df['close'].rolling(window=period).std() * std_dev)
                df['bb_lower'] = df[f'ma_{period}'] - (df['close'].rolling(window=period).std() * std_dev)
                ax.plot(df['date'], df['bb_upper'], '--', label=f'Upper BB ({period}, {std_dev})', color='gray', linewidth=1)
                ax.plot(df['date'], df['bb_lower'], '--', label=f'Lower BB ({period}, {std_dev})', color='gray', linewidth=1)
                ax.fill_between(df['date'], df['bb_upper'], df['bb_lower'], alpha=0.1, color='gray')
                
            # RSI
            if 'rsi' in indicators:
                period = indicators['rsi']
                delta = df['close'].diff()
                gain = delta.clip(lower=0)
                loss = -delta.clip(upper=0)
                avg_gain = gain.rolling(window=period).mean()
                avg_loss = loss.rolling(window=period).mean()
                rs = avg_gain / avg_loss
                df['rsi'] = 100 - (100 / (1 + rs))
                
                # Add subplot for RSI
                ax_rsi = fig.add_axes([0.125, 0.06, 0.775, 0.2])
                ax_rsi.plot(df['date'], df['rsi'], color='purple', linewidth=1.5)
                ax_rsi.axhline(y=70, color='r', linestyle='--', alpha=0.5)
                ax_rsi.axhline(y=30, color='g', linestyle='--', alpha=0.5)
                ax_rsi.set_ylabel('RSI')
                ax_rsi.set_ylim(0, 100)
                
                # Format RSI x-axis
                ax_rsi.set_xticklabels([])
                
        # Mark entry, stop loss, and take profit if provided
        if entry_price:
            ax.axhline(y=entry_price, color='blue', linestyle='-', linewidth=2, alpha=0.7,
                      label=f'Entry: {entry_price:.8f}')
        if stop_loss:
            ax.axhline(y=stop_loss, color='red', linestyle='-', linewidth=2, alpha=0.7,
                      label=f'Stop: {stop_loss:.8f}')
        if take_profit:
            ax.axhline(y=take_profit, color='green', linestyle='-', linewidth=2, alpha=0.7,
                      label=f'Target: {take_profit:.8f}')
            
        # Format x-axis
        ax.xaxis_date()
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        plt.xticks(rotation=45)
        
        # Add grid, legend and labels
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper left')
        ax.set_ylabel('Price')
        
        # Adjust margins
        plt.subplots_adjust(left=0.125, right=0.9, bottom=0.3, top=0.95)
        
        # Title
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        plt.title(f'{symbol} - {timeframe} Chart ({current_time})')
        
        # Save chart
        clean_symbol = symbol.replace('/', '_')
        filename = f"{self.output_dir}/{clean_symbol}_{timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(filename, dpi=100)
        plt.close()
        
        logger.info(f"Generated chart: {filename}")
        return filename
    
    def generate_alert_chart(self, df, symbol, timeframe, alert_type, 
                           entry_price, stop_loss, take_profit):
        """Generate a chart specifically for a trading alert.
        
        Args:
            df (DataFrame): OHLCV data
            symbol (str): Symbol name (e.g., 'BTC/USDT')
            timeframe (str): Timeframe (e.g., '1h', '4h')
            alert_type (str): Type of alert (e.g., 'MA Cross', 'Breakout')
            entry_price (float): Entry price
            stop_loss (float): Stop loss price
            take_profit (float): Take profit price
            
        Returns:
            str: Path to the generated chart image
        """
        indicators = {}
        
        # Add relevant indicators based on alert type
        if alert_type == 'MA Cross':
            indicators['ma'] = [(9, 'blue'), (21, 'red')]
            
        elif alert_type == 'Breakout':
            indicators['ma'] = [(20, 'blue')]
            indicators['bollinger'] = (20, 2)
            
        elif alert_type == 'Volume + Price Spike':
            indicators['ma'] = [(20, 'blue')]
            
        # Always add RSI
        indicators['rsi'] = 14
        
        return self.generate_chart(
            df, symbol, timeframe, indicators, 
            entry_price, stop_loss, take_profit
        )
