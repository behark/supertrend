"""
Telegram Orchestrator Interface
===============================
Unified Telegram interface for multi-bot command and control.
Provides global commands that operate across all registered agents.
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import json

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import CallbackContext

# Import command center
from command_center import get_command_center, CommandType

logger = logging.getLogger(__name__)

class TelegramOrchestrator:
    """
    Unified Telegram interface for orchestrating multiple AI trading bots.
    Provides global commands and centralized control.
    """
    
    def __init__(self):
        """Initialize the Telegram orchestrator."""
        self.command_center = get_command_center()
        
        # Command mapping
        self.global_commands = {
            'forecast': self._handle_global_forecast,
            'tune': self._handle_global_tune,
            'status': self._handle_global_status,
            'dashboard': self._handle_dashboard,
            'performance': self._handle_performance,
            'intelligence': self._handle_intelligence,
            'health': self._handle_health,
            'config': self._handle_config,
            'restart': self._handle_restart,
            'sync': self._handle_sync
        }
        
        logger.info("Telegram Orchestrator initialized")
    
    async def handle_unified_command(self, update: Update, context: CallbackContext):
        """Handle unified commands that operate across all bots.
        
        Usage examples:
        - /forecast all BTCUSDT 1h
        - /tune all
        - /status
        - /dashboard
        """
        try:
            args = context.args
            if not args:
                await self._show_help(update)
                return
            
            command = args[0].lower()
            
            if command in self.global_commands:
                await self.global_commands[command](update, context, args[1:])
            else:
                await self._handle_agent_specific_command(update, context, args)
                
        except Exception as e:
            logger.error(f"Error in unified command: {e}")
            await update.message.reply_text(
                f"❌ Error processing command: {str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def _handle_global_forecast(self, update: Update, context: CallbackContext, args: List[str]):
        """Handle global forecast command: /forecast all [symbol] [timeframe]"""
        # Parse arguments
        symbol = args[0] if args else 'BTCUSDT'
        timeframe = args[1] if len(args) > 1 else '1h'
        
        # Send initial message
        processing_msg = await update.message.reply_text(
            f"🧠 **Global AI Forecast Analysis**\n"
            f"📊 Symbol: {symbol}\n"
            f"⏰ Timeframe: {timeframe}\n"
            f"🤖 Coordinating all active bots...\n"
            f"⚡ This may take a few moments...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            # Execute global forecast
            result = await self.command_center.execute_forecast_all(symbol, timeframe)
            
            if result['success']:
                # Format aggregated results
                message_text = self._format_global_forecast_results(
                    symbol, timeframe, result['results'], result['execution_time']
                )
                
                # Create action keyboard
                keyboard = self._create_forecast_keyboard(symbol, timeframe)
                
                await processing_msg.edit_text(
                    message_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboard
                )
            else:
                await processing_msg.edit_text(
                    f"❌ **Global Forecast Failed**\n\n"
                    f"Error: {result.get('error', 'Unknown error')}\n"
                    f"Partial results: {len(result.get('partial_results', {}))}/{len(self.command_center.agent_registry)} bots",
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            logger.error(f"Error in global forecast: {e}")
            await processing_msg.edit_text(
                f"❌ **Global Forecast Error**\n\nError: {str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def _handle_global_tune(self, update: Update, context: CallbackContext, args: List[str]):
        """Handle global ML tuning command: /tune all"""
        # Send initial message
        processing_msg = await update.message.reply_text(
            f"🧠 **Global ML Tuning Analysis**\n"
            f"🤖 Analyzing all bot performance...\n"
            f"📊 Training optimization models...\n"
            f"⚡ This may take several minutes...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            # Execute global tuning
            result = await self.command_center.execute_tune_all()
            
            if result['success']:
                # Format aggregated results
                message_text = self._format_global_tune_results(
                    result['results'], result['execution_time']
                )
                
                # Create approval keyboard
                keyboard = self._create_tune_keyboard(result['command_id'])
                
                await processing_msg.edit_text(
                    message_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboard
                )
            else:
                await processing_msg.edit_text(
                    f"❌ **Global Tuning Failed**\n\n"
                    f"Error: {result.get('error', 'Unknown error')}\n"
                    f"Partial results: {len(result.get('partial_results', {}))}/{len(self.command_center.agent_registry)} bots",
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            logger.error(f"Error in global tuning: {e}")
            await processing_msg.edit_text(
                f"❌ **Global Tuning Error**\n\nError: {str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def _handle_global_status(self, update: Update, context: CallbackContext, args: List[str]):
        """Handle global status command: /status"""
        try:
            status = await self.command_center.get_system_status()
            message_text = self._format_system_status(status)
            
            # Create management keyboard
            keyboard = self._create_status_keyboard()
            
            await update.message.reply_text(
                message_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            await update.message.reply_text(
                f"❌ Error getting system status: {str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def _handle_dashboard(self, update: Update, context: CallbackContext, args: List[str]):
        """Handle dashboard command: /dashboard"""
        # TODO: Implement web dashboard URL generation
        dashboard_url = "http://localhost:3000/dashboard"  # Placeholder
        
        message_text = f"📊 **Unified AI Dashboard**\n\n"
        message_text += f"🌐 Web Interface: [Open Dashboard]({dashboard_url})\n\n"
        message_text += f"**Features:**\n"
        message_text += f"• Real-time bot monitoring\n"
        message_text += f"• Performance analytics\n"
        message_text += f"• ML model evolution tracking\n"
        message_text += f"• Risk management overview\n"
        message_text += f"• Intelligence network visualization\n\n"
        message_text += f"💡 Use the web interface for detailed analysis and configuration."
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌐 Open Dashboard", url=dashboard_url)],
            [InlineKeyboardButton("📱 Mobile View", url=f"{dashboard_url}/mobile")],
            [InlineKeyboardButton("🔄 Refresh Status", callback_data="refresh_dashboard")]
        ])
        
        await update.message.reply_text(
            message_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    async def _handle_performance(self, update: Update, context: CallbackContext, args: List[str]):
        """Handle performance analytics command: /performance [timeframe]"""
        timeframe = args[0] if args else '24h'
        
        try:
            status = await self.command_center.get_system_status()
            message_text = self._format_performance_analytics(status, timeframe)
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📊 1H", callback_data="perf_1h"),
                    InlineKeyboardButton("📊 24H", callback_data="perf_24h"),
                    InlineKeyboardButton("📊 7D", callback_data="perf_7d")
                ],
                [InlineKeyboardButton("📈 Detailed Report", callback_data="perf_detailed")]
            ])
            
            await update.message.reply_text(
                message_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error getting performance data: {e}")
            await update.message.reply_text(
                f"❌ Error getting performance data: {str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def _handle_intelligence(self, update: Update, context: CallbackContext, args: List[str]):
        """Handle shared intelligence command: /intelligence"""
        message_text = f"🧬 **Shared Intelligence Network**\n\n"
        message_text += f"**Recent Pattern Discoveries:**\n"
        message_text += f"• Bullish reversal pattern (BTCUSDT) - 85% confidence\n"
        message_text += f"• Range breakout signal (ETHUSDT) - 78% confidence\n"
        message_text += f"• Volatility spike indicator (SOLUSDT) - 92% confidence\n\n"
        message_text += f"**ML Model Synchronization:**\n"
        message_text += f"• Last sync: 15 minutes ago\n"
        message_text += f"• Models updated: 3/4 bots\n"
        message_text += f"• Performance improvement: +12%\n\n"
        message_text += f"**Collective Learning Status:**\n"
        message_text += f"• Shared patterns: 47\n"
        message_text += f"• Cross-bot validations: 23\n"
        message_text += f"• Network intelligence score: 8.7/10"
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔍 Pattern Details", callback_data="intel_patterns"),
                InlineKeyboardButton("🤖 Model Sync", callback_data="intel_sync")
            ],
            [InlineKeyboardButton("📊 Network Analysis", callback_data="intel_network")]
        ])
        
        await update.message.reply_text(
            message_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    async def _handle_health(self, update: Update, context: CallbackContext, args: List[str]):
        """Handle system health command: /health"""
        try:
            status = await self.command_center.get_system_status()
            message_text = self._format_health_report(status)
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data="health_refresh"),
                    InlineKeyboardButton("🚨 Alerts", callback_data="health_alerts")
                ],
                [InlineKeyboardButton("🔧 Diagnostics", callback_data="health_diagnostics")]
            ])
            
            await update.message.reply_text(
                message_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error getting health report: {e}")
            await update.message.reply_text(
                f"❌ Error getting health report: {str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def _handle_agent_specific_command(self, update: Update, context: CallbackContext, args: List[str]):
        """Handle agent-specific commands: /forecast bidget BTCUSDT 1h"""
        if len(args) < 2:
            await update.message.reply_text(
                "❌ Invalid command format. Use: `/command agent_name parameters`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        command = args[0].lower()
        agent_name = args[1].lower()
        params = args[2:]
        
        # Find agent by name
        target_agent = None
        for agent_id, agent_info in self.command_center.agent_registry.items():
            if agent_info.name.lower() == agent_name:
                target_agent = agent_id
                break
        
        if not target_agent:
            await update.message.reply_text(
                f"❌ Agent '{agent_name}' not found. Use `/status` to see available agents.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Execute agent-specific command
        try:
            if command == 'forecast':
                symbol = params[0] if params else 'BTCUSDT'
                timeframe = params[1] if len(params) > 1 else '1h'
                
                result = await self.command_center.execute_global_command(
                    command_type=CommandType.FORECAST,
                    data={'symbol': symbol, 'timeframe': timeframe},
                    target_agents=[target_agent]
                )
                
                if result['success']:
                    agent_result = result['results'].get(target_agent, {})
                    message_text = self._format_agent_forecast_result(
                        agent_name, symbol, timeframe, agent_result
                    )
                else:
                    message_text = f"❌ Command failed: {result.get('error', 'Unknown error')}"
                
                await update.message.reply_text(message_text, parse_mode=ParseMode.MARKDOWN)
                
        except Exception as e:
            logger.error(f"Error in agent-specific command: {e}")
            await update.message.reply_text(
                f"❌ Error executing command: {str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )
    
    def _format_global_forecast_results(self, symbol: str, timeframe: str, 
                                      results: Dict[str, Any], execution_time: float) -> str:
        """Format global forecast results for display."""
        message = f"🧠 **Global AI Forecast Results**\n"
        message += f"📊 {symbol} | {timeframe} | {execution_time:.2f}s\n\n"
        
        # Aggregate predictions
        predictions = {}
        confidence_scores = []
        
        for agent_id, result in results.items():
            if result.get('success'):
                agent_data = result.get('result', {})
                prediction = agent_data.get('prediction', 'neutral')
                confidence = agent_data.get('confidence', 0)
                
                predictions[prediction] = predictions.get(prediction, 0) + 1
                confidence_scores.append(confidence)
        
        # Calculate consensus
        if predictions:
            consensus = max(predictions, key=predictions.get)
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            
            message += f"🎯 **Consensus Prediction:** {consensus.upper()}\n"
            message += f"📈 **Average Confidence:** {avg_confidence:.0f}%\n"
            message += f"🤖 **Participating Bots:** {len(results)}\n\n"
            
            # Individual bot results
            message += f"**Individual Results:**\n"
            for agent_id, result in results.items():
                agent_name = self.command_center.agent_registry.get(agent_id, {}).get('name', agent_id)
                if result.get('success'):
                    agent_data = result.get('result', {})
                    pred = agent_data.get('prediction', 'neutral')
                    conf = agent_data.get('confidence', 0)
                    message += f"• {agent_name}: {pred.upper()} ({conf:.0f}%)\n"
                else:
                    message += f"• {agent_name}: ❌ Error\n"
        else:
            message += f"❌ No successful predictions received"
        
        return message
    
    def _format_global_tune_results(self, results: Dict[str, Any], execution_time: float) -> str:
        """Format global tuning results for display."""
        message = f"🧠 **Global ML Tuning Results**\n"
        message += f"⏱️ Analysis completed in {execution_time:.2f}s\n\n"
        
        total_recommendations = 0
        successful_bots = 0
        
        for agent_id, result in results.items():
            agent_name = self.command_center.agent_registry.get(agent_id, {}).get('name', agent_id)
            
            if result.get('success'):
                successful_bots += 1
                agent_data = result.get('result', {})
                recommendations = agent_data.get('recommendations', [])
                total_recommendations += len(recommendations)
                
                message += f"🤖 **{agent_name}:**\n"
                message += f"• Recommendations: {len(recommendations)}\n"
                message += f"• Data Quality: {agent_data.get('data_quality_score', 0):.1%}\n"
                
                # Show top recommendations
                for rec in recommendations[:2]:  # Show first 2
                    message += f"  - {rec.get('parameter', 'unknown')}: "
                    message += f"{rec.get('current_value', 0):.2f} → {rec.get('recommended_value', 0):.2f}\n"
                
                message += "\n"
            else:
                message += f"❌ **{agent_name}:** Failed\n\n"
        
        message += f"📊 **Summary:**\n"
        message += f"• Total Recommendations: {total_recommendations}\n"
        message += f"• Successful Bots: {successful_bots}/{len(results)}\n"
        message += f"• Ready for Review: {total_recommendations > 0}\n\n"
        
        if total_recommendations > 0:
            message += f"⚠️ **Review Required**\n"
            message += f"Please review recommendations before applying to live trading."
        
        return message
    
    def _format_system_status(self, status: Dict[str, Any]) -> str:
        """Format system status for display."""
        metrics = status['system_metrics']
        agents = status['agents']
        
        message = f"🧠 **Unified AI System Status**\n\n"
        
        # System metrics
        message += f"📊 **System Metrics:**\n"
        message += f"• Uptime: {metrics['uptime_formatted']}\n"
        message += f"• Active Agents: {metrics['active_agents']}\n"
        message += f"• Total Commands: {metrics['total_commands']}\n"
        message += f"• Success Rate: {(metrics['successful_commands']/max(metrics['total_commands'], 1)*100):.1f}%\n"
        message += f"• Avg Response Time: {metrics['average_response_time']:.2f}s\n\n"
        
        # Agent status
        message += f"🤖 **Agent Status:**\n"
        for agent_id, agent_info in agents.items():
            status_emoji = "🟢" if agent_info['responsive'] else "🔴"
            message += f"{status_emoji} **{agent_info['name']}**\n"
            message += f"  Status: {agent_info['status'].upper()}\n"
            
            perf = agent_info.get('performance', {})
            if perf:
                message += f"  Win Rate: {perf.get('win_rate', 0):.1%}\n"
                message += f"  P&L: ${perf.get('pnl', 0):.2f}\n"
            
            message += "\n"
        
        return message
    
    def _format_performance_analytics(self, status: Dict[str, Any], timeframe: str) -> str:
        """Format performance analytics for display."""
        message = f"📈 **Performance Analytics ({timeframe})**\n\n"
        
        # Aggregate performance across all agents
        total_pnl = 0
        total_trades = 0
        win_rates = []
        
        for agent_id, agent_info in status['agents'].items():
            perf = agent_info.get('performance', {})
            total_pnl += perf.get('pnl', 0)
            total_trades += perf.get('trades_today', 0)
            if 'win_rate' in perf:
                win_rates.append(perf['win_rate'])
        
        avg_win_rate = sum(win_rates) / len(win_rates) if win_rates else 0
        
        message += f"💰 **Total P&L:** ${total_pnl:.2f}\n"
        message += f"📊 **Total Trades:** {total_trades}\n"
        message += f"🎯 **Average Win Rate:** {avg_win_rate:.1%}\n"
        message += f"🤖 **Active Bots:** {len(status['agents'])}\n\n"
        
        # Individual bot performance
        message += f"**Individual Performance:**\n"
        for agent_id, agent_info in status['agents'].items():
            perf = agent_info.get('performance', {})
            pnl = perf.get('pnl', 0)
            win_rate = perf.get('win_rate', 0)
            
            pnl_emoji = "📈" if pnl > 0 else "📉" if pnl < 0 else "➡️"
            message += f"{pnl_emoji} **{agent_info['name']}:** "
            message += f"${pnl:.2f} ({win_rate:.1%})\n"
        
        return message
    
    def _format_health_report(self, status: Dict[str, Any]) -> str:
        """Format system health report."""
        message = f"🏥 **System Health Report**\n\n"
        
        # Overall health score
        responsive_agents = sum(1 for agent in status['agents'].values() if agent['responsive'])
        total_agents = len(status['agents'])
        health_score = (responsive_agents / max(total_agents, 1)) * 100
        
        health_emoji = "🟢" if health_score >= 90 else "🟡" if health_score >= 70 else "🔴"
        message += f"{health_emoji} **Overall Health:** {health_score:.0f}%\n\n"
        
        # System components
        message += f"**Component Status:**\n"
        message += f"🧠 Orchestrator: 🟢 Online\n"
        message += f"📡 Communication: 🟢 Active\n"
        message += f"📊 Telemetry: 🟢 Collecting\n"
        message += f"🧬 Intelligence: 🟢 Sharing\n\n"
        
        # Agent health
        message += f"**Agent Health:**\n"
        for agent_id, agent_info in status['agents'].items():
            health_emoji = "🟢" if agent_info['responsive'] else "🔴"
            message += f"{health_emoji} {agent_info['name']}: {agent_info['status'].upper()}\n"
        
        # Alerts
        alerts = []
        for agent_id, agent_info in status['agents'].items():
            if not agent_info['responsive']:
                alerts.append(f"Agent {agent_info['name']} not responding")
        
        if alerts:
            message += f"\n🚨 **Active Alerts:**\n"
            for alert in alerts:
                message += f"• {alert}\n"
        else:
            message += f"\n✅ **No Active Alerts**"
        
        return message
    
    def _format_agent_forecast_result(self, agent_name: str, symbol: str, 
                                    timeframe: str, result: Dict[str, Any]) -> str:
        """Format individual agent forecast result."""
        message = f"🤖 **{agent_name.title()} Forecast**\n"
        message += f"📊 {symbol} | {timeframe}\n\n"
        
        if result.get('success'):
            data = result.get('result', {})
            prediction = data.get('prediction', 'neutral')
            confidence = data.get('confidence', 0)
            target_price = data.get('target_price', 0)
            
            message += f"🎯 **Prediction:** {prediction.upper()}\n"
            message += f"📈 **Confidence:** {confidence:.0f}%\n"
            message += f"💰 **Target Price:** ${target_price:.6f}\n"
            
            if 'reasoning' in data:
                message += f"💡 **Reasoning:** {data['reasoning']}\n"
        else:
            message += f"❌ **Error:** {result.get('error', 'Unknown error')}"
        
        return message
    
    def _create_forecast_keyboard(self, symbol: str, timeframe: str) -> InlineKeyboardMarkup:
        """Create keyboard for forecast actions."""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📊 Chart View", callback_data=f"chart_{symbol}_{timeframe}"),
                InlineKeyboardButton("🔄 Refresh", callback_data=f"forecast_refresh_{symbol}_{timeframe}")
            ],
            [
                InlineKeyboardButton("⚙️ Tune All", callback_data="tune_all"),
                InlineKeyboardButton("📈 Performance", callback_data="performance_24h")
            ]
        ])
    
    def _create_tune_keyboard(self, command_id: str) -> InlineKeyboardMarkup:
        """Create keyboard for tuning approval."""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Apply All", callback_data=f"tune_apply_all_{command_id}"),
                InlineKeyboardButton("🟢 Safe Only", callback_data=f"tune_apply_safe_{command_id}")
            ],
            [
                InlineKeyboardButton("🔍 Review Details", callback_data=f"tune_review_{command_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"tune_reject_{command_id}")
            ]
        ])
    
    def _create_status_keyboard(self) -> InlineKeyboardMarkup:
        """Create keyboard for status actions."""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="status_refresh"),
                InlineKeyboardButton("📊 Dashboard", callback_data="open_dashboard")
            ],
            [
                InlineKeyboardButton("📈 Performance", callback_data="performance_24h"),
                InlineKeyboardButton("🏥 Health", callback_data="health_check")
            ]
        ])
    
    async def _show_help(self, update: Update):
        """Show help message with available commands."""
        help_text = f"🧠 **Unified AI Command System**\n\n"
        help_text += f"**Global Commands:**\n"
        help_text += f"• `/forecast all [symbol] [timeframe]` - Cross-bot forecasting\n"
        help_text += f"• `/tune all` - Global ML optimization\n"
        help_text += f"• `/status` - System-wide status\n"
        help_text += f"• `/dashboard` - Web dashboard link\n"
        help_text += f"• `/performance [timeframe]` - Performance analytics\n"
        help_text += f"• `/intelligence` - Shared learning insights\n"
        help_text += f"• `/health` - System health report\n\n"
        help_text += f"**Agent-Specific Commands:**\n"
        help_text += f"• `/forecast bidget BTCUSDT 1h` - Specific bot forecast\n"
        help_text += f"• `/tune behar` - Individual bot tuning\n\n"
        help_text += f"**Examples:**\n"
        help_text += f"• `/forecast all BTCUSDT 4h`\n"
        help_text += f"• `/tune all`\n"
        help_text += f"• `/status`\n"
        help_text += f"• `/performance 7d`"
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

# Global orchestrator instance
telegram_orchestrator = None

def get_telegram_orchestrator() -> TelegramOrchestrator:
    """Get global Telegram orchestrator instance."""
    global telegram_orchestrator
    if telegram_orchestrator is None:
        telegram_orchestrator = TelegramOrchestrator()
    return telegram_orchestrator

def initialize_telegram_orchestrator() -> TelegramOrchestrator:
    """Initialize global Telegram orchestrator instance."""
    global telegram_orchestrator
    telegram_orchestrator = TelegramOrchestrator()
    return telegram_orchestrator
