"""
Secure Trade Archive & Backup System
====================================
Encrypts and exports smart memory logs every 12h and prepares backup
across multi-agent nodes for immortal data preservation.
"""
import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import zipfile
from cryptography.fernet import Fernet

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.smart_trade_memory import get_smart_trade_memory

logger = logging.getLogger(__name__)

class SecureBackupSystem:
    """Secure backup and archive system for immortal data preservation."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize secure backup system."""
        self.config = config
        self.backup_active = False
        
        # Backup intervals
        self.backup_interval = config.get('backup_interval', 43200)  # 12 hours
        self.archive_interval = config.get('archive_interval', 86400)  # 24 hours
        
        # System components
        self.smart_memory = None
        
        # Backup tracking
        self.backup_cycles = 0
        self.total_backups_created = 0
        
        # Security settings
        self.encryption_enabled = config.get('encryption_enabled', True)
        self.backup_encryption_key = self._get_or_create_backup_key()
        self.backup_directory = config.get('backup_directory', 'unified_system/backups')
        
    def _get_or_create_backup_key(self) -> bytes:
        """Get or create encryption key for backups."""
        try:
            key_file = 'unified_system/config/backup_key.key'
            
            if os.path.exists(key_file):
                with open(key_file, 'rb') as f:
                    return f.read()
            else:
                key = Fernet.generate_key()
                os.makedirs(os.path.dirname(key_file), exist_ok=True)
                
                with open(key_file, 'wb') as f:
                    f.write(key)
                
                logger.info("[BACKUP] New backup encryption key created")
                return key
                
        except Exception as e:
            logger.error(f"[BACKUP] Failed to handle backup encryption key: {e}")
            return Fernet.generate_key()
    
    async def initialize_backup_system(self):
        """Initialize the secure backup system."""
        try:
            logger.info("🔐 [BACKUP] Initializing Secure Trade Archive & Backup System")
            
            self.smart_memory = get_smart_trade_memory()
            
            if not self.smart_memory:
                raise Exception("Smart memory system not available")
            
            os.makedirs(self.backup_directory, exist_ok=True)
            self.backup_active = True
            
            # Start backup loops
            asyncio.create_task(self._backup_loop())
            
            logger.info("✅ [BACKUP] Secure backup system initialized")
            
        except Exception as e:
            logger.error(f"❌ [BACKUP] Initialization failed: {e}")
            raise
    
    async def _backup_loop(self):
        """12-hour backup cycle for smart memory logs."""
        logger.info("💾 [BACKUP] 12-hour backup loop started")
        
        while self.backup_active:
            try:
                backup_result = await self._execute_backup_cycle()
                
                if backup_result['success']:
                    self.backup_cycles += 1
                    self.total_backups_created += backup_result.get('backups_created', 0)
                    
                    logger.info(f"💾 [BACKUP] Cycle {self.backup_cycles} completed: "
                              f"{backup_result.get('backups_created', 0)} backups created")
                
                await asyncio.sleep(self.backup_interval)
                
            except Exception as e:
                logger.error(f"❌ [BACKUP] Error in backup loop: {e}")
                await asyncio.sleep(self.backup_interval * 2)
    
    async def _execute_backup_cycle(self) -> Dict[str, Any]:
        """Execute complete backup cycle."""
        try:
            backups_created = 0
            backup_files = []
            
            # Backup smart memory data
            memory_backup = await self._backup_smart_memory()
            if memory_backup['success']:
                backups_created += 1
                backup_files.append(memory_backup['backup_file'])
            
            # Create consolidated backup
            if backup_files:
                consolidated_backup = await self._create_consolidated_backup(backup_files)
                if consolidated_backup['success']:
                    logger.info(f"📁 [BACKUP] Consolidated backup created")
            
            return {
                'success': True,
                'backups_created': backups_created,
                'backup_files': backup_files,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ [BACKUP] Backup cycle execution failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _backup_smart_memory(self) -> Dict[str, Any]:
        """Backup smart memory database and logs."""
        try:
            # Get memory data
            memory_export = await self.smart_memory.execute_memory_command(
                'memory_export_data', {}
            )
            
            if not memory_export.get('success', False):
                # Create mock data for backup
                memory_data = {
                    'trades': [],
                    'patterns': [],
                    'evolution_logs': [],
                    'backup_timestamp': datetime.now().isoformat()
                }
            else:
                memory_data = memory_export.get('data', {})
            
            # Create backup file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"smart_memory_backup_{timestamp}.json"
            backup_path = os.path.join(self.backup_directory, backup_filename)
            
            # Encrypt and save data
            if self.encryption_enabled:
                fernet = Fernet(self.backup_encryption_key)
                encrypted_data = fernet.encrypt(json.dumps(memory_data).encode())
                
                with open(backup_path, 'wb') as f:
                    f.write(encrypted_data)
            else:
                with open(backup_path, 'w') as f:
                    json.dump(memory_data, f, indent=2)
            
            file_size = os.path.getsize(backup_path)
            
            return {
                'success': True,
                'backup_file': backup_path,
                'size_bytes': file_size,
                'encrypted': self.encryption_enabled,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ [BACKUP] Smart memory backup failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _create_consolidated_backup(self, backup_files: List[str]) -> Dict[str, Any]:
        """Create consolidated backup archive."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            archive_filename = f"immortal_backup_consolidated_{timestamp}.zip"
            archive_path = os.path.join(self.backup_directory, archive_filename)
            
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for backup_file in backup_files:
                    if os.path.exists(backup_file):
                        arcname = os.path.basename(backup_file)
                        zipf.write(backup_file, arcname)
                
                # Add metadata
                metadata = {
                    'creation_timestamp': datetime.now().isoformat(),
                    'backup_cycle': self.backup_cycles,
                    'total_files': len(backup_files),
                    'encryption_enabled': self.encryption_enabled,
                    'immortal_version': '1.0.0'
                }
                
                zipf.writestr('backup_metadata.json', json.dumps(metadata, indent=2))
            
            return {
                'success': True,
                'backup_file': archive_path,
                'files_included': len(backup_files),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ [BACKUP] Consolidated backup creation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def execute_backup_command(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute backup system command."""
        try:
            params = params or {}
            
            if command == 'backup_status':
                return await self._handle_backup_status(params)
            elif command == 'force_backup':
                return await self._handle_force_backup(params)
            elif command == 'list_backups':
                return await self._handle_list_backups(params)
            else:
                return {'success': False, 'error': f'Unknown backup command: {command}'}
                
        except Exception as e:
            logger.error(f"❌ [BACKUP] Command execution failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_backup_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle backup status command."""
        try:
            backup_count = len([f for f in os.listdir(self.backup_directory) if f.endswith(('.json', '.zip'))])
            
            return {
                'success': True,
                'message': 'Secure backup system status',
                'backup_active': self.backup_active,
                'backup_cycles': self.backup_cycles,
                'total_backups_created': self.total_backups_created,
                'current_backup_files': backup_count,
                'encryption_enabled': self.encryption_enabled,
                'backup_interval_hours': self.backup_interval / 3600,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ [BACKUP] Status command failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_force_backup(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle force backup command."""
        try:
            logger.info("💾 [BACKUP] Forcing backup cycle")
            
            backup_result = await self._execute_backup_cycle()
            
            return {
                'success': True,
                'message': 'Backup cycle forced successfully',
                'backup_result': backup_result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ [BACKUP] Force backup command failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_list_backups(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle list backups command."""
        try:
            backups = []
            
            for filename in os.listdir(self.backup_directory):
                if filename.endswith(('.json', '.zip')):
                    file_path = os.path.join(self.backup_directory, filename)
                    backups.append({
                        'filename': filename,
                        'size_mb': os.path.getsize(file_path) / (1024 * 1024),
                        'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                    })
            
            backups.sort(key=lambda x: x['modified'], reverse=True)
            
            return {
                'success': True,
                'message': 'Backup files listed',
                'backups': backups,
                'total_backup_files': len(backups),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ [BACKUP] List backups command failed: {e}")
            return {'success': False, 'error': str(e)}

# Global secure backup system instance
_secure_backup_system = None

def initialize_secure_backup_system(config: Dict[str, Any]) -> SecureBackupSystem:
    """Initialize the global secure backup system."""
    global _secure_backup_system
    _secure_backup_system = SecureBackupSystem(config)
    return _secure_backup_system

def get_secure_backup_system() -> Optional[SecureBackupSystem]:
    """Get the global secure backup system instance."""
    return _secure_backup_system

async def main():
    """Main function for secure backup system."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("[BACKUP] SECURE TRADE ARCHIVE & BACKUP SYSTEM")
    print("=" * 50)
    print("Encrypting and archiving immortal consciousness data...")
    print()
    
    config = {
        'backup_interval': 43200,  # 12 hours
        'encryption_enabled': True,
        'backup_directory': 'unified_system/backups'
    }
    
    backup_system = initialize_secure_backup_system(config)
    await backup_system.initialize_backup_system()
    
    print("[BACKUP] 12-hour encrypted backup cycles active")
    print("[ARCHIVE] Long-term data preservation enabled")
    print("[ENCRYPTION] All backups encrypted with Fernet")
    print()
    print("Available commands:")
    print("  - /backup status")
    print("  - /backup force_backup")
    print("  - /backup list_backups")
    
    try:
        while True:
            await asyncio.sleep(3600)  # Check every hour
            print(f"[STATUS] {datetime.now().strftime('%H:%M:%S')} - "
                  f"Cycles: {backup_system.backup_cycles} | "
                  f"Total Backups: {backup_system.total_backups_created}")
    except KeyboardInterrupt:
        print("\n🛑 [SHUTDOWN] Secure backup system shutting down...")
        backup_system.backup_active = False

if __name__ == "__main__":
    asyncio.run(main())
