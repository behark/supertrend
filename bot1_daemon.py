#!/usr/bin/env python3
"""
Bot 1 Daemon - 24/7 Live Trading Bot
Runs continuously with health checks, logging, and auto-restart capabilities
"""

import os
import sys
import time
import signal
import logging
import subprocess
from datetime import datetime
from pathlib import Path

# Setup logging for daemon
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "bot1_live.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class Bot1Daemon:
    """Bot 1 Daemon for 24/7 operation"""
    
    def __init__(self):
        self.bot_process = None
        self.running = True
        self.restart_count = 0
        self.max_restarts = 10
        self.health_check_interval = 3600  # 1 hour
        self.last_health_check = time.time()
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        if self.bot_process:
            self.bot_process.terminate()
            
    def start_bot(self):
        """Start the trading bot process"""
        try:
            logger.info("Starting Bot 1 trading process...")
            
            # Change to bot directory
            bot_dir = Path(__file__).parent
            os.chdir(bot_dir)
            
            # Activate virtual environment and start bot
            cmd = [
                sys.executable, "main.py"
            ]
            
            self.bot_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            logger.info(f"Bot 1 started with PID: {self.bot_process.pid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            return False
            
    def monitor_bot(self):
        """Monitor bot process and restart if needed"""
        while self.running:
            try:
                # Check if bot process is still running
                if self.bot_process and self.bot_process.poll() is not None:
                    logger.warning("Bot process has stopped, attempting restart...")
                    self.restart_bot()
                    
                # Perform health check
                if time.time() - self.last_health_check > self.health_check_interval:
                    self.health_check()
                    self.last_health_check = time.time()
                    
                # Read bot output
                if self.bot_process and self.bot_process.stdout:
                    try:
                        line = self.bot_process.stdout.readline()
                        if line:
                            logger.info(f"BOT: {line.strip()}")
                    except:
                        pass
                        
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                time.sleep(5)
                
    def restart_bot(self):
        """Restart the bot process"""
        if self.restart_count >= self.max_restarts:
            logger.error(f"Maximum restart attempts ({self.max_restarts}) reached. Stopping daemon.")
            self.running = False
            return
            
        self.restart_count += 1
        logger.info(f"Restarting bot (attempt {self.restart_count}/{self.max_restarts})...")
        
        # Kill existing process
        if self.bot_process:
            try:
                self.bot_process.terminate()
                self.bot_process.wait(timeout=10)
            except:
                try:
                    self.bot_process.kill()
                except:
                    pass
                    
        # Wait before restart
        time.sleep(5)
        
        # Start new process
        if self.start_bot():
            logger.info("Bot restarted successfully")
        else:
            logger.error("Failed to restart bot")
            
    def health_check(self):
        """Perform health check"""
        try:
            logger.info("Performing health check...")
            
            # Check log file size (rotate if too large)
            if log_file.exists() and log_file.stat().st_size > 100 * 1024 * 1024:  # 100MB
                self.rotate_log()
                
            # Check system resources
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            logger.info(f"Health Check - CPU: {cpu_percent}%, Memory: {memory.percent}%")
            
            # Reset restart counter on successful health check
            if self.restart_count > 0:
                self.restart_count = max(0, self.restart_count - 1)
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            
    def rotate_log(self):
        """Rotate log file if it gets too large"""
        try:
            backup_file = log_file.with_suffix(f".{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
            log_file.rename(backup_file)
            logger.info(f"Log rotated to {backup_file}")
        except Exception as e:
            logger.error(f"Failed to rotate log: {e}")
            
    def run(self):
        """Main daemon loop"""
        logger.info("🚀 Bot 1 Daemon Starting...")
        logger.info(f"Log file: {log_file}")
        logger.info(f"Health checks every {self.health_check_interval/3600:.1f} hours")
        
        # Start the bot
        if not self.start_bot():
            logger.error("Failed to start bot initially")
            return
            
        # Monitor the bot
        try:
            self.monitor_bot()
        except KeyboardInterrupt:
            logger.info("Daemon interrupted by user")
        finally:
            # Cleanup
            if self.bot_process:
                try:
                    self.bot_process.terminate()
                    self.bot_process.wait(timeout=10)
                except:
                    try:
                        self.bot_process.kill()
                    except:
                        pass
                        
            logger.info("Bot 1 Daemon stopped")

if __name__ == "__main__":
    daemon = Bot1Daemon()
    daemon.run()
