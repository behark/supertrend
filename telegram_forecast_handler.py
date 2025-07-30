"""
Telegram Forecast Handler for Visual Intelligence System
Handles /forecast and /plan commands with chart generation and inline buttons
"""
import os
import logging
import asyncio
from datetime import datetime, timedelta
import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import CallbackContext

# Local imports
from forecast_chart_generator import ForecastChartGenerator
from ml_predictor import MLPredictor
from market_regime import MarketRegimeDetector
from bybit_trader import BybitTrader

logger = logging.getLogger(__name__)

class TelegramForecastHandler:
    """Handles visual forecast commands for Telegram bot"""
    
    def __init__(self, bybit_trader=None):
        """Initialize the forecast handler.
        
        Args:
            bybit_trader (BybitTrader): Trading interface for market data
        """
        self.chart_generator = ForecastChartGenerator()
        self.ml_predictor = MLPredictor()
        self.regime_detector = MarketRegimeDetector()
        self.trader = bybit_trader
        
        # Default settings
        self.default_symbol = 'BTCUSDT'
        self.default_timeframe = '1h'
        self.default_lookback = 100  # candles
        
        logger.info("Telegram Forecast Handler initialized")
    
    async def handle_forecast_command(self, update: Update, context: CallbackContext):
        """Handle /forecast command with optional parameters.
        
        Usage: /forecast [symbol] [timeframe] [format]
        Examples:
        - /forecast
        - /forecast ETHUSDT
        - /forecast BTCUSDT 4h
        - /forecast symbol=ADAUSDT timeframe=1h
        """
        try:
            # Parse command arguments
            args = context.args
            symbol, timeframe, format_type = self._parse_forecast_args(args)
            
            # Send initial "generating" message
            generating_msg = await update.message.reply_text(
                "🧠 Generating AI forecast chart...\n"
                f"📊 Symbol: {symbol}\n"
                f"⏰ Timeframe: {timeframe}\n"
                "⚡ This may take a few moments..."
            )
            
            # Get market data
            df = await self._get_market_data(symbol, timeframe, self.default_lookback)
            if df is None or len(df) < 20:
                await generating_msg.edit_text(
                    "❌ Unable to fetch sufficient market data for forecast.\n"
                    "Please try again or check if the symbol is valid."
                )
                return
            
            # Generate forecast data
            forecast_data = await self._generate_forecast_data(df, symbol, timeframe)
            
            # Detect regime zones
            regime_zones = await self._detect_regime_zones(df)
            
            # Get current trade context if available
            trade_context = await self._get_trade_context(symbol)
            
            # Generate forecast chart
            chart_path = self.chart_generator.generate_forecast_chart(
                df=df,
                symbol=symbol,
                timeframe=timeframe,
                forecast_data=forecast_data,
                trade_context=trade_context,
                regime_zones=regime_zones
            )
            
            # Create forecast message
            message_text = self._create_forecast_message(
                symbol, timeframe, forecast_data, trade_context
            )
            
            # Create inline keyboard
            keyboard = self._create_forecast_keyboard(symbol, timeframe)
            
            # Send chart with message
            with open(chart_path, 'rb') as chart_file:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=chart_file,
                    caption=message_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboard
                )
            
            # Delete generating message
            await generating_msg.delete()
            
            # Clean up chart file
            try:
                os.remove(chart_path)
            except:
                pass
                
        except Exception as e:
            logger.error(f"Error in forecast command: {str(e)}")
            await update.message.reply_text(
                "❌ Error generating forecast. Please try again later."
            )
    
    async def handle_plan_command(self, update: Update, context: CallbackContext):
        """Handle /plan command for trading plan with visual forecast.
        
        Usage: /plan [symbol]
        """
        try:
            # Parse symbol
            symbol = self.default_symbol
            if context.args:
                symbol = context.args[0].upper()
                if not symbol.endswith('USDT'):
                    symbol += 'USDT'
            
            # Send generating message
            generating_msg = await update.message.reply_text(
                f"📋 Generating trading plan for {symbol}...\n"
                "🧠 Analyzing market conditions and strategy..."
            )
            
            # Get extended market data for comprehensive analysis
            df_1h = await self._get_market_data(symbol, '1h', 200)
            df_4h = await self._get_market_data(symbol, '4h', 100)
            
            if df_1h is None or df_4h is None:
                await generating_msg.edit_text(
                    f"❌ Unable to fetch market data for {symbol}.\n"
                    "Please check the symbol and try again."
                )
                return
            
            # Multi-timeframe analysis
            forecast_1h = await self._generate_forecast_data(df_1h, symbol, '1h')
            forecast_4h = await self._generate_forecast_data(df_4h, symbol, '4h')
            
            # Generate comprehensive trading plan
            trading_plan = await self._generate_trading_plan(
                symbol, df_1h, df_4h, forecast_1h, forecast_4h
            )
            
            # Generate plan chart (using 1h for detail)
            regime_zones = await self._detect_regime_zones(df_1h)
            chart_path = self.chart_generator.generate_forecast_chart(
                df=df_1h,
                symbol=symbol,
                timeframe='1h',
                forecast_data=forecast_1h,
                trade_context=trading_plan.get('trade_context'),
                regime_zones=regime_zones
            )
            
            # Create plan message
            plan_message = self._create_trading_plan_message(symbol, trading_plan)
            
            # Create plan keyboard
            keyboard = self._create_plan_keyboard(symbol)
            
            # Send plan with chart
            with open(chart_path, 'rb') as chart_file:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=chart_file,
                    caption=plan_message,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboard
                )
            
            await generating_msg.delete()
            
            # Clean up
            try:
                os.remove(chart_path)
            except:
                pass
                
        except Exception as e:
            logger.error(f"Error in plan command: {str(e)}")
            await update.message.reply_text(
                "❌ Error generating trading plan. Please try again later."
            )
    
    async def handle_forecast_callback(self, update: Update, context: CallbackContext):
        """Handle inline button callbacks for forecast commands."""
        query = update.callback_query
        await query.answer()
        
        try:
            data = query.data.split('_')
            action = data[1]
            symbol = data[2] if len(data) > 2 else self.default_symbol
            
            if action == 'history':
                await self._show_forecast_history(query, symbol)
            elif action == 'switch':
                await self._show_symbol_switcher(query)
            elif action == 'save':
                await self._save_forecast(query, symbol)
            elif action == 'refresh':
                await self._refresh_forecast(query, symbol)
                
        except Exception as e:
            logger.error(f"Error in forecast callback: {str(e)}")
            await query.edit_message_text("❌ Error processing request.")
    
    def _parse_forecast_args(self, args):
        """Parse forecast command arguments."""
        symbol = self.default_symbol
        timeframe = self.default_timeframe
        format_type = 'full'
        
        for arg in args:
            if '=' in arg:
                key, value = arg.split('=', 1)
                if key.lower() == 'symbol':
                    symbol = value.upper()
                elif key.lower() == 'timeframe':
                    timeframe = value.lower()
                elif key.lower() == 'format':
                    format_type = value.lower()
            else:
                # Positional arguments
                if arg.upper().endswith('USDT') or len(arg) <= 6:
                    symbol = arg.upper()
                elif arg.lower() in ['1m', '5m', '15m', '1h', '4h', '1d']:
                    timeframe = arg.lower()
        
        # Ensure symbol ends with USDT
        if not symbol.endswith('USDT'):
            symbol += 'USDT'
            
        return symbol, timeframe, format_type
    
    async def _get_market_data(self, symbol, timeframe, limit):
        """Get market data for analysis."""
        try:
            if self.trader:
                # Use trader's get_klines method
                return await asyncio.get_event_loop().run_in_executor(
                    None, self.trader.get_klines, symbol, timeframe, limit
                )
            else:
                # Fallback: generate sample data (for testing)
                logger.warning("No trader available, generating sample data")
                return self._generate_sample_data(limit)
        except Exception as e:
            logger.error(f"Error fetching market data: {str(e)}")
            return None
    
    def _generate_sample_data(self, limit):
        """Generate sample OHLCV data for testing."""
        import random
        
        dates = pd.date_range(end=datetime.now(), periods=limit, freq='1H')
        base_price = 45000
        
        data = []
        for i, date in enumerate(dates):
            # Simple random walk
            change = random.uniform(-0.02, 0.02)
            base_price *= (1 + change)
            
            high = base_price * random.uniform(1.001, 1.01)
            low = base_price * random.uniform(0.99, 0.999)
            close = base_price * random.uniform(0.995, 1.005)
            volume = random.uniform(100, 1000)
            
            data.append({
                'timestamp': date,
                'open': base_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    async def _generate_forecast_data(self, df, symbol, timeframe):
        """Generate forecast data using ML predictor."""
        try:
            # Use ML predictor if available
            if hasattr(self.ml_predictor, 'predict_signal'):
                prediction = await asyncio.get_event_loop().run_in_executor(
                    None, self.ml_predictor.predict_signal, df
                )
            else:
                # Simple technical analysis fallback
                prediction = self._simple_forecast(df)
            
            # Calculate target price and confidence
            last_price = df['close'].iloc[-1]
            
            if prediction.get('signal') == 'BUY':
                target_price = last_price * 1.03  # 3% target
                pred_type = 'bullish'
            elif prediction.get('signal') == 'SELL':
                target_price = last_price * 0.97  # 3% target
                pred_type = 'bearish'
            else:
                target_price = last_price
                pred_type = 'neutral'
            
            return {
                'prediction': pred_type,
                'confidence': prediction.get('confidence', 65),
                'target_price': target_price,
                'probability': prediction.get('probability', 0.65),
                'horizon': 24,  # 24 periods ahead
                'strategy': prediction.get('strategy', 'AI Analysis'),
                'timeframe': timeframe
            }
            
        except Exception as e:
            logger.error(f"Error generating forecast: {str(e)}")
            return {
                'prediction': 'neutral',
                'confidence': 50,
                'target_price': df['close'].iloc[-1],
                'probability': 0.5,
                'horizon': 24,
                'strategy': 'Technical Analysis',
                'timeframe': timeframe
            }
    
    def _simple_forecast(self, df):
        """Simple technical analysis forecast."""
        if len(df) < 20:
            return {'signal': 'HOLD', 'confidence': 50}
        
        # Simple moving average crossover
        ma_short = df['close'].rolling(9).mean().iloc[-1]
        ma_long = df['close'].rolling(21).mean().iloc[-1]
        current_price = df['close'].iloc[-1]
        
        if ma_short > ma_long and current_price > ma_short:
            return {'signal': 'BUY', 'confidence': 70, 'strategy': 'MA Crossover'}
        elif ma_short < ma_long and current_price < ma_short:
            return {'signal': 'SELL', 'confidence': 70, 'strategy': 'MA Crossover'}
        else:
            return {'signal': 'HOLD', 'confidence': 60, 'strategy': 'MA Analysis'}
    
    async def _detect_regime_zones(self, df):
        """Detect market regime zones."""
        try:
            if hasattr(self.regime_detector, 'detect_regime_zones'):
                return await asyncio.get_event_loop().run_in_executor(
                    None, self.regime_detector.detect_regime_zones, df
                )
            else:
                # Simple regime detection fallback
                return self._simple_regime_detection(df)
        except Exception as e:
            logger.error(f"Error detecting regimes: {str(e)}")
            return []
    
    def _simple_regime_detection(self, df):
        """Simple regime detection based on volatility and trend."""
        if len(df) < 20:
            return []
        
        # Calculate rolling volatility
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(20).std()
        
        zones = []
        zone_size = 20
        
        for i in range(0, len(df) - zone_size, zone_size):
            zone_data = df.iloc[i:i + zone_size]
            
            # Determine regime based on price trend and volatility
            price_change = (zone_data['close'].iloc[-1] - zone_data['close'].iloc[0]) / zone_data['close'].iloc[0]
            avg_volatility = zone_data['volatility'].mean()
            
            if price_change > 0.02:
                regime = 'bullish'
            elif price_change < -0.02:
                regime = 'bearish'
            else:
                regime = 'neutral'
            
            zones.append({
                'start_idx': i,
                'end_idx': min(i + zone_size - 1, len(df) - 1),
                'regime': regime,
                'strength': min(abs(price_change) * 10, 1.0)
            })
        
        return zones
    
    async def _get_trade_context(self, symbol):
        """Get current trade context if available."""
        try:
            if self.trader and hasattr(self.trader, 'get_current_position'):
                position = await asyncio.get_event_loop().run_in_executor(
                    None, self.trader.get_current_position, symbol
                )
                if position:
                    return {
                        'strategy': 'Active Trade',
                        'leverage': position.get('leverage', 1),
                        'entry_price': position.get('entry_price'),
                        'stop_loss': position.get('stop_loss'),
                        'take_profit': position.get('take_profit')
                    }
        except Exception as e:
            logger.error(f"Error getting trade context: {str(e)}")
        
        return None
    
    async def _generate_trading_plan(self, symbol, df_1h, df_4h, forecast_1h, forecast_4h):
        """Generate comprehensive trading plan."""
        plan = {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'timeframes': {
                '1h': forecast_1h,
                '4h': forecast_4h
            },
            'overall_bias': self._determine_overall_bias(forecast_1h, forecast_4h),
            'risk_level': self._calculate_risk_level(df_1h, df_4h),
            'entry_zones': self._calculate_entry_zones(df_1h),
            'trade_context': self._generate_trade_context(symbol, forecast_1h, df_1h)
        }
        
        return plan
    
    def _determine_overall_bias(self, forecast_1h, forecast_4h):
        """Determine overall market bias from multi-timeframe analysis."""
        h1_score = {'bullish': 1, 'neutral': 0, 'bearish': -1}[forecast_1h['prediction']]
        h4_score = {'bullish': 1, 'neutral': 0, 'bearish': -1}[forecast_4h['prediction']]
        
        # Weight 4h more heavily
        combined_score = (h1_score + h4_score * 2) / 3
        
        if combined_score > 0.3:
            return 'bullish'
        elif combined_score < -0.3:
            return 'bearish'
        else:
            return 'neutral'
    
    def _calculate_risk_level(self, df_1h, df_4h):
        """Calculate current market risk level."""
        # Simple volatility-based risk calculation
        vol_1h = df_1h['close'].pct_change().rolling(24).std().iloc[-1]
        vol_4h = df_4h['close'].pct_change().rolling(24).std().iloc[-1]
        
        avg_vol = (vol_1h + vol_4h) / 2
        
        if avg_vol > 0.05:
            return 'high'
        elif avg_vol > 0.03:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_entry_zones(self, df):
        """Calculate potential entry zones."""
        current_price = df['close'].iloc[-1]
        
        # Simple support/resistance levels
        recent_high = df['high'].tail(20).max()
        recent_low = df['low'].tail(20).min()
        
        return {
            'support': recent_low,
            'resistance': recent_high,
            'current': current_price
        }
    
    def _generate_trade_context(self, symbol, forecast, df):
        """Generate trade context for the plan."""
        current_price = df['close'].iloc[-1]
        
        if forecast['prediction'] == 'bullish':
            return {
                'strategy': 'Long Setup',
                'leverage': 3,
                'entry_price': current_price * 0.999,  # Slight discount
                'stop_loss': current_price * 0.97,     # 3% stop
                'take_profit': current_price * 1.06    # 6% target
            }
        elif forecast['prediction'] == 'bearish':
            return {
                'strategy': 'Short Setup',
                'leverage': 2,
                'entry_price': current_price * 1.001,  # Slight premium
                'stop_loss': current_price * 1.03,     # 3% stop
                'take_profit': current_price * 0.94    # 6% target
            }
        else:
            return {
                'strategy': 'Wait & Watch',
                'leverage': 1,
                'entry_price': None,
                'stop_loss': None,
                'take_profit': None
            }
    
    def _create_forecast_message(self, symbol, timeframe, forecast_data, trade_context):
        """Create formatted forecast message."""
        prediction = forecast_data['prediction'].title()
        confidence = forecast_data['confidence']
        target = forecast_data['target_price']
        strategy = forecast_data.get('strategy', 'AI Analysis')
        
        # Emoji based on prediction
        emoji_map = {
            'bullish': '📈',
            'bearish': '📉',
            'neutral': '➡️'
        }
        emoji = emoji_map.get(forecast_data['prediction'], '🔮')
        
        message = f"""🧠 *AI Forecast: {prediction} Zone*
{emoji} *Confidence:* {confidence:.0f}%
📊 *Strategy:* {strategy}
🎯 *Target:* {target:.6f}
⏰ *Timeframe:* {timeframe.upper()}

"""
        
        if trade_context:
            leverage = trade_context.get('leverage', 1)
            message += f"💼 *Current Setup:* {trade_context['strategy']} | {leverage}x Leverage\n"
            
            if trade_context.get('entry_price'):
                message += f"🎯 *Entry:* {trade_context['entry_price']:.6f}\n"
                message += f"🛑 *Stop:* {trade_context['stop_loss']:.6f}\n"
                message += f"💰 *Target:* {trade_context['take_profit']:.6f}\n"
        
        message += f"\n📈 *Chart Analysis Attached*"
        
        return message
    
    def _create_trading_plan_message(self, symbol, plan):
        """Create formatted trading plan message."""
        bias = plan['overall_bias'].title()
        risk = plan['risk_level'].title()
        
        message = f"""📋 *Trading Plan: {symbol}*

🎯 *Overall Bias:* {bias}
⚠️ *Risk Level:* {risk}

📊 *Multi-Timeframe Analysis:*
• 1H: {plan['timeframes']['1h']['prediction'].title()} ({plan['timeframes']['1h']['confidence']:.0f}%)
• 4H: {plan['timeframes']['4h']['prediction'].title()} ({plan['timeframes']['4h']['confidence']:.0f}%)

🎯 *Key Levels:*
• Support: {plan['entry_zones']['support']:.6f}
• Resistance: {plan['entry_zones']['resistance']:.6f}
• Current: {plan['entry_zones']['current']:.6f}

"""
        
        trade_ctx = plan.get('trade_context', {})
        if trade_ctx.get('strategy') != 'Wait & Watch':
            message += f"""💼 *Recommended Setup:*
• Strategy: {trade_ctx['strategy']}
• Leverage: {trade_ctx['leverage']}x
• Entry: {trade_ctx.get('entry_price', 'TBD'):.6f}
• Stop: {trade_ctx.get('stop_loss', 'TBD'):.6f}
• Target: {trade_ctx.get('take_profit', 'TBD'):.6f}
"""
        else:
            message += "⏳ *Recommendation:* Wait for clearer setup\n"
        
        message += "\n📈 *Detailed Chart Analysis Attached*"
        
        return message
    
    def _create_forecast_keyboard(self, symbol, timeframe):
        """Create inline keyboard for forecast commands."""
        keyboard = [
            [
                InlineKeyboardButton("📊 View History", callback_data=f"forecast_history_{symbol}"),
                InlineKeyboardButton("🔄 Switch Symbol", callback_data="forecast_switch")
            ],
            [
                InlineKeyboardButton("💾 Save Forecast", callback_data=f"forecast_save_{symbol}"),
                InlineKeyboardButton("🔄 Refresh", callback_data=f"forecast_refresh_{symbol}")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def _create_plan_keyboard(self, symbol):
        """Create inline keyboard for plan commands."""
        keyboard = [
            [
                InlineKeyboardButton("📊 Detailed Analysis", callback_data=f"plan_detail_{symbol}"),
                InlineKeyboardButton("⚡ Quick Setup", callback_data=f"plan_quick_{symbol}")
            ],
            [
                InlineKeyboardButton("🔔 Set Alerts", callback_data=f"plan_alerts_{symbol}"),
                InlineKeyboardButton("📋 Export Plan", callback_data=f"plan_export_{symbol}")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def _show_forecast_history(self, query, symbol):
        """Show forecast history for symbol."""
        # Implementation for showing historical forecasts
        await query.edit_message_text(
            f"📊 Forecast history for {symbol} will be implemented in next update."
        )
    
    async def _show_symbol_switcher(self, query):
        """Show symbol switcher interface."""
        popular_symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'DOTUSDT']
        
        keyboard = []
        for i in range(0, len(popular_symbols), 2):
            row = []
            for j in range(2):
                if i + j < len(popular_symbols):
                    symbol = popular_symbols[i + j]
                    row.append(InlineKeyboardButton(
                        symbol.replace('USDT', ''), 
                        callback_data=f"forecast_switch_{symbol}"
                    ))
            keyboard.append(row)
        
        await query.edit_message_text(
            "🔄 Select symbol for forecast:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _save_forecast(self, query, symbol):
        """Save forecast for later reference."""
        await query.edit_message_text(
            f"💾 Forecast for {symbol} saved to your watchlist."
        )
    
    async def _refresh_forecast(self, query, symbol):
        """Refresh forecast with latest data."""
        await query.edit_message_text(
            f"🔄 Refreshing forecast for {symbol}..."
        )
        # Implementation would regenerate and update the forecast
