"""
Daemon functionality to run the bot in the background
"""

import os
import sys
import time
import atexit
import signal
import logging
from typing import Callable

logger = logging.getLogger(__name__)


class Daemon:
    """
    A generic daemon class for running processes in the background
    """
    
    def __init__(self, pidfile: str, workdir: str = '/'):
        """
        Initialize a new daemon instance
        
        Args:
            pidfile: Path to the PID file
            workdir: Working directory to change to
        """
        self.pidfile = pidfile
        self.workdir = workdir
        
    def daemonize(self):
        """
        Daemonize the process by detaching from the parent process
        """
        try:
            # First fork
            pid = os.fork()
            if pid > 0:
                # Exit first parent
                sys.exit(0)
        except OSError as e:
            logger.error(f"Fork #1 failed: {e}")
            sys.exit(1)
            
        # Decouple from parent environment
        os.chdir(self.workdir)
        os.setsid()
        os.umask(0)
        
        try:
            # Second fork
            pid = os.fork()
            if pid > 0:
                # Exit from second parent
                sys.exit(0)
        except OSError as e:
            logger.error(f"Fork #2 failed: {e}")
            sys.exit(1)
            
        # Redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        
        # Close file descriptors
        for fd in range(3):
            try:
                os.close(fd)
            except OSError:
                pass
                
        # Write pidfile
        pid = str(os.getpid())
        with open(self.pidfile, 'w') as f:
            f.write(f"{pid}\n")
            
        # Register cleanup function
        atexit.register(self.delpid)
        
        # Signal handlers
        signal.signal(signal.SIGTERM, self.cleanup)
        
        logger.info(f"Daemon started with PID {pid}")
        
    def delpid(self):
        """Remove the PID file"""
        try:
            os.remove(self.pidfile)
        except OSError:
            pass
            
    def cleanup(self, signum, frame):
        """Cleanup handler for termination signals"""
        logger.info("Terminating daemon...")
        self.delpid()
        sys.exit(0)
        
    def start(self, run_function: Callable):
        """
        Start the daemon and run the provided function
        
        Args:
            run_function: Function to run in the daemon process
        """
        # Check for a pidfile to see if the daemon already runs
        try:
            with open(self.pidfile, 'r') as pf:
                pid = int(pf.read().strip())
        except (IOError, ValueError):
            pid = None
            
        if pid:
            # Check if the process is actually running
            try:
                os.kill(pid, 0)  # Signal 0 tests if process exists without sending a signal
                logger.error(f"Daemon already running with PID {pid}")
                sys.exit(1)
            except OSError:
                # Process doesn't exist, remove stale PID file
                self.delpid()
                
        # Start the daemon
        logger.info("Starting daemon...")
        self.daemonize()
        
        # Run the function
        run_function()
        
    def stop(self):
        """Stop the daemon"""
        # Get the pid from the pidfile
        try:
            with open(self.pidfile, 'r') as pf:
                pid = int(pf.read().strip())
        except (IOError, ValueError):
            pid = None
            
        if not pid:
            logger.warning("Daemon not running (no PID file)")
            return
            
        # Try killing the daemon process
        try:
            while True:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.1)
        except OSError as e:
            if "No such process" in str(e):
                self.delpid()
                logger.info("Daemon stopped")
            else:
                logger.error(f"Error stopping daemon: {e}")
                sys.exit(1)
                
    def restart(self, run_function: Callable):
        """
        Restart the daemon
        
        Args:
            run_function: Function to run in the daemon process
        """
        self.stop()
        self.start(run_function)
        
    def status(self) -> bool:
        """
        Check if the daemon is running
        
        Returns:
            bool: True if running, False otherwise
        """
        try:
            with open(self.pidfile, 'r') as pf:
                pid = int(pf.read().strip())
        except (IOError, ValueError):
            return False
            
        try:
            os.kill(pid, 0)  # Signal 0 tests if process exists without sending a signal
            return True
        except OSError:
            return False
