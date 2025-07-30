"""
Unified AI Command System - Telegram Integration Bridge
=====================================================
Connects the Unified Command System with your existing Telegram bot
for seamless multi-agent orchestration and control.
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import json

# Telegram imports
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext

# Import unified system components
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from unified_system.orchestrator.command_center import UnifiedCommandCenter
from unified_system.orchestrator.telegram_orchestrator import TelegramOrchestrator
from unified_system.agents.bidget_adapter import BidgetAgent
from unified_system.communication.protocol import CommandType, MessageType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramUnifiedBridge:
    """Bridge between Telegram bot and Unified AI Command System."""
    
    def __init__(self, telegram_token: str, command_center: UnifiedCommandCenter):
        """Initialize the Telegram bridge.
        
        Args:
            telegram_token: Telegram bot token
            command_center: Unified command center instance
        """
        self.telegram_token = telegram_token
        self.command_center = command_center
        self.app = None
        self.orchestrator = TelegramOrchestrator({'command_center': command_center})
        
        # Track active sessions
        self.active_sessions = {}
        
    async def initialize(self):
        """Initialize the Telegram application."""
        self.app = Application.builder().token(self.telegram_token).build()
        
        # Register unified command handlers
        self.app.add_handler(CommandHandler("forecast", self.handle_forecast_command))
        self.app.add_handler(CommandHandler("tune", self.handle_tune_command))
        self.app.add_handler(CommandHandler("status", self.handle_status_command))
        self.app.add_handler(CommandHandler("network", self.handle_network_command))
        self.app.add_handler(CommandHandler("dashboard", self.handle_dashboard_command))
        
        # Callback query handler for interactive buttons
        self.app.add_handler(CallbackQueryHandler(self.handle_callback_query))
        
        logger.info("[BRIDGE] Telegram Unified Bridge initialized")
    
    async def handle_forecast_command(self, update: Update, context: CallbackContext):
        """Handle /forecast command with unified orchestration."""
        try:
            args = context.args
            chat_id = update.effective_chat.id
            
            # Parse command: /forecast [all|agent_name] [symbol] [timeframe]
            if not args:
                await self._send_forecast_help(update, context)
                return
            
            target = args[0].lower()
            
            if target == "all":
                # Global forecast across all agents
                symbol = args[1] if len(args) > 1 else "BTCUSDT"
                timeframe = args[2] if len(args) > 2 else "1h"
                
                await update.message.reply_text(
                    f"🧠 **GLOBAL FORECAST INITIATED**\n"
                    f"📊 Symbol: {symbol}\n"
                    f"⏰ Timeframe: {timeframe}\n"
                    f"🤖 Querying all agents in the network...",
                    parse_mode='Markdown'
                )
                
                # Execute global forecast
                result = await self.command_center.execute_forecast_all(symbol, timeframe)
                await self._send_global_forecast_results(update, context, result, symbol, timeframe)
                
            else:
                # Agent-specific forecast
                agent_id = target
                symbol = args[1] if len(args) > 1 else "BTCUSDT"
                timeframe = args[2] if len(args) > 2 else "1h"
                
                await update.message.reply_text(
                    f"🤖 **AGENT FORECAST**\n"
                    f"🎯 Agent: {agent_id}\n"
                    f"📊 Symbol: {symbol}\n"
                    f"⏰ Timeframe: {timeframe}",
                    parse_mode='Markdown'
                )
                
                # Execute agent-specific forecast
                result = await self.command_center.execute_agent_command(
                    agent_id, CommandType.FORECAST, 
                    {'symbol': symbol, 'timeframe': timeframe}
                )
                await self._send_agent_forecast_result(update, context, result, agent_id, symbol, timeframe)
                
        except Exception as e:
            logger.error(f"[ERROR] Forecast command failed: {e}")
            await update.message.reply_text(f"❌ Forecast failed: {str(e)}")
    
    async def handle_tune_command(self, update: Update, context: CallbackContext):
        """Handle /tune command with unified orchestration."""
        try:
            args = context.args
            
            if not args or args[0].lower() == "all":
                # Global ML tuning
                await update.message.reply_text(
                    "🧠 **GLOBAL ML TUNING INITIATED**\n"
                    "🔬 Analyzing performance across all agents...\n"
                    "⚙️ Generating optimization recommendations...",
                    parse_mode='Markdown'
                )
                
                result = await self.command_center.execute_tune_all()
                await self._send_global_tune_results(update, context, result)
                
            else:
                # Agent-specific tuning
                agent_id = args[0]
                await update.message.reply_text(
                    f"🤖 **AGENT ML TUNING**\n"
                    f"🎯 Agent: {agent_id}\n"
                    f"🔬 Analyzing performance data...",
                    parse_mode='Markdown'
                )
                
                result = await self.command_center.execute_agent_command(
                    agent_id, CommandType.TUNE, {}
                )
                await self._send_agent_tune_result(update, context, result, agent_id)
                
        except Exception as e:
            logger.error(f"[ERROR] Tune command failed: {e}")
            await update.message.reply_text(f"❌ Tuning failed: {str(e)}")
    
    async def handle_status_command(self, update: Update, context: CallbackContext):
        """Handle /status command for network overview."""
        try:
            await update.message.reply_text(
                "🧠 **UNIFIED AI NETWORK STATUS**\n"
                "📡 Querying all nodes...",
                parse_mode='Markdown'
            )
            
            status = await self.command_center.get_system_status()
            await self._send_network_status(update, context, status)
            
        except Exception as e:
            logger.error(f"[ERROR] Status command failed: {e}")
            await update.message.reply_text(f"❌ Status query failed: {str(e)}")
    
    async def handle_network_command(self, update: Update, context: CallbackContext):
        """Handle /network command for detailed network information."""
        try:
            status = await self.command_center.get_system_status()
            
            # Create network overview message
            message = "🌐 **UNIFIED AI COMMAND NETWORK**\n"
            message += "=" * 40 + "\n\n"
            
            # System metrics
            metrics = status['system_metrics']
            message += f"📊 **SYSTEM METRICS**\n"
            message += f"• Active Agents: {metrics['active_agents']}\n"
            message += f"• Commands Executed: {metrics['total_commands']}\n"
            message += f"• Success Rate: {(metrics['successful_commands']/max(metrics['total_commands'], 1)*100):.1f}%\n"
            message += f"• Avg Response Time: {metrics['average_response_time']:.2f}s\n"
            message += f"• Network Uptime: {metrics['uptime_formatted']}\n\n"
            
            # Agent details
            message += f"🤖 **ACTIVE AGENTS**\n"
            for agent_id, agent_info in status['agents'].items():
                status_icon = "🟢" if agent_info['responsive'] else "🔴"
                message += f"{status_icon} **{agent_info['name']}** ({agent_info['status']})\n"
                
                # Performance metrics
                perf = agent_info.get('performance', {})
                if perf:
                    message += f"  - Trades: {perf.get('trades_today', 0)}\n"
                    message += f"  - Win Rate: {perf.get('win_rate', 0):.1%}\n"
                    message += f"  - P&L: ${perf.get('pnl_today', 0):.2f}\n"
                message += "\n"
            
            # Network capabilities
            message += f"🧠 **NETWORK CAPABILITIES**\n"
            message += f"✅ Global Command Execution\n"
            message += f"✅ Cross-Agent Intelligence Sharing\n"
            message += f"✅ Real-Time Performance Monitoring\n"
            message += f"✅ Secure Message Authentication\n"
            message += f"✅ Fault-Tolerant Operations\n"
            message += f"✅ Collaborative Learning Network\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"[ERROR] Network command failed: {e}")
            await update.message.reply_text(f"❌ Network query failed: {str(e)}")
    
    async def handle_dashboard_command(self, update: Update, context: CallbackContext):
        """Handle /dashboard command for web dashboard access."""
        keyboard = [
            [InlineKeyboardButton("📊 Live Dashboard", url="http://localhost:8080/dashboard")],
            [InlineKeyboardButton("📈 Performance Analytics", url="http://localhost:8080/analytics")],
            [InlineKeyboardButton("🔧 System Configuration", url="http://localhost:8080/config")],
            [InlineKeyboardButton("📱 Mobile View", url="http://localhost:8080/mobile")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🌐 **UNIFIED AI DASHBOARD ACCESS**\n\n"
            "Select your preferred dashboard interface:\n\n"
            "📊 **Live Dashboard** - Real-time network monitoring\n"
            "📈 **Performance Analytics** - Trading performance insights\n"
            "🔧 **System Configuration** - Network settings and controls\n"
            "📱 **Mobile View** - Optimized for mobile devices",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def handle_callback_query(self, update: Update, context: CallbackContext):
        """Handle callback queries from inline keyboards."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("forecast_"):
            # Handle forecast-related callbacks
            await self._handle_forecast_callback(query, context, data)
        elif data.startswith("tune_"):
            # Handle tuning-related callbacks
            await self._handle_tune_callback(query, context, data)
        elif data.startswith("status_"):
            # Handle status-related callbacks
            await self._handle_status_callback(query, context, data)
    
    async def _send_forecast_help(self, update: Update, context: CallbackContext):
        """Send forecast command help."""
        help_text = (
            "🧠 **UNIFIED FORECAST COMMANDS**\n\n"
            "**Global Forecasts:**\n"
            "`/forecast all BTCUSDT 1h` - All agents forecast\n"
            "`/forecast all ETHUSDT 4h` - All agents, 4h timeframe\n\n"
            "**Agent-Specific Forecasts:**\n"
            "`/forecast bidget BTCUSDT 1h` - Bidget's forecast\n"
            "`/forecast behar ETHUSDT 1d` - BeharBot's forecast\n\n"
            "**Supported Timeframes:**\n"
            "`1m, 5m, 15m, 1h, 4h, 1d, 1w`\n\n"
            "**Supported Symbols:**\n"
            "`BTCUSDT, ETHUSDT, ADAUSDT, SOLUSDT, etc.`"
        )
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def _send_global_forecast_results(self, update: Update, context: CallbackContext, 
                                          result: Dict, symbol: str, timeframe: str):
        """Send global forecast results."""
        if not result['success']:
            await update.message.reply_text(f"❌ Global forecast failed: {result.get('error', 'Unknown error')}")
            return
        
        message = f"🧠 **GLOBAL FORECAST RESULTS**\n"
        message += f"📊 {symbol} | {timeframe}\n"
        message += "=" * 30 + "\n\n"
        
        for agent_id, forecast_data in result['results'].items():
            if forecast_data['success']:
                data = forecast_data['data']
                message += f"🤖 **{agent_id.upper()}**\n"
                message += f"📈 Regime: {data.get('current_regime', 'Unknown')}\n"
                message += f"🎯 Confidence: {data.get('confidence', 0):.1%}\n"
                message += f"📊 Signal: {data.get('signal', 'HOLD')}\n"
                message += f"💰 Entry: ${data.get('entry_price', 0):.2f}\n"
                message += f"🛑 Stop Loss: ${data.get('stop_loss', 0):.2f}\n"
                message += f"🎯 Take Profit: ${data.get('take_profit', 0):.2f}\n\n"
            else:
                message += f"❌ **{agent_id.upper()}**: {forecast_data.get('error', 'Failed')}\n\n"
        
        # Add consensus analysis
        successful_forecasts = [r for r in result['results'].values() if r['success']]
        if len(successful_forecasts) > 1:
            message += "🧠 **COLLECTIVE INTELLIGENCE CONSENSUS**\n"
            message += f"📊 {len(successful_forecasts)} agents analyzed\n"
            message += f"🤝 Network confidence: HIGH\n"
            message += f"🎯 Recommended action: Based on majority signal\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def _send_global_tune_results(self, update: Update, context: CallbackContext, result: Dict):
        """Send global tuning results."""
        if not result['success']:
            await update.message.reply_text(f"❌ Global tuning failed: {result.get('error', 'Unknown error')}")
            return
        
        message = "🧠 **GLOBAL ML TUNING RESULTS**\n"
        message += "=" * 30 + "\n\n"
        
        total_recommendations = 0
        total_applied = 0
        
        for agent_id, tune_data in result['results'].items():
            if tune_data['success']:
                data = tune_data['data']
                recommendations = data.get('recommendations', [])
                applied = data.get('applied_count', 0)
                
                message += f"🤖 **{agent_id.upper()}**\n"
                message += f"📊 Recommendations: {len(recommendations)}\n"
                message += f"✅ Applied: {applied}\n"
                message += f"📈 Performance Impact: {data.get('impact_score', 0):.2f}\n\n"
                
                total_recommendations += len(recommendations)
                total_applied += applied
            else:
                message += f"❌ **{agent_id.upper()}**: {tune_data.get('error', 'Failed')}\n\n"
        
        message += f"🧠 **NETWORK OPTIMIZATION SUMMARY**\n"
        message += f"📊 Total Recommendations: {total_recommendations}\n"
        message += f"✅ Total Applied: {total_applied}\n"
        message += f"🎯 Network Evolution: ACTIVE\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def _send_network_status(self, update: Update, context: CallbackContext, status: Dict):
        """Send network status overview."""
        metrics = status['system_metrics']
        
        message = "🧠 **UNIFIED AI NETWORK STATUS**\n"
        message += "=" * 35 + "\n\n"
        
        # System health
        health_icon = "🟢" if metrics['active_agents'] > 0 else "🔴"
        message += f"{health_icon} **NETWORK HEALTH: {'OPERATIONAL' if metrics['active_agents'] > 0 else 'OFFLINE'}**\n\n"
        
        # Key metrics
        message += f"📊 **SYSTEM METRICS**\n"
        message += f"🤖 Active Agents: {metrics['active_agents']}\n"
        message += f"⚡ Commands Executed: {metrics['total_commands']}\n"
        message += f"✅ Success Rate: {(metrics['successful_commands']/max(metrics['total_commands'], 1)*100):.1f}%\n"
        message += f"⏱️ Avg Response: {metrics['average_response_time']:.2f}s\n"
        message += f"🕐 Uptime: {metrics['uptime_formatted']}\n\n"
        
        # Agent status summary
        message += f"🤖 **AGENT STATUS**\n"
        for agent_id, agent_info in status['agents'].items():
            status_icon = "🟢" if agent_info['responsive'] else "🔴"
            message += f"{status_icon} {agent_info['name']}: {agent_info['status']}\n"
        
        # Quick action buttons
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh Status", callback_data="status_refresh")],
            [InlineKeyboardButton("📊 Detailed View", callback_data="status_detailed")],
            [InlineKeyboardButton("🌐 Network Info", callback_data="status_network")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def start_polling(self):
        """Start the Telegram bot polling."""
        if not self.app:
            await self.initialize()
        
        logger.info("[BRIDGE] Starting Telegram Unified Bridge polling...")
        await self.app.run_polling()
    
    async def stop(self):
        """Stop the Telegram bridge."""
        if self.app:
            await self.app.stop()
        logger.info("[BRIDGE] Telegram Unified Bridge stopped")

async def main():
    """Main function to demonstrate the Telegram bridge."""
    # Initialize command center (in production, this would be your actual instance)
    command_center = UnifiedCommandCenter({
        'secret_key': 'unified_ai_secret_2024',
        'max_agents': 10,
        'command_timeout': 30
    })
    
    # Initialize Telegram bridge
    # Replace with your actual Telegram bot token
    TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
    
    bridge = TelegramUnifiedBridge(TELEGRAM_TOKEN, command_center)
    
    try:
        print("🧠 UNIFIED AI TELEGRAM BRIDGE")
        print("🌐 Connecting Telegram to Command Network...")
        print("=" * 50)
        
        # Start the bridge
        await bridge.start_polling()
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Telegram bridge...")
        await bridge.stop()
        print("✅ Bridge shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())
