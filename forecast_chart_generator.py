"""
Advanced Forecast Chart Generator for Cryptocurrency Trading
Creates intelligent visual forecasts with regime zones, confidence scores, and predictions
"""
import os
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from mplfinance.original_flavor import candlestick_ohlc
import matplotlib.patches as patches
from matplotlib.patches import Rectangle
import seaborn as sns

# Set style for professional charts
plt.style.use('dark_background')
sns.set_palette("husl")

logger = logging.getLogger(__name__)

class ForecastChartGenerator:
    """Creates advanced forecast charts with regime detection and predictions"""
    
    def __init__(self, output_dir='charts'):
        """Initialize the forecast chart generator.
        
        Args:
            output_dir (str): Directory to save chart images
        """
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Chart styling configuration
        self.colors = {
            'bullish': '#00ff88',
            'bearish': '#ff4444', 
            'neutral': '#ffaa00',
            'background': '#0a0a0a',
            'grid': '#333333',
            'text': '#ffffff',
            'entry': '#00aaff',
            'stop': '#ff3366',
            'target': '#00ff66',
            'confidence_high': '#00ff00',
            'confidence_medium': '#ffff00',
            'confidence_low': '#ff6600'
        }
        
        logger.info(f"Forecast chart generator initialized with output directory: {output_dir}")
    
    def generate_forecast_chart(self, df, symbol, timeframe, forecast_data, 
                              trade_context=None, regime_zones=None):
        """Generate an advanced forecast chart with regime zones and predictions.
        
        Args:
            df (DataFrame): Historical OHLCV data
            symbol (str): Symbol name (e.g., 'BTC/USDT')
            timeframe (str): Timeframe (e.g., '1h', '4h')
            forecast_data (dict): Forecast information containing:
                - prediction: 'bullish', 'bearish', 'neutral'
                - confidence: float (0-100)
                - target_price: float
                - probability: float
                - horizon: int (periods ahead)
            trade_context (dict, optional): Current trade context with:
                - strategy: str
                - leverage: float
                - entry_price: float
                - stop_loss: float
                - take_profit: float
            regime_zones (list, optional): List of regime zone dicts with:
                - start_idx: int
                - end_idx: int
                - regime: str ('bullish', 'bearish', 'neutral')
                - strength: float (0-1)
                
        Returns:
            str: Path to the generated forecast chart image
        """
        # Prepare data
        df = df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = df['timestamp'].map(mdates.date2num)
        
        # Create figure with subplots
        fig = plt.figure(figsize=(16, 12), facecolor=self.colors['background'])
        
        # Main price chart (70% height)
        ax_main = plt.subplot2grid((4, 1), (0, 0), rowspan=2, facecolor=self.colors['background'])
        
        # Volume chart (15% height)
        ax_volume = plt.subplot2grid((4, 1), (2, 0), facecolor=self.colors['background'])
        
        # Indicators chart (15% height)
        ax_indicators = plt.subplot2grid((4, 1), (3, 0), facecolor=self.colors['background'])
        
        # Plot regime zones first (background)
        if regime_zones:
            self._plot_regime_zones(ax_main, df, regime_zones)
        
        # Plot candlesticks
        ohlc_data = df[['date', 'open', 'high', 'low', 'close']].values
        candlestick_ohlc(ax_main, ohlc_data, width=0.6, 
                        colorup=self.colors['bullish'], 
                        colordown=self.colors['bearish'], 
                        alpha=0.9)
        
        # Add technical indicators
        self._add_technical_indicators(ax_main, df)
        
        # Plot forecast projection
        self._plot_forecast_projection(ax_main, df, forecast_data)
        
        # Add trade context markers
        if trade_context:
            self._add_trade_markers(ax_main, trade_context)
        
        # Plot volume
        self._plot_volume(ax_volume, df)
        
        # Plot secondary indicators (RSI, MACD)
        self._plot_secondary_indicators(ax_indicators, df)
        
        # Add confidence score annotation
        self._add_confidence_annotation(ax_main, forecast_data)
        
        # Format main chart
        self._format_main_chart(ax_main, symbol, timeframe, forecast_data)
        
        # Format volume chart
        self._format_volume_chart(ax_volume)
        
        # Format indicators chart
        self._format_indicators_chart(ax_indicators)
        
        # Add watermark/branding
        self._add_branding(fig)
        
        # Save chart
        filename = self._save_chart(fig, symbol, timeframe, forecast_data)
        
        plt.close(fig)
        logger.info(f"Generated forecast chart: {filename}")
        return filename
    
    def _plot_regime_zones(self, ax, df, regime_zones):
        """Plot regime zones as background colored areas."""
        for zone in regime_zones:
            start_idx = max(0, zone['start_idx'])
            end_idx = min(len(df) - 1, zone['end_idx'])
            
            if start_idx >= len(df) or end_idx < 0:
                continue
                
            start_date = df.iloc[start_idx]['date']
            end_date = df.iloc[end_idx]['date']
            
            # Get price range for the zone
            zone_data = df.iloc[start_idx:end_idx + 1]
            y_min = zone_data['low'].min()
            y_max = zone_data['high'].max()
            
            # Color based on regime
            regime_color = self.colors.get(zone['regime'], self.colors['neutral'])
            alpha = 0.15 * zone.get('strength', 0.5)
            
            # Add regime zone rectangle
            rect = Rectangle((start_date, y_min), end_date - start_date, y_max - y_min,
                           facecolor=regime_color, alpha=alpha, edgecolor='none')
            ax.add_patch(rect)
            
            # Add regime label
            mid_date = start_date + (end_date - start_date) / 2
            mid_price = y_min + (y_max - y_min) * 0.9
            ax.text(mid_date, mid_price, zone['regime'].upper(), 
                   color=regime_color, fontsize=9, ha='center', 
                   weight='bold', alpha=0.7)
    
    def _add_technical_indicators(self, ax, df):
        """Add technical indicators to the main chart."""
        # Moving averages
        periods = [9, 21, 50]
        colors = ['#00aaff', '#ff6600', '#ffffff']
        
        for period, color in zip(periods, colors):
            if len(df) >= period:
                ma = df['close'].rolling(window=period).mean()
                ax.plot(df['date'], ma, color=color, linewidth=1.5, 
                       alpha=0.8, label=f'MA{period}')
        
        # Bollinger Bands
        if len(df) >= 20:
            ma20 = df['close'].rolling(window=20).mean()
            std20 = df['close'].rolling(window=20).std()
            bb_upper = ma20 + (std20 * 2)
            bb_lower = ma20 - (std20 * 2)
            
            ax.plot(df['date'], bb_upper, '--', color='#888888', 
                   linewidth=1, alpha=0.6, label='BB Upper')
            ax.plot(df['date'], bb_lower, '--', color='#888888', 
                   linewidth=1, alpha=0.6, label='BB Lower')
            ax.fill_between(df['date'], bb_upper, bb_lower, 
                          alpha=0.05, color='#888888')
    
    def _plot_forecast_projection(self, ax, df, forecast_data):
        """Plot forecast projection line and target zone."""
        if not forecast_data or len(df) == 0:
            return
            
        # Get last price and date
        last_price = df['close'].iloc[-1]
        last_date = df['date'].iloc[-1]
        
        # Calculate forecast timeline
        horizon = forecast_data.get('horizon', 24)  # Default 24 periods
        target_price = forecast_data.get('target_price', last_price)
        
        # Create forecast dates
        date_range = pd.date_range(
            start=df['timestamp'].iloc[-1], 
            periods=horizon + 1, 
            freq='1H' if '1h' in str(forecast_data.get('timeframe', '1h')) else '4H'
        )
        forecast_dates = [mdates.date2num(d) for d in date_range]
        
        # Create forecast price path (simple linear for now, can be enhanced)
        price_change = target_price - last_price
        forecast_prices = [last_price + (price_change * i / horizon) for i in range(horizon + 1)]
        
        # Plot forecast line
        forecast_color = self.colors[forecast_data.get('prediction', 'neutral')]
        ax.plot(forecast_dates, forecast_prices, '--', color=forecast_color, 
               linewidth=3, alpha=0.8, label='Forecast Path')
        
        # Add target zone
        confidence = forecast_data.get('confidence', 50) / 100
        price_range = abs(target_price - last_price) * (1 - confidence) * 0.5
        
        upper_bound = [p + price_range for p in forecast_prices]
        lower_bound = [p - price_range for p in forecast_prices]
        
        ax.fill_between(forecast_dates, upper_bound, lower_bound, 
                       alpha=0.2, color=forecast_color, label='Confidence Zone')
        
        # Mark target price
        ax.scatter([forecast_dates[-1]], [target_price], 
                  color=forecast_color, s=100, marker='*', 
                  zorder=5, label=f'Target: {target_price:.6f}')
    
    def _add_trade_markers(self, ax, trade_context):
        """Add trade entry, stop loss, and take profit markers."""
        if 'entry_price' in trade_context:
            ax.axhline(y=trade_context['entry_price'], 
                      color=self.colors['entry'], linestyle='-', 
                      linewidth=2, alpha=0.8, 
                      label=f"Entry: {trade_context['entry_price']:.6f}")
        
        if 'stop_loss' in trade_context:
            ax.axhline(y=trade_context['stop_loss'], 
                      color=self.colors['stop'], linestyle='-', 
                      linewidth=2, alpha=0.8, 
                      label=f"Stop: {trade_context['stop_loss']:.6f}")
        
        if 'take_profit' in trade_context:
            ax.axhline(y=trade_context['take_profit'], 
                      color=self.colors['target'], linestyle='-', 
                      linewidth=2, alpha=0.8, 
                      label=f"Target: {trade_context['take_profit']:.6f}")
    
    def _plot_volume(self, ax, df):
        """Plot volume bars."""
        colors = [self.colors['bullish'] if close > open_price else self.colors['bearish'] 
                 for close, open_price in zip(df['close'], df['open'])]
        ax.bar(df['date'], df['volume'], color=colors, alpha=0.6, width=0.6)
        ax.set_ylabel('Volume', color=self.colors['text'])
    
    def _plot_secondary_indicators(self, ax, df):
        """Plot RSI and other secondary indicators."""
        if len(df) < 14:
            return
            
        # Calculate RSI
        delta = df['close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        # Plot RSI
        ax.plot(df['date'], rsi, color='#ff6600', linewidth=2, label='RSI')
        ax.axhline(y=70, color=self.colors['bearish'], linestyle='--', alpha=0.5)
        ax.axhline(y=30, color=self.colors['bullish'], linestyle='--', alpha=0.5)
        ax.set_ylim(0, 100)
        ax.set_ylabel('RSI', color=self.colors['text'])
    
    def _add_confidence_annotation(self, ax, forecast_data):
        """Add confidence score annotation to the chart."""
        confidence = forecast_data.get('confidence', 50)
        prediction = forecast_data.get('prediction', 'neutral').upper()
        
        # Choose color based on confidence level
        if confidence >= 80:
            conf_color = self.colors['confidence_high']
        elif confidence >= 60:
            conf_color = self.colors['confidence_medium']
        else:
            conf_color = self.colors['confidence_low']
        
        # Add confidence box
        bbox_props = dict(boxstyle="round,pad=0.3", facecolor=conf_color, alpha=0.8)
        ax.text(0.02, 0.98, f"{prediction}\nConfidence: {confidence:.0f}%", 
               transform=ax.transAxes, fontsize=12, weight='bold',
               verticalalignment='top', bbox=bbox_props, color='black')
    
    def _format_main_chart(self, ax, symbol, timeframe, forecast_data):
        """Format the main price chart."""
        ax.set_facecolor(self.colors['background'])
        ax.grid(True, alpha=0.3, color=self.colors['grid'])
        ax.legend(loc='upper left', framealpha=0.8)
        ax.set_ylabel('Price (USDT)', color=self.colors['text'], fontsize=12)
        
        # Format x-axis
        ax.xaxis_date()
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        
        # Title with forecast info
        strategy = forecast_data.get('strategy', 'AI Forecast')
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        title = f"🧠 {symbol} {timeframe} | {strategy} | {current_time}"
        ax.set_title(title, color=self.colors['text'], fontsize=14, weight='bold', pad=20)
    
    def _format_volume_chart(self, ax):
        """Format the volume chart."""
        ax.set_facecolor(self.colors['background'])
        ax.grid(True, alpha=0.3, color=self.colors['grid'])
        ax.tick_params(colors=self.colors['text'])
    
    def _format_indicators_chart(self, ax):
        """Format the indicators chart."""
        ax.set_facecolor(self.colors['background'])
        ax.grid(True, alpha=0.3, color=self.colors['grid'])
        ax.tick_params(colors=self.colors['text'])
        ax.xaxis_date()
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    def _add_branding(self, fig):
        """Add subtle branding/watermark to the chart."""
        fig.text(0.99, 0.01, 'CryptoBot Pro • AI-Powered Trading Intelligence', 
                ha='right', va='bottom', fontsize=8, alpha=0.6, 
                color=self.colors['text'])
    
    def _save_chart(self, fig, symbol, timeframe, forecast_data):
        """Save the chart and return filename."""
        clean_symbol = symbol.replace('/', '_')
        prediction = forecast_data.get('prediction', 'forecast')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{self.output_dir}/forecast_{clean_symbol}_{timeframe}_{prediction}_{timestamp}.png"
        
        plt.tight_layout()
        fig.savefig(filename, dpi=150, bbox_inches='tight', 
                   facecolor=self.colors['background'], 
                   edgecolor='none')
        
        return filename

    def generate_simple_forecast_chart(self, df, symbol, forecast_data):
        """Generate a simplified forecast chart for quick updates.
        
        Args:
            df (DataFrame): Recent OHLCV data (last 50-100 candles)
            symbol (str): Symbol name
            forecast_data (dict): Forecast information
            
        Returns:
            str: Path to generated chart
        """
        # Simplified version for faster generation
        df = df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = df['timestamp'].map(mdates.date2num)
        
        fig, ax = plt.subplots(figsize=(12, 8), facecolor=self.colors['background'])
        ax.set_facecolor(self.colors['background'])
        
        # Plot candlesticks
        ohlc_data = df[['date', 'open', 'high', 'low', 'close']].values
        candlestick_ohlc(ax, ohlc_data, width=0.6, 
                        colorup=self.colors['bullish'], 
                        colordown=self.colors['bearish'], 
                        alpha=0.9)
        
        # Add simple moving averages
        if len(df) >= 21:
            ma21 = df['close'].rolling(window=21).mean()
            ax.plot(df['date'], ma21, color='#ff6600', linewidth=2, label='MA21')
        
        # Add forecast projection
        self._plot_forecast_projection(ax, df, forecast_data)
        
        # Add confidence annotation
        self._add_confidence_annotation(ax, forecast_data)
        
        # Format chart
        ax.grid(True, alpha=0.3, color=self.colors['grid'])
        ax.legend(loc='upper left', framealpha=0.8)
        ax.set_ylabel('Price (USDT)', color=self.colors['text'])
        ax.xaxis_date()
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        # Title
        prediction = forecast_data.get('prediction', 'neutral').upper()
        confidence = forecast_data.get('confidence', 50)
        ax.set_title(f"🔮 {symbol} Forecast: {prediction} ({confidence:.0f}%)", 
                    color=self.colors['text'], fontsize=14, weight='bold')
        
        # Save
        filename = self._save_chart(fig, symbol, 'quick', forecast_data)
        plt.close(fig)
        
        return filename
