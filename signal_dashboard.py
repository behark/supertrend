#!/usr/bin/env python
"""
Live Signal Confidence Dashboard
-------------------------------
Tracks signal metrics and generates visual insights:
- Signal confidence distribution (>95%, >98%, etc.)
- Win-rate curves by timeframe and coin
- Signal quality trends over time
"""
import os
import sys
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import seaborn as sns

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SignalDashboard:
    """Track and visualize signal metrics for Bidget"""
    
    def __init__(self, data_dir='data'):
        """Initialize the dashboard
        
        Args:
            data_dir (str): Directory to store dashboard data
        """
        self.data_dir = data_dir
        self.signals_file = os.path.join(data_dir, 'signal_metrics.json')
        self.signals_df_file = os.path.join(data_dir, 'signal_metrics.csv')
        self.dashboard_file = os.path.join(data_dir, 'dashboard_stats.json')
        self.signals = []
        self.dashboard_stats = {
            'last_update': datetime.now().isoformat(),
            'confidence_bins': {
                '90-92%': 0,
                '92-95%': 0,
                '95-98%': 0,
                '98-100%': 0
            },
            'win_rate_by_timeframe': {},
            'win_rate_by_symbol': {},
            'signals_today': 0,
            'signals_total': 0,
            'avg_probability': 0.0,
            'best_performing_pairs': [],
            'best_performing_timeframes': []
        }
        
        # Load existing data if available
        self._load_data()
    
    def _load_data(self):
        """Load signal metrics data from disk"""
        try:
            # Create data directory if it doesn't exist
            os.makedirs(self.data_dir, exist_ok=True)
            
            # Load signals
            if os.path.exists(self.signals_file):
                with open(self.signals_file, 'r') as f:
                    self.signals = json.load(f)
                logger.info(f"Loaded {len(self.signals)} signal records")
            
            # Load dashboard stats
            if os.path.exists(self.dashboard_file):
                with open(self.dashboard_file, 'r') as f:
                    self.dashboard_stats = json.load(f)
                logger.info(f"Loaded dashboard stats from {self.dashboard_file}")
                
        except Exception as e:
            logger.error(f"Error loading dashboard data: {str(e)}")
    
    def _save_data(self):
        """Save signal metrics data to disk"""
        try:
            # Create data directory if it doesn't exist
            os.makedirs(self.data_dir, exist_ok=True)
            
            # Save signals
            with open(self.signals_file, 'w') as f:
                json.dump(self.signals, f, indent=2)
            
            # Save dashboard stats
            with open(self.dashboard_file, 'w') as f:
                json.dump(self.dashboard_stats, f, indent=2)
            
            # Convert to DataFrame and save as CSV for easier analysis
            if self.signals:
                df = pd.DataFrame(self.signals)
                df.to_csv(self.signals_df_file, index=False)
            
            logger.info(f"Saved {len(self.signals)} signal records")
                
        except Exception as e:
            logger.error(f"Error saving dashboard data: {str(e)}")
    
    def add_signal(self, signal):
        """Add a new signal to the dashboard
        
        Args:
            signal (dict): Signal data with symbol, timeframe, probability, etc.
        """
        # Ensure signal has required fields
        required_fields = ['symbol', 'timeframe', 'probability', 'entry_price']
        for field in required_fields:
            if field not in signal:
                logger.warning(f"Signal missing required field: {field}")
                return
        
        # Add timestamp if not present
        if 'timestamp' not in signal:
            signal['timestamp'] = datetime.now().isoformat()
        
        # Add to signals list
        self.signals.append(signal)
        
        # Update dashboard stats
        self._update_stats()
        
        # Save data
        self._save_data()
        
        logger.info(f"Added new signal for {signal['symbol']} with {signal['probability']*100:.1f}% probability")
    
    def update_signal_result(self, signal_id, result):
        """Update a signal with its result (win/loss)
        
        Args:
            signal_id (str): ID of the signal to update
            result (bool): True for win, False for loss
        """
        # Find the signal
        for signal in self.signals:
            if signal.get('id') == signal_id:
                signal['result'] = result
                signal['result_timestamp'] = datetime.now().isoformat()
                
                # Update dashboard stats
                self._update_stats()
                
                # Save data
                self._save_data()
                
                logger.info(f"Updated signal {signal_id} with result: {'win' if result else 'loss'}")
                return True
        
        logger.warning(f"Signal {signal_id} not found")
        return False
    
    def _update_stats(self):
        """Update dashboard statistics"""
        try:
            # Skip if no signals
            if not self.signals:
                return
            
            # Convert signals to DataFrame for easier analysis
            df = pd.DataFrame(self.signals)
            
            # Convert timestamps to datetime
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Calculate confidence bins
            confidence_bins = {
                '90-92%': 0,
                '92-95%': 0,
                '95-98%': 0,
                '98-100%': 0
            }
            
            for prob in df['probability']:
                prob_pct = prob * 100
                if 90 <= prob_pct < 92:
                    confidence_bins['90-92%'] += 1
                elif 92 <= prob_pct < 95:
                    confidence_bins['92-95%'] += 1
                elif 95 <= prob_pct < 98:
                    confidence_bins['95-98%'] += 1
                elif 98 <= prob_pct <= 100:
                    confidence_bins['98-100%'] += 1
            
            # Calculate signals today
            today = datetime.now().date()
            signals_today = df[df['timestamp'].dt.date == today].shape[0] if 'timestamp' in df.columns else 0
            
            # Calculate win rates by timeframe and symbol
            win_rate_by_timeframe = {}
            win_rate_by_symbol = {}
            
            # Only calculate if we have result data
            if 'result' in df.columns and not df['result'].isna().all():
                # Win rate by timeframe
                timeframe_groups = df.groupby('timeframe')
                for tf, group in timeframe_groups:
                    results = group['result'].dropna()
                    if len(results) > 0:
                        win_rate = results.mean()
                        win_rate_by_timeframe[tf] = win_rate
                
                # Win rate by symbol
                symbol_groups = df.groupby('symbol')
                for sym, group in symbol_groups:
                    results = group['result'].dropna()
                    if len(results) > 0:
                        win_rate = results.mean()
                        win_rate_by_symbol[sym] = win_rate
                
                # Best performing pairs and timeframes
                best_pairs = sorted(win_rate_by_symbol.items(), key=lambda x: x[1], reverse=True)[:5]
                best_timeframes = sorted(win_rate_by_timeframe.items(), key=lambda x: x[1], reverse=True)[:3]
                
                best_performing_pairs = [{"symbol": sym, "win_rate": rate} for sym, rate in best_pairs]
                best_performing_timeframes = [{"timeframe": tf, "win_rate": rate} for tf, rate in best_timeframes]
            else:
                best_performing_pairs = []
                best_performing_timeframes = []
            
            # Update dashboard stats
            self.dashboard_stats = {
                'last_update': datetime.now().isoformat(),
                'confidence_bins': confidence_bins,
                'win_rate_by_timeframe': win_rate_by_timeframe,
                'win_rate_by_symbol': win_rate_by_symbol,
                'signals_today': signals_today,
                'signals_total': len(self.signals),
                'avg_probability': df['probability'].mean(),
                'best_performing_pairs': best_performing_pairs,
                'best_performing_timeframes': best_performing_timeframes
            }
            
        except Exception as e:
            logger.error(f"Error updating dashboard stats: {str(e)}")
    
    def get_dashboard_stats(self):
        """Get current dashboard statistics
        
        Returns:
            dict: Dashboard statistics
        """
        return self.dashboard_stats
    
    def generate_dashboard_html(self, output_file='dashboard.html'):
        """Generate an HTML dashboard for signal metrics
        
        Args:
            output_file (str): Path to output HTML file
        """
        try:
            # Skip if no signals
            if not self.signals:
                logger.warning("No signals available to generate dashboard")
                return False
            
            # Convert signals to DataFrame
            df = pd.DataFrame(self.signals)
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Create dashboard directory
            dashboard_dir = os.path.join(self.data_dir, 'dashboard')
            os.makedirs(dashboard_dir, exist_ok=True)
            
            # Generate plots
            self._generate_confidence_distribution_plot(df, dashboard_dir)
            self._generate_win_rate_plots(df, dashboard_dir)
            self._generate_signal_timeline_plot(df, dashboard_dir)
            
            # Generate HTML
            html_content = self._generate_html_content()
            
            # Save HTML
            output_path = os.path.join(dashboard_dir, output_file)
            with open(output_path, 'w') as f:
                f.write(html_content)
            
            logger.info(f"Generated dashboard HTML at {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating dashboard HTML: {str(e)}")
            return False
    
    def _generate_confidence_distribution_plot(self, df, output_dir):
        """Generate confidence distribution plot
        
        Args:
            df (DataFrame): Signal data
            output_dir (str): Output directory for plot
        """
        try:
            plt.figure(figsize=(10, 6))
            
            # Create confidence distribution
            sns.histplot(df['probability'] * 100, bins=10, kde=True)
            
            plt.title('Signal Confidence Distribution')
            plt.xlabel('Confidence (%)')
            plt.ylabel('Number of Signals')
            plt.grid(True, alpha=0.3)
            
            # Save plot
            output_file = os.path.join(output_dir, 'confidence_distribution.png')
            plt.savefig(output_file)
            plt.close()
            
        except Exception as e:
            logger.error(f"Error generating confidence distribution plot: {str(e)}")
    
    def _generate_win_rate_plots(self, df, output_dir):
        """Generate win rate plots by timeframe and symbol
        
        Args:
            df (DataFrame): Signal data
            output_dir (str): Output directory for plots
        """
        try:
            # Skip if no result data
            if 'result' not in df.columns or df['result'].isna().all():
                return
            
            # Win rate by timeframe
            plt.figure(figsize=(10, 6))
            timeframe_win_rates = df.groupby('timeframe')['result'].mean().sort_values(ascending=False)
            
            sns.barplot(x=timeframe_win_rates.index, y=timeframe_win_rates.values)
            plt.title('Win Rate by Timeframe')
            plt.xlabel('Timeframe')
            plt.ylabel('Win Rate')
            plt.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            
            # Save plot
            output_file = os.path.join(output_dir, 'win_rate_by_timeframe.png')
            plt.savefig(output_file)
            plt.close()
            
            # Win rate by symbol
            plt.figure(figsize=(12, 6))
            symbol_win_rates = df.groupby('symbol')['result'].mean().sort_values(ascending=False)
            
            sns.barplot(x=symbol_win_rates.index, y=symbol_win_rates.values)
            plt.title('Win Rate by Symbol')
            plt.xlabel('Symbol')
            plt.ylabel('Win Rate')
            plt.grid(True, alpha=0.3)
            plt.xticks(rotation=90)
            
            # Save plot
            output_file = os.path.join(output_dir, 'win_rate_by_symbol.png')
            plt.savefig(output_file)
            plt.close()
            
            # Win rate by confidence level
            plt.figure(figsize=(10, 6))
            
            # Create confidence bins
            df['confidence_bin'] = pd.cut(
                df['probability'] * 100,
                bins=[90, 92, 95, 98, 100],
                labels=['90-92%', '92-95%', '95-98%', '98-100%']
            )
            
            confidence_win_rates = df.groupby('confidence_bin')['result'].mean()
            
            sns.barplot(x=confidence_win_rates.index, y=confidence_win_rates.values)
            plt.title('Win Rate by Confidence Level')
            plt.xlabel('Confidence Level')
            plt.ylabel('Win Rate')
            plt.grid(True, alpha=0.3)
            
            # Save plot
            output_file = os.path.join(output_dir, 'win_rate_by_confidence.png')
            plt.savefig(output_file)
            plt.close()
            
        except Exception as e:
            logger.error(f"Error generating win rate plots: {str(e)}")
    
    def _generate_signal_timeline_plot(self, df, output_dir):
        """Generate signal timeline plot
        
        Args:
            df (DataFrame): Signal data
            output_dir (str): Output directory for plot
        """
        try:
            # Skip if no timestamp data
            if 'timestamp' not in df.columns:
                return
            
            plt.figure(figsize=(12, 6))
            
            # Create timeline of signal probabilities
            plt.scatter(df['timestamp'], df['probability'] * 100, alpha=0.7)
            plt.plot(df['timestamp'], df['probability'].rolling(10).mean() * 100, 'r-', label='10-signal moving average')
            
            plt.title('Signal Confidence Timeline')
            plt.xlabel('Time')
            plt.ylabel('Confidence (%)')
            plt.grid(True, alpha=0.3)
            plt.legend()
            
            # Format x-axis date
            plt.gcf().autofmt_xdate()
            
            # Save plot
            output_file = os.path.join(output_dir, 'signal_timeline.png')
            plt.savefig(output_file)
            plt.close()
            
        except Exception as e:
            logger.error(f"Error generating signal timeline plot: {str(e)}")
    
    def _generate_html_content(self):
        """Generate HTML content for the dashboard
        
        Returns:
            str: HTML content
        """
        # Get dashboard stats
        stats = self.dashboard_stats
        
        # Format stats for display
        last_update = datetime.fromisoformat(stats['last_update']).strftime('%Y-%m-%d %H:%M:%S')
        avg_probability = f"{stats['avg_probability']*100:.1f}%"
        
        # Generate HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bidget Signal Dashboard</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f8fa;
        }}
        h1, h2, h3 {{
            color: #2c3e50;
        }}
        .dashboard-header {{
            background-color: #2c3e50;
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .stats-container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background-color: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #3498db;
            margin: 10px 0;
        }}
        .stat-label {{
            font-size: 14px;
            color: #7f8c8d;
            text-transform: uppercase;
        }}
        .chart-container {{
            background-color: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
        }}
        .chart-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
        }}
        .chart {{
            width: 100%;
            max-width: 100%;
            height: auto;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        .footer {{
            margin-top: 30px;
            text-align: center;
            font-size: 14px;
            color: #7f8c8d;
        }}
        .auto-refresh {{
            font-size: 12px;
            color: #95a5a6;
        }}
    </style>
</head>
<body>
    <div class="dashboard-header">
        <div>
            <h1>Bidget Signal Dashboard</h1>
            <p>Last updated: {last_update}</p>
        </div>
        <div>
            <button onclick="location.reload()">Refresh Dashboard</button>
            <div class="auto-refresh">Auto-refreshes every 5 minutes</div>
        </div>
    </div>
    
    <div class="stats-container">
        <div class="stat-card">
            <div class="stat-label">Signals Today</div>
            <div class="stat-value">{stats['signals_today']}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Total Signals</div>
            <div class="stat-value">{stats['signals_total']}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Average Confidence</div>
            <div class="stat-value">{avg_probability}</div>
        </div>
    </div>
    
    <h2>Confidence Distribution</h2>
    <div class="stats-container">
        <div class="stat-card">
            <div class="stat-label">90-92% Confidence</div>
            <div class="stat-value">{stats['confidence_bins']['90-92%']}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">92-95% Confidence</div>
            <div class="stat-value">{stats['confidence_bins']['92-95%']}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">95-98% Confidence</div>
            <div class="stat-value">{stats['confidence_bins']['95-98%']}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">98-100% Confidence</div>
            <div class="stat-value">{stats['confidence_bins']['98-100%']}</div>
        </div>
    </div>
    
    <div class="chart-grid">
        <div class="chart-container">
            <h2>Confidence Distribution</h2>
            <img class="chart" src="confidence_distribution.png" alt="Confidence Distribution">
        </div>
        <div class="chart-container">
            <h2>Signal Timeline</h2>
            <img class="chart" src="signal_timeline.png" alt="Signal Timeline">
        </div>
    </div>
    
    <div class="chart-grid">
        <div class="chart-container">
            <h2>Win Rate by Timeframe</h2>
            <img class="chart" src="win_rate_by_timeframe.png" alt="Win Rate by Timeframe">
        </div>
        <div class="chart-container">
            <h2>Win Rate by Symbol</h2>
            <img class="chart" src="win_rate_by_symbol.png" alt="Win Rate by Symbol">
        </div>
    </div>
    
    <div class="chart-container">
        <h2>Win Rate by Confidence Level</h2>
        <img class="chart" src="win_rate_by_confidence.png" alt="Win Rate by Confidence Level">
    </div>
    
    <div class="chart-container">
        <h2>Best Performing Pairs</h2>
        <table>
            <tr>
                <th>Symbol</th>
                <th>Win Rate</th>
            </tr>
"""
        
        # Add best performing pairs
        for pair in stats['best_performing_pairs']:
            html += f"""            <tr>
                <td>{pair['symbol']}</td>
                <td>{pair['win_rate']*100:.1f}%</td>
            </tr>
"""
        
        html += """        </table>
    </div>
    
    <div class="chart-container">
        <h2>Best Performing Timeframes</h2>
        <table>
            <tr>
                <th>Timeframe</th>
                <th>Win Rate</th>
            </tr>
"""
        
        # Add best performing timeframes
        for tf in stats['best_performing_timeframes']:
            html += f"""            <tr>
                <td>{tf['timeframe']}</td>
                <td>{tf['win_rate']*100:.1f}%</td>
            </tr>
"""
        
        html += """        </table>
    </div>
    
    <div class="footer">
        <p>Bidget Trading Bot &copy; 2025 | Refresh interval: 5 minutes</p>
    </div>
    
    <script>
        // Auto-refresh every 5 minutes
        setTimeout(function() {
            location.reload();
        }, 300000);
    </script>
</body>
</html>"""
        
        return html

def create_sample_data():
    """Create sample data for testing"""
    dashboard = SignalDashboard()
    
    # Create sample symbols
    symbols = ['XRP/USDT', 'ADA/USDT', 'DOGE/USDT', 'TRX/USDT', 'XLM/USDT']
    timeframes = ['15m', '30m', '1h', '2h', '3h']
    
    # Create sample signals
    for i in range(100):
        # Random timestamp in the last week
        days_ago = np.random.randint(0, 7)
        hours_ago = np.random.randint(0, 24)
        timestamp = datetime.now() - timedelta(days=days_ago, hours=hours_ago)
        
        # Random symbol and timeframe
        symbol = np.random.choice(symbols)
        timeframe = np.random.choice(timeframes)
        
        # Random probability (90-100%)
        probability = np.random.uniform(0.9, 1.0)
        
        # Create signal
        signal = {
            'id': f"sig-{i}",
            'symbol': symbol,
            'timeframe': timeframe,
            'probability': probability,
            'entry_price': np.random.uniform(0.1, 0.9),
            'timestamp': timestamp.isoformat()
        }
        
        # Add to dashboard
        dashboard.add_signal(signal)
        
        # Add random result for some signals
        if i < 80:  # Only add results for some signals
            result = np.random.random() < (probability - 0.1)  # More likely to be true with higher probability
            dashboard.update_signal_result(f"sig-{i}", result)
    
    # Generate dashboard HTML
    dashboard.generate_dashboard_html()
    
    print("Created sample data and generated dashboard")

if __name__ == "__main__":
    # Check if we should create sample data
    if len(sys.argv) > 1 and sys.argv[1] == "--sample":
        create_sample_data()
    else:
        # Just create the dashboard object
        dashboard = SignalDashboard()
        dashboard.generate_dashboard_html()
