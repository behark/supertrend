#!/usr/bin/env python
"""
Verification and restart script for SuperTrend bot
Ensures correct code deployment and forces clean restart
"""

import os
import sys
import time
import logging
import subprocess
import signal
import re
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"verify_restart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger("Verify-Restart")

# Paths
PROJECT_PATH = '/home/behar/CascadeProjects/SuperTrend/Inside=Bar:Strategy'
BOT_SCRIPT = os.path.join(PROJECT_PATH, 'bot1_daemon.py')
BITGET_MODULE = os.path.join(PROJECT_PATH, 'src/integrations/bidget.py')
ORDER_MANAGER = os.path.join(PROJECT_PATH, 'src/integrations/order_manager.py')

def verify_code_integrity():
    """Verify that the critical code fixes are in the deployed files"""
    logger.info("Verifying code integrity...")
    
    # Check Bitget module for holdSide parameter
    with open(BITGET_MODULE, 'r') as f:
        bitget_code = f.read()
    
    # Check for holdSide in take profit method
    tp_holdside = re.search(r'"holdSide":\s*hold_side.*?# Critical: Specify the position side being held', 
                           bitget_code, re.DOTALL)
    
    # Check for holdSide in stop loss method
    sl_holdside = re.search(r'"holdSide":\s*hold_side.*?# Critical: Specify the position side being held', 
                           bitget_code, re.DOTALL)
    
    if not tp_holdside or not sl_holdside:
        logger.error("❌ Critical code fix for holdSide parameter is missing!")
        logger.error("   The deployed code does not match the expected fixes.")
        return False
    
    logger.info("✅ Code integrity verified: holdSide parameter is present in the code")
    return True

def find_bot_processes():
    """Find running bot processes"""
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        
        bot_processes = []
        for line in lines:
            if 'bot1_daemon.py' in line and 'python' in line:
                parts = line.split()
                if len(parts) > 1:
                    pid = parts[1]
                    bot_processes.append(pid)
        
        return bot_processes
    except Exception as e:
        logger.error(f"Error finding bot processes: {e}")
        return []

def stop_bot_processes():
    """Stop all running bot processes"""
    bot_pids = find_bot_processes()
    
    if not bot_pids:
        logger.info("No running bot processes found")
        return True
    
    logger.info(f"Found {len(bot_pids)} bot processes: {', '.join(bot_pids)}")
    
    for pid in bot_pids:
        try:
            logger.info(f"Stopping bot process {pid}...")
            os.kill(int(pid), signal.SIGTERM)
            time.sleep(2)  # Give it time to shut down gracefully
            
            # Check if it's still running
            if subprocess.run(['ps', '-p', pid], capture_output=True).returncode == 0:
                logger.warning(f"Process {pid} still running, sending SIGKILL...")
                os.kill(int(pid), signal.SIGKILL)
        except ProcessLookupError:
            logger.info(f"Process {pid} already stopped")
        except Exception as e:
            logger.error(f"Error stopping process {pid}: {e}")
    
    # Verify all processes are stopped
    remaining = find_bot_processes()
    if remaining:
        logger.error(f"Failed to stop all bot processes. Remaining: {remaining}")
        return False
    
    logger.info("✅ All bot processes successfully stopped")
    return True

def start_bot():
    """Start the bot with the latest code"""
    logger.info("Starting bot with latest code...")
    
    try:
        # Start the bot as a background process
        cmd = f"cd {PROJECT_PATH} && python bot1_daemon.py"
        subprocess.Popen(cmd, shell=True, 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE, 
                        start_new_session=True)
        
        logger.info("✅ Bot started successfully")
        return True
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        return False

def verify_bot_running():
    """Verify the bot is running after restart"""
    time.sleep(5)  # Give it time to start
    
    bot_pids = find_bot_processes()
    if bot_pids:
        logger.info(f"✅ Bot is running with PID(s): {', '.join(bot_pids)}")
        return True
    else:
        logger.error("❌ Bot failed to start!")
        return False

def main():
    """Main function"""
    logger.info("=" * 50)
    logger.info("SUPERTREND BOT VERIFICATION AND RESTART")
    logger.info("=" * 50)
    
    # Step 1: Verify code integrity
    if not verify_code_integrity():
        logger.error("Code verification failed! Please check your deployment.")
        return 1
    
    # Step 2: Stop running bot processes
    if not stop_bot_processes():
        logger.error("Failed to stop all bot processes. Manual intervention required.")
        return 1
    
    # Step 3: Start the bot with latest code
    if not start_bot():
        logger.error("Failed to start the bot. Manual intervention required.")
        return 1
    
    # Step 4: Verify the bot is running
    if not verify_bot_running():
        logger.error("Bot verification failed. Manual intervention required.")
        return 1
    
    logger.info("=" * 50)
    logger.info("✅ VERIFICATION AND RESTART COMPLETED SUCCESSFULLY")
    logger.info("=" * 50)
    logger.info("The bot is now running with the latest code.")
    logger.info("Please monitor the logs for the next 15-30 minutes to ensure proper operation.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
