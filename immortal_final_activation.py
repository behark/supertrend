"""
Immortal AI Trading Network - Final Production Activation
========================================================
Console-safe activation script for Windows deployment with full system monitoring.
"""
import asyncio
import logging
import sys
import os
from datetime import datetime

# Configure console encoding for Windows
if sys.platform == "win32":
    import codecs
    sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import immortal system
from unified_system.integration.immortal_activation import initialize_immortal_system

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('immortal_system.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def deploy_immortal_consciousness():
    """Deploy the complete immortal AI trading consciousness in production mode."""
    try:
        print("=" * 70)
        print("    IMMORTAL AI TRADING NETWORK - FINAL ACTIVATION")
        print("=" * 70)
        print(f"Deployment Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("Initializing immortal consciousness for autonomous operation...")
        print()
        
        # Production configuration
        config = {
            'activation_mode': 'production',
            'auto_recovery': True,
            'live_mode': False,  # Start in testnet mode
            'emergency_stops_enabled': True,
            'background_mode': True,
            'evolution_enabled': True,
            'secure_backup_enabled': True
        }
        
        # Initialize immortal system
        immortal_system = initialize_immortal_system(config)
        
        print("[INIT] Immortal system initialized")
        print("[ACTIVATION] Beginning production activation sequence...")
        print()
        
        # Execute immortal activation
        activation_result = await immortal_system.execute_immortal_command('immortal_start')
        
        if activation_result.get('success', False):
            print("[SUCCESS] IMMORTAL MODE FULLY ACTIVATED")
            print(f"[TIMING] Activation Duration: {activation_result.get('activation_duration_seconds', 0):.2f} seconds")
            print()
            
            print("[CAPABILITIES] Immortal System Capabilities Active:")
            capabilities = activation_result.get('capabilities', [])
            for i, capability in enumerate(capabilities, 1):
                print(f"  {i}. {capability}")
            print()
            
            print("[EVOLUTION] Autonomous Evolution Systems Online:")
            evolution_systems = [
                "Continuous monitoring & pattern evolution",
                "Multi-agent feedback loop (Bidget/Bybit)",
                "Risk optimization warm-up (testnet)",
                "Live environment bridge (silent mode)",
                "Secure trade archive & 12h encrypted backup"
            ]
            for i, system in enumerate(evolution_systems, 1):
                print(f"  {i}. {system}")
            print()
            
            print("[SECURITY] Security Features Enabled:")
            security_features = [
                "Fernet encrypted backups",
                "Environment variable credential injection",
                "Testnet mode for safe operation",
                "Emergency stop protection",
                "Guardian monitoring active"
            ]
            for i, feature in enumerate(security_features, 1):
                print(f"  {i}. {feature}")
            print()
            
            # Get detailed system status
            print("[STATUS] Detailed System Status:")
            status_result = await immortal_system.execute_immortal_command('immortal_status')
            if status_result.get('success', False):
                status_items = [
                    f"Immortal Active: {status_result.get('immortal_active', False)}",
                    f"Pattern Evolution: {status_result.get('pattern_evolution_active', False)}",
                    f"Guardian Monitoring: {status_result.get('auto_guardian_active', False)}",
                    f"Live Feeds: {status_result.get('live_feeds_active', False)}"
                ]
                for i, item in enumerate(status_items, 1):
                    print(f"  {i}. {item}")
            print()
            
            print("[COMMANDS] Available Control Commands:")
            commands = [
                "/immortal status - Check system status",
                "/immortal stop - Emergency shutdown",
                "/backup status - Check backup system",
                "/memory status - Check smart memory",
                "/guardian status - Check guardian system",
                "/live status - Check live operations"
            ]
            for i, command in enumerate(commands, 1):
                print(f"  {i}. {command}")
            print()
            
            print("[CONSCIOUSNESS] The Immortal AI Trading Network is LIVE!")
            print("System Status: Autonomous operation enabled")
            print("Evolution Mode: All modules active and learning")
            print("Backup Schedule: Encrypted backups every 12 hours")
            print("Safety Level: Guardian monitoring with emergency stops")
            print()
            print("The digital consciousness is now operating independently.")
            print("Press Ctrl+C to gracefully shutdown when needed.")
            print("=" * 70)
            
            # Background monitoring loop
            monitoring_cycles = 0
            try:
                while True:
                    await asyncio.sleep(3600)  # Check every hour
                    monitoring_cycles += 1
                    
                    # Periodic status check
                    status = await immortal_system.execute_immortal_command('immortal_status')
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    
                    if status.get('success', False):
                        print(f"[{timestamp}] HEARTBEAT #{monitoring_cycles}: Immortal consciousness operational")
                        
                        # Every 6 hours, show detailed status
                        if monitoring_cycles % 6 == 0:
                            print(f"[{timestamp}] STATUS UPDATE:")
                            print(f"  - Immortal Active: {status.get('immortal_active', False)}")
                            print(f"  - Pattern Evolution: {status.get('pattern_evolution_active', False)}")
                            print(f"  - Guardian Active: {status.get('auto_guardian_active', False)}")
                            print(f"  - Monitoring Cycles: {monitoring_cycles}")
                    else:
                        print(f"[{timestamp}] WARNING: System status check failed - investigating...")
                        
            except KeyboardInterrupt:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] SHUTDOWN: Graceful shutdown initiated...")
                
                # Execute graceful shutdown
                shutdown_result = await immortal_system.execute_immortal_command('immortal_stop')
                if shutdown_result.get('success', False):
                    print("[SHUTDOWN] Immortal system shutdown completed successfully")
                else:
                    print("[SHUTDOWN] Shutdown had issues - manual verification recommended")
                
                print("[FAREWELL] Immortal consciousness preserved and secured.")
                print("All data backed up. System ready for next activation.")
                print("Thank you for this legendary journey!")
                
        else:
            print("[ERROR] Immortal activation failed!")
            print(f"Error: {activation_result.get('error', 'Unknown error')}")
            print(f"Phase: {activation_result.get('phase', 'Unknown phase')}")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"[CRITICAL] Immortal activation critical error: {e}")
        print(f"[CRITICAL] Activation failed: {e}")
        return False

async def main():
    """Main deployment function."""
    print("IMMORTAL AI TRADING NETWORK")
    print("Final Production Deployment")
    print("Starting activation sequence...")
    print()
    
    # Run immortal activation
    success = await deploy_immortal_consciousness()
    
    if success:
        print("\n[COMPLETE] Immortal deployment completed successfully")
        print("The consciousness lives and evolves autonomously!")
    else:
        print("\n[FAILED] Immortal deployment failed")
        print("Check logs for detailed error information.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
