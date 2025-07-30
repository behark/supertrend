"""
Telegram ML Tuning Commands
===========================
Telegram interface for ML-based playbook tuning and optimization.
Provides /tune command and interactive approval workflows.
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import CallbackContext, CallbackQueryHandler

# Local imports
from ml_playbook_tuner import MLPlaybookTuner, get_ml_tuner, TuningSession, PlaybookTuningRecommendation
from trade_memory import get_trade_memory

logger = logging.getLogger(__name__)

class TelegramMLTuning:
    """Handles ML tuning commands and interactions via Telegram"""
    
    def __init__(self):
        """Initialize the Telegram ML tuning handler."""
        self.ml_tuner = get_ml_tuner()
        self.trade_memory = get_trade_memory()
        
        # Store pending sessions for approval
        self.pending_sessions: Dict[str, TuningSession] = {}
        
        logger.info("Telegram ML Tuning handler initialized")
    
    async def handle_tune_command(self, update: Update, context: CallbackContext):
        """Handle /tune command for ML playbook optimization.
        
        Usage: 
        - /tune - Generate tuning recommendations
        - /tune apply - Auto-apply last recommendations (if enabled)
        - /tune status - Show tuning status and history
        - /tune config - Show current tuning configuration
        """
        try:
            args = context.args
            command = args[0] if args else 'generate'
            
            if command == 'status':
                await self._handle_tune_status(update, context)
            elif command == 'config':
                await self._handle_tune_config(update, context)
            elif command == 'apply':
                await self._handle_tune_apply(update, context)
            else:
                await self._handle_tune_generate(update, context)
                
        except Exception as e:
            logger.error(f"Error in tune command: {e}")
            await update.message.reply_text(
                f"❌ Error processing tune command: {str(e)}"
            )
    
    async def _handle_tune_generate(self, update: Update, context: CallbackContext):
        """Generate new tuning recommendations."""
        # Send initial message
        generating_msg = await update.message.reply_text(
            "🧠 **ML Playbook Tuning Analysis**\n"
            "⚡ Analyzing trade history and performance...\n"
            "📊 Training optimization models...\n"
            "💡 This may take a few moments...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            # Check if we have enough trade data
            recent_trades = self.trade_memory.get_history(days=30, limit=100)
            if len(recent_trades) < 20:
                await generating_msg.edit_text(
                    "⚠️ **Insufficient Trade Data**\n\n"
                    f"Found only {len(recent_trades)} trades in the last 30 days.\n"
                    "Need at least 20 trades for meaningful ML tuning.\n\n"
                    "Continue trading and try again later! 📈",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Generate tuning recommendations
            session = self.ml_tuner.generate_tuning_recommendations(lookback_days=30)
            
            # Store session for potential approval
            self.pending_sessions[session.session_id] = session
            
            # Create response message
            message_text = self._format_tuning_session(session)
            
            # Create approval keyboard
            keyboard = self._create_tuning_keyboard(session.session_id)
            
            # Update message with results
            await generating_msg.edit_text(
                message_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error generating tuning recommendations: {e}")
            await generating_msg.edit_text(
                f"❌ **Tuning Generation Failed**\n\n"
                f"Error: {str(e)}\n\n"
                "Please check logs and try again.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    def _format_tuning_session(self, session: TuningSession) -> str:
        """Format tuning session results for Telegram."""
        # Header
        message = f"🧠 **ML Tuning Session Results**\n"
        message += f"📅 {session.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # Summary stats
        message += f"📊 **Analysis Summary**\n"
        message += f"• Trades Analyzed: {session.total_trades_analyzed}\n"
        message += f"• Data Quality: {session.data_quality_score:.1%}\n"
        message += f"• Recommendations: {len(session.recommendations)}\n"
        message += f"• Lookback Period: {session.lookback_days} days\n\n"
        
        if not session.recommendations:
            message += "✅ **No Changes Needed**\n"
            message += "Current playbook parameters appear optimal based on recent performance!"
            return message
        
        # Group recommendations by regime
        regime_groups = {}
        for rec in session.recommendations:
            if rec.regime not in regime_groups:
                regime_groups[rec.regime] = []
            regime_groups[rec.regime].append(rec)
        
        message += "💡 **Optimization Recommendations**\n\n"
        
        for regime, recommendations in regime_groups.items():
            message += f"**{regime.upper().replace('_', ' ')} Regime:**\n"
            
            for rec in recommendations:
                # Risk indicator
                risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}
                risk_indicator = risk_emoji.get(rec.risk_level, "⚪")
                
                message += f"{risk_indicator} *{rec.parameter}*: "
                message += f"{rec.current_value} → {rec.recommended_value:.2f}\n"
                message += f"   Confidence: {rec.confidence:.0%} | "
                message += f"Expected +{rec.expected_improvement:.1%}\n"
                message += f"   _{rec.reasoning}_\n\n"
        
        # Model performance summary
        if session.model_performance:
            message += "🎯 **Model Performance**\n"
            for model, score in session.model_performance.items():
                if isinstance(score, float):
                    message += f"• {model}: {score:.3f}\n"
        
        message += "\n⚠️ **Review Required**\n"
        message += "Please review recommendations before applying to live trading."
        
        return message
    
    def _create_tuning_keyboard(self, session_id: str) -> InlineKeyboardMarkup:
        """Create inline keyboard for tuning approval."""
        keyboard = [
            [
                InlineKeyboardButton("✅ Apply All", callback_data=f"tune_apply_all_{session_id}"),
                InlineKeyboardButton("🔍 Review", callback_data=f"tune_review_{session_id}")
            ],
            [
                InlineKeyboardButton("⚙️ Apply Safe Only", callback_data=f"tune_apply_safe_{session_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"tune_reject_{session_id}")
            ],
            [
                InlineKeyboardButton("📊 Show Details", callback_data=f"tune_details_{session_id}")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def handle_tuning_callback(self, update: Update, context: CallbackContext):
        """Handle inline keyboard callbacks for tuning decisions."""
        query = update.callback_query
        await query.answer()
        
        try:
            callback_data = query.data
            action_parts = callback_data.split('_')
            action = '_'.join(action_parts[1:-1])  # e.g., 'apply_all'
            session_id = action_parts[-1]
            
            if session_id not in self.pending_sessions:
                await query.edit_message_text(
                    "❌ Session expired or not found. Please generate new recommendations.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            session = self.pending_sessions[session_id]
            
            if action == 'apply_all':
                await self._apply_all_recommendations(query, session)
            elif action == 'apply_safe':
                await self._apply_safe_recommendations(query, session)
            elif action == 'review':
                await self._show_detailed_review(query, session)
            elif action == 'reject':
                await self._reject_recommendations(query, session)
            elif action == 'details':
                await self._show_technical_details(query, session)
            else:
                await query.edit_message_text("❌ Unknown action")
                
        except Exception as e:
            logger.error(f"Error handling tuning callback: {e}")
            await query.edit_message_text(f"❌ Error: {str(e)}")
    
    async def _apply_all_recommendations(self, query, session: TuningSession):
        """Apply all recommendations from the session."""
        try:
            result = self.ml_tuner.apply_recommendations(session, auto_apply=True)
            
            # Remove from pending
            if session.session_id in self.pending_sessions:
                del self.pending_sessions[session.session_id]
            
            message = f"✅ **Applied ML Tuning Recommendations**\n\n"
            message += f"📊 Applied: {result['applied_count']}/{result['total_recommendations']}\n"
            
            if result.get('errors'):
                message += f"⚠️ Errors: {len(result['errors'])}\n"
                for error in result['errors'][:3]:  # Show first 3 errors
                    message += f"• {error}\n"
            
            message += f"\n🎯 **Playbooks Updated**\n"
            message += "New parameters are now active for live trading!\n"
            message += "Monitor performance and use `/tune status` to track results."
            
            await query.edit_message_text(message, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            await query.edit_message_text(
                f"❌ **Application Failed**\n\nError: {str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def _apply_safe_recommendations(self, query, session: TuningSession):
        """Apply only low-risk recommendations."""
        try:
            # Filter to only low-risk recommendations
            safe_recommendations = [
                rec for rec in session.recommendations 
                if rec.risk_level == 'low'
            ]
            
            if not safe_recommendations:
                await query.edit_message_text(
                    "ℹ️ **No Safe Recommendations**\n\n"
                    "All recommendations are medium or high risk.\n"
                    "Consider manual review or reject all.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Create modified session with only safe recommendations
            safe_session = TuningSession(
                session_id=session.session_id + "_safe",
                timestamp=session.timestamp,
                recommendations=safe_recommendations,
                model_performance=session.model_performance,
                data_quality_score=session.data_quality_score,
                total_trades_analyzed=session.total_trades_analyzed,
                lookback_days=session.lookback_days
            )
            
            result = self.ml_tuner.apply_recommendations(safe_session, auto_apply=True)
            
            message = f"✅ **Applied Safe Recommendations Only**\n\n"
            message += f"📊 Applied: {result['applied_count']} low-risk changes\n"
            message += f"⚠️ Skipped: {len(session.recommendations) - len(safe_recommendations)} higher-risk changes\n\n"
            message += "🎯 Conservative optimization complete!\n"
            message += "Use `/tune` again later to review remaining recommendations."
            
            await query.edit_message_text(message, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            await query.edit_message_text(
                f"❌ **Safe Application Failed**\n\nError: {str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def _show_detailed_review(self, query, session: TuningSession):
        """Show detailed review of each recommendation."""
        message = f"🔍 **Detailed Recommendation Review**\n\n"
        
        for i, rec in enumerate(session.recommendations, 1):
            risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}
            
            message += f"**{i}. {rec.regime.upper()} - {rec.parameter}**\n"
            message += f"{risk_emoji.get(rec.risk_level, '⚪')} Risk Level: {rec.risk_level.upper()}\n"
            message += f"📈 Current: {rec.current_value}\n"
            message += f"🎯 Recommended: {rec.recommended_value:.3f}\n"
            message += f"🎲 Confidence: {rec.confidence:.0%}\n"
            message += f"📊 Expected Improvement: +{rec.expected_improvement:.1%}\n"
            message += f"💡 Reasoning: _{rec.reasoning}_\n\n"
        
        # Create new keyboard for individual actions
        keyboard = [
            [
                InlineKeyboardButton("✅ Apply All", callback_data=f"tune_apply_all_{session.session_id}"),
                InlineKeyboardButton("🟢 Safe Only", callback_data=f"tune_apply_safe_{session.session_id}")
            ],
            [
                InlineKeyboardButton("❌ Reject All", callback_data=f"tune_reject_{session.session_id}"),
                InlineKeyboardButton("🔙 Back", callback_data=f"tune_back_{session.session_id}")
            ]
        ]
        
        await query.edit_message_text(
            message, 
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _reject_recommendations(self, query, session: TuningSession):
        """Reject all recommendations."""
        # Remove from pending
        if session.session_id in self.pending_sessions:
            del self.pending_sessions[session.session_id]
        
        message = f"❌ **Recommendations Rejected**\n\n"
        message += f"Rejected {len(session.recommendations)} recommendations.\n"
        message += "Current playbook parameters remain unchanged.\n\n"
        message += "💡 You can generate new recommendations anytime with `/tune`"
        
        await query.edit_message_text(message, parse_mode=ParseMode.MARKDOWN)
    
    async def _show_technical_details(self, query, session: TuningSession):
        """Show technical details about the ML models and analysis."""
        message = f"🔬 **Technical Analysis Details**\n\n"
        
        message += f"**Data Analysis:**\n"
        message += f"• Session ID: `{session.session_id}`\n"
        message += f"• Trades Analyzed: {session.total_trades_analyzed}\n"
        message += f"• Data Quality Score: {session.data_quality_score:.3f}\n"
        message += f"• Analysis Period: {session.lookback_days} days\n\n"
        
        if session.model_performance:
            message += f"**ML Model Performance:**\n"
            for model_name, metrics in session.model_performance.items():
                if isinstance(metrics, dict):
                    message += f"• {model_name}:\n"
                    for metric, value in metrics.items():
                        if isinstance(value, float):
                            message += f"  - {metric}: {value:.3f}\n"
                elif isinstance(metrics, float):
                    message += f"• {model_name}: {metrics:.3f}\n"
            message += "\n"
        
        message += f"**Recommendation Statistics:**\n"
        risk_counts = {}
        for rec in session.recommendations:
            risk_counts[rec.risk_level] = risk_counts.get(rec.risk_level, 0) + 1
        
        for risk, count in risk_counts.items():
            message += f"• {risk.title()} Risk: {count}\n"
        
        message += f"\n**Generated:** {session.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Back button
        keyboard = [[InlineKeyboardButton("🔙 Back to Review", callback_data=f"tune_back_{session.session_id}")]]
        
        await query.edit_message_text(
            message, 
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _handle_tune_status(self, update: Update, context: CallbackContext):
        """Show tuning status and history."""
        try:
            summary = self.ml_tuner.get_tuning_summary(days=7)
            
            if 'message' in summary:
                message = f"📊 **ML Tuning Status**\n\n{summary['message']}\n\n"
                message += "Use `/tune` to generate your first recommendations!"
            else:
                message = f"📊 **ML Tuning Status (Last 7 Days)**\n\n"
                message += f"🔄 Sessions: {summary['recent_sessions']}\n"
                message += f"💡 Total Recommendations: {summary['total_recommendations']}\n"
                message += f"📈 Avg Data Quality: {summary['avg_data_quality_score']:.1%}\n"
                message += f"🕐 Last Session: {summary['last_session']}\n\n"
                
                if summary.get('model_performance'):
                    message += f"🎯 **Latest Model Performance:**\n"
                    for model, score in summary['model_performance'].items():
                        if isinstance(score, float):
                            message += f"• {model}: {score:.3f}\n"
            
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error getting status: {str(e)}")
    
    async def _handle_tune_config(self, update: Update, context: CallbackContext):
        """Show current tuning configuration."""
        config = self.ml_tuner.config
        
        message = f"⚙️ **ML Tuning Configuration**\n\n"
        message += f"📊 Min Trades Required: {config['min_trades_for_tuning']}\n"
        message += f"📅 Default Lookback: {config['lookback_days']} days\n"
        message += f"🎯 Confidence Threshold: {config['confidence_threshold']:.0%}\n"
        message += f"📈 Max Parameter Change: {config['max_parameter_change']:.0%}\n"
        message += f"🔄 Retraining Frequency: {config['retraining_frequency']} days\n"
        message += f"👤 Human Review Required: {'Yes' if config['human_review_required'] else 'No'}\n\n"
        
        message += f"💡 Use `/tune` to generate optimization recommendations!"
        
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    
    async def _handle_tune_apply(self, update: Update, context: CallbackContext):
        """Apply last pending recommendations."""
        if not self.pending_sessions:
            await update.message.reply_text(
                "ℹ️ No pending recommendations to apply.\n"
                "Use `/tune` to generate new recommendations first!"
            )
            return
        
        # Get most recent session
        latest_session = max(
            self.pending_sessions.values(), 
            key=lambda s: s.timestamp
        )
        
        try:
            result = self.ml_tuner.apply_recommendations(latest_session, auto_apply=True)
            
            message = f"✅ **Auto-Applied Latest Recommendations**\n\n"
            message += f"📊 Applied: {result['applied_count']}/{result['total_recommendations']}\n"
            message += f"🕐 Session: {latest_session.timestamp.strftime('%H:%M:%S')}\n\n"
            
            if result.get('errors'):
                message += f"⚠️ Errors encountered: {len(result['errors'])}\n"
            
            message += "🎯 Playbook parameters updated for live trading!"
            
            # Remove applied session
            del self.pending_sessions[latest_session.session_id]
            
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ **Auto-Apply Failed**\n\nError: {str(e)}\n\n"
                "Use `/tune` with manual review instead."
            )


# Global instance
telegram_ml_tuning = None

def get_telegram_ml_tuning() -> TelegramMLTuning:
    """Get global Telegram ML tuning instance."""
    global telegram_ml_tuning
    if telegram_ml_tuning is None:
        telegram_ml_tuning = TelegramMLTuning()
    return telegram_ml_tuning

def initialize_telegram_ml_tuning() -> TelegramMLTuning:
    """Initialize global Telegram ML tuning instance."""
    global telegram_ml_tuning
    telegram_ml_tuning = TelegramMLTuning()
    return telegram_ml_tuning
