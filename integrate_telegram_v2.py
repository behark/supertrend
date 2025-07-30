#!/usr/bin/env python3
"""
Telegram Command Center V2 Integration Example
---------------------------------------------
Shows how to integrate the new Telegram Command Center V2 with the main bot
"""
import os
import sys
import logging
from typing import Optional

# Local imports
from telegram_command_center_v2 import TelegramCommandCenterV2
from market_regime import MarketRegime
from playbook import Playbook
from trade_planner import SmartTradePlanner

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("telegram_integration.log")
    ]
)

logger = logging.getLogger(__name__)

class BotIntegration:
    """
    Example class showing how to integrate TelegramCommandCenterV2 with the main bot
    
    In a real scenario, replace this with your actual bot class
    """
    def __init__(self, data_dir='data'):
        self.data_dir = data_dir
        self.strategy = 'auto'
        self.symbols = ['BTCUSDT', 'ETHUSDT']
        self.timeframe = '1h'
        self.dataframes = {}  # In real bot, this would contain actual dataframes
        self.signal_count = 0
        self.is_paused = False
        
        # Initialize components
        self.market_regime = MarketRegime(data_dir=data_dir)
        self.playbook = Playbook(data_dir=data_dir)
        self.trade_planner = SmartTradePlanner(data_dir=data_dir)
        
        # Initialize Telegram command center and pass bot instance for integration
        self.telegram = TelegramCommandCenterV2(
            bot_instance=self,
            data_dir=data_dir
        )
        
        logger.info("Bot initialized with Telegram Command Center V2")
        
    def set_paused(self, paused: bool) -> None:
        """Set bot paused state"""
        self.is_paused = paused
        logger.info(f"Bot paused state set to {paused}")
        
    def restart(self) -> None:
        """Restart the bot"""
        logger.info("Restarting bot...")
        # Actual restart logic would go here
        
    def shutdown(self) -> None:
        """Shutdown the bot"""
        logger.info("Shutting down bot...")
        # Actual shutdown logic would go here
        sys.exit(0)
        
    def start(self) -> None:
        """Start the bot with integrated Telegram command center"""
        logger.info("Starting bot with Telegram Command Center V2...")
        
        # Start Telegram polling
        self.telegram.start_polling()
        
        # Simulated bot main loop
        import time
        try:
            while True:
                if not self.is_paused:
                    # Simulate some bot activity
                    logger.info("Bot is running... (Press Ctrl+C to exit)")
                else:
                    logger.info("Bot is paused... (Press Ctrl+C to exit)")
                    
                # Sleep for a while
                time.sleep(10)
                
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
            self.telegram.stop()
            logger.info("Bot shutdown complete")
            
    def __del__(self):
        """Clean up resources"""
        if hasattr(self, 'telegram'):
            self.telegram.stop()

if __name__ == "__main__":
    # Create and start the bot
    try:
        bot = BotIntegration()
        bot.start()
    except Exception as e:
        logger.error(f"Error starting bot: {str(e)}", exc_info=True)
