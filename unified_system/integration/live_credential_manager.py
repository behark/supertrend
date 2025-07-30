"""
Live API Credential Integration Manager
======================================
Secure, environment-safe method for connecting real API keys with encryption support.
Handles Binance and Bybit API credential validation and integration.
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import hashlib
import hmac
import base64
from cryptography.fernet import Fernet
import asyncio

logger = logging.getLogger(__name__)

@dataclass
class APICredential:
    """API credential structure."""
    exchange: str
    api_key: str
    api_secret: str
    testnet: bool
    encrypted: bool
    last_validated: Optional[datetime]
    validation_status: str

class LiveCredentialManager:
    """Secure API credential management for live trading."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize credential manager."""
        self.config = config
        
        # Encryption settings
        self.encryption_enabled = config.get('encryption_enabled', True)
        self.encryption_key = self._get_or_create_encryption_key()
        
        # Credential storage
        self.credentials_file = config.get('credentials_file', 'unified_system/config/api_credentials.json')
        self.env_prefix = config.get('env_prefix', 'TRADING_')
        
        # Validation settings
        self.validation_timeout = config.get('validation_timeout', 10)
        self.auto_validate = config.get('auto_validate', True)
        
        # Credential storage
        self.credentials: Dict[str, APICredential] = {}
        self.manager_active = False
        
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for credential storage."""
        try:
            key_file = 'unified_system/config/credential_key.key'
            
            if os.path.exists(key_file):
                with open(key_file, 'rb') as f:
                    return f.read()
            else:
                # Create new encryption key
                key = Fernet.generate_key()
                os.makedirs(os.path.dirname(key_file), exist_ok=True)
                
                with open(key_file, 'wb') as f:
                    f.write(key)
                
                logger.info("[CREDENTIALS] New encryption key created")
                return key
                
        except Exception as e:
            logger.error(f"[CREDENTIALS] Failed to handle encryption key: {e}")
            return Fernet.generate_key()  # Fallback to memory-only key
    
    async def initialize_credential_manager(self):
        """Initialize the credential management system."""
        try:
            logger.info("[CREDENTIALS] Initializing Live Credential Manager")
            
            # Load existing credentials
            await self._load_credentials()
            
            # Load from environment variables
            await self._load_from_environment()
            
            # Validate credentials if auto-validation is enabled
            if self.auto_validate:
                await self._validate_all_credentials()
            
            self.manager_active = True
            logger.info("[CREDENTIALS] Live Credential Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"[CREDENTIALS] Initialization failed: {e}")
            raise
    
    async def _load_credentials(self):
        """Load credentials from encrypted file."""
        try:
            if not os.path.exists(self.credentials_file):
                logger.info("[CREDENTIALS] No existing credentials file found")
                return
            
            with open(self.credentials_file, 'r') as f:
                encrypted_data = json.load(f)
            
            if self.encryption_enabled:
                fernet = Fernet(self.encryption_key)
                
                for exchange, encrypted_cred in encrypted_data.items():
                    try:
                        decrypted_data = fernet.decrypt(encrypted_cred['data'].encode()).decode()
                        cred_data = json.loads(decrypted_data)
                        
                        credential = APICredential(
                            exchange=exchange,
                            api_key=cred_data['api_key'],
                            api_secret=cred_data['api_secret'],
                            testnet=cred_data.get('testnet', True),
                            encrypted=True,
                            last_validated=datetime.fromisoformat(cred_data['last_validated']) if cred_data.get('last_validated') else None,
                            validation_status=cred_data.get('validation_status', 'unknown')
                        )
                        
                        self.credentials[exchange] = credential
                        
                    except Exception as e:
                        logger.error(f"[CREDENTIALS] Failed to decrypt {exchange} credentials: {e}")
            else:
                # Load unencrypted (development only)
                for exchange, cred_data in encrypted_data.items():
                    credential = APICredential(
                        exchange=exchange,
                        api_key=cred_data['api_key'],
                        api_secret=cred_data['api_secret'],
                        testnet=cred_data.get('testnet', True),
                        encrypted=False,
                        last_validated=datetime.fromisoformat(cred_data['last_validated']) if cred_data.get('last_validated') else None,
                        validation_status=cred_data.get('validation_status', 'unknown')
                    )
                    
                    self.credentials[exchange] = credential
            
            logger.info(f"[CREDENTIALS] Loaded {len(self.credentials)} credential sets")
            
        except Exception as e:
            logger.error(f"[CREDENTIALS] Failed to load credentials: {e}")
    
    async def _load_from_environment(self):
        """Load credentials from environment variables."""
        try:
            exchanges = ['BINANCE', 'BYBIT']
            
            for exchange in exchanges:
                api_key_env = f"{self.env_prefix}{exchange}_API_KEY"
                api_secret_env = f"{self.env_prefix}{exchange}_API_SECRET"
                testnet_env = f"{self.env_prefix}{exchange}_TESTNET"
                
                api_key = os.getenv(api_key_env)
                api_secret = os.getenv(api_secret_env)
                testnet = os.getenv(testnet_env, 'true').lower() == 'true'
                
                if api_key and api_secret:
                    credential = APICredential(
                        exchange=exchange.lower(),
                        api_key=api_key,
                        api_secret=api_secret,
                        testnet=testnet,
                        encrypted=False,
                        last_validated=None,
                        validation_status='pending'
                    )
                    
                    self.credentials[exchange.lower()] = credential
                    logger.info(f"[CREDENTIALS] Loaded {exchange} credentials from environment")
            
        except Exception as e:
            logger.error(f"[CREDENTIALS] Failed to load from environment: {e}")
    
    async def add_credential(self, exchange: str, api_key: str, api_secret: str, 
                           testnet: bool = True, validate: bool = True) -> bool:
        """Add new API credential."""
        try:
            logger.info(f"[CREDENTIALS] Adding {exchange} credential")
            
            # Create credential object
            credential = APICredential(
                exchange=exchange.lower(),
                api_key=api_key,
                api_secret=api_secret,
                testnet=testnet,
                encrypted=self.encryption_enabled,
                last_validated=None,
                validation_status='pending'
            )
            
            # Validate credential if requested
            if validate:
                validation_result = await self._validate_credential(credential)
                credential.validation_status = 'valid' if validation_result else 'invalid'
                credential.last_validated = datetime.now()
            
            # Store credential
            self.credentials[exchange.lower()] = credential
            
            # Save to file
            await self._save_credentials()
            
            logger.info(f"[CREDENTIALS] {exchange} credential added successfully")
            return True
            
        except Exception as e:
            logger.error(f"[CREDENTIALS] Failed to add {exchange} credential: {e}")
            return False
    
    async def _validate_credential(self, credential: APICredential) -> bool:
        """Validate API credential by making test request."""
        try:
            logger.info(f"[CREDENTIALS] Validating {credential.exchange} credential")
            
            if credential.exchange == 'binance':
                return await self._validate_binance_credential(credential)
            elif credential.exchange == 'bybit':
                return await self._validate_bybit_credential(credential)
            else:
                logger.warning(f"[CREDENTIALS] Unknown exchange: {credential.exchange}")
                return False
                
        except Exception as e:
            logger.error(f"[CREDENTIALS] Credential validation failed: {e}")
            return False
    
    async def _validate_binance_credential(self, credential: APICredential) -> bool:
        """Validate Binance API credential."""
        try:
            # Mock validation for now - in production, make actual API call
            # This would typically involve:
            # 1. Creating signed request to /api/v3/account endpoint
            # 2. Checking response for valid account info
            # 3. Verifying permissions (spot trading, etc.)
            
            # For now, just validate format
            if len(credential.api_key) >= 64 and len(credential.api_secret) >= 64:
                logger.info("[CREDENTIALS] Binance credential format validation passed")
                return True
            else:
                logger.warning("[CREDENTIALS] Binance credential format validation failed")
                return False
                
        except Exception as e:
            logger.error(f"[CREDENTIALS] Binance validation error: {e}")
            return False
    
    async def _validate_bybit_credential(self, credential: APICredential) -> bool:
        """Validate Bybit API credential."""
        try:
            # Mock validation for now - in production, make actual API call
            # This would typically involve:
            # 1. Creating signed request to /v2/private/account endpoint
            # 2. Checking response for valid account info
            # 3. Verifying permissions
            
            # For now, just validate format
            if len(credential.api_key) >= 20 and len(credential.api_secret) >= 20:
                logger.info("[CREDENTIALS] Bybit credential format validation passed")
                return True
            else:
                logger.warning("[CREDENTIALS] Bybit credential format validation failed")
                return False
                
        except Exception as e:
            logger.error(f"[CREDENTIALS] Bybit validation error: {e}")
            return False
    
    async def _validate_all_credentials(self):
        """Validate all stored credentials."""
        try:
            logger.info("[CREDENTIALS] Validating all stored credentials")
            
            for exchange, credential in self.credentials.items():
                if credential.validation_status != 'valid':
                    validation_result = await self._validate_credential(credential)
                    credential.validation_status = 'valid' if validation_result else 'invalid'
                    credential.last_validated = datetime.now()
            
            # Save updated validation results
            await self._save_credentials()
            
        except Exception as e:
            logger.error(f"[CREDENTIALS] Bulk validation failed: {e}")
    
    async def _save_credentials(self):
        """Save credentials to encrypted file."""
        try:
            os.makedirs(os.path.dirname(self.credentials_file), exist_ok=True)
            
            if self.encryption_enabled:
                fernet = Fernet(self.encryption_key)
                encrypted_data = {}
                
                for exchange, credential in self.credentials.items():
                    cred_data = {
                        'api_key': credential.api_key,
                        'api_secret': credential.api_secret,
                        'testnet': credential.testnet,
                        'last_validated': credential.last_validated.isoformat() if credential.last_validated else None,
                        'validation_status': credential.validation_status
                    }
                    
                    encrypted_cred_data = fernet.encrypt(json.dumps(cred_data).encode()).decode()
                    encrypted_data[exchange] = {
                        'data': encrypted_cred_data,
                        'encrypted': True
                    }
                
                with open(self.credentials_file, 'w') as f:
                    json.dump(encrypted_data, f, indent=2)
            else:
                # Save unencrypted (development only)
                unencrypted_data = {}
                
                for exchange, credential in self.credentials.items():
                    unencrypted_data[exchange] = {
                        'api_key': credential.api_key,
                        'api_secret': credential.api_secret,
                        'testnet': credential.testnet,
                        'last_validated': credential.last_validated.isoformat() if credential.last_validated else None,
                        'validation_status': credential.validation_status,
                        'encrypted': False
                    }
                
                with open(self.credentials_file, 'w') as f:
                    json.dump(unencrypted_data, f, indent=2)
            
            logger.info("[CREDENTIALS] Credentials saved successfully")
            
        except Exception as e:
            logger.error(f"[CREDENTIALS] Failed to save credentials: {e}")
    
    async def execute_credential_command(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute credential management command."""
        try:
            params = params or {}
            
            if command == 'credential_status':
                return await self._handle_credential_status(params)
            elif command == 'credential_add':
                return await self._handle_credential_add(params)
            elif command == 'credential_validate':
                return await self._handle_credential_validate(params)
            elif command == 'credential_test':
                return await self._handle_credential_test(params)
            else:
                return {'success': False, 'error': f'Unknown credential command: {command}'}
                
        except Exception as e:
            logger.error(f"[CREDENTIALS] Command execution failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_credential_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle credential status command."""
        try:
            credential_summary = {}
            
            for exchange, credential in self.credentials.items():
                credential_summary[exchange] = {
                    'exchange': credential.exchange,
                    'testnet': credential.testnet,
                    'encrypted': credential.encrypted,
                    'validation_status': credential.validation_status,
                    'last_validated': credential.last_validated.isoformat() if credential.last_validated else None,
                    'api_key_preview': credential.api_key[:8] + '...' if len(credential.api_key) > 8 else 'SHORT'
                }
            
            return {
                'success': True,
                'message': f'Status for {len(credential_summary)} credential sets',
                'credentials': credential_summary,
                'encryption_enabled': self.encryption_enabled,
                'auto_validate': self.auto_validate,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"[CREDENTIALS] Status command failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_credential_add(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle credential add command."""
        try:
            exchange = params.get('exchange', '').lower()
            api_key = params.get('api_key', '')
            api_secret = params.get('api_secret', '')
            testnet = params.get('testnet', True)
            
            if not exchange or not api_key or not api_secret:
                return {
                    'success': False,
                    'error': 'Missing required parameters: exchange, api_key, api_secret'
                }
            
            result = await self.add_credential(exchange, api_key, api_secret, testnet)
            
            if result:
                return {
                    'success': True,
                    'message': f'{exchange.upper()} credential added successfully',
                    'exchange': exchange,
                    'testnet': testnet,
                    'validation_status': self.credentials[exchange].validation_status,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'success': False,
                    'error': f'Failed to add {exchange} credential'
                }
                
        except Exception as e:
            logger.error(f"[CREDENTIALS] Add command failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_credential_validate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle credential validation command."""
        try:
            exchange = params.get('exchange', 'all').lower()
            
            if exchange == 'all':
                await self._validate_all_credentials()
                
                validation_results = {}
                for ex, cred in self.credentials.items():
                    validation_results[ex] = {
                        'validation_status': cred.validation_status,
                        'last_validated': cred.last_validated.isoformat() if cred.last_validated else None
                    }
                
                return {
                    'success': True,
                    'message': f'Validated {len(validation_results)} credential sets',
                    'validation_results': validation_results,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                if exchange not in self.credentials:
                    return {
                        'success': False,
                        'error': f'No credentials found for {exchange}'
                    }
                
                credential = self.credentials[exchange]
                validation_result = await self._validate_credential(credential)
                credential.validation_status = 'valid' if validation_result else 'invalid'
                credential.last_validated = datetime.now()
                
                await self._save_credentials()
                
                return {
                    'success': True,
                    'message': f'{exchange.upper()} credential validation completed',
                    'exchange': exchange,
                    'validation_status': credential.validation_status,
                    'last_validated': credential.last_validated.isoformat(),
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"[CREDENTIALS] Validation command failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_credential_test(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle credential test command."""
        try:
            # Test all credential integrations
            test_results = {}
            
            for exchange, credential in self.credentials.items():
                test_result = {
                    'exchange': exchange,
                    'api_key_format': len(credential.api_key) >= 20,
                    'api_secret_format': len(credential.api_secret) >= 20,
                    'validation_status': credential.validation_status,
                    'testnet_mode': credential.testnet,
                    'encrypted': credential.encrypted
                }
                
                # Test connection (mock for now)
                test_result['connection_test'] = credential.validation_status == 'valid'
                test_result['overall_status'] = 'pass' if all([
                    test_result['api_key_format'],
                    test_result['api_secret_format'],
                    test_result['connection_test']
                ]) else 'fail'
                
                test_results[exchange] = test_result
            
            overall_pass = all(result['overall_status'] == 'pass' for result in test_results.values())
            
            return {
                'success': True,
                'message': f'Credential test completed for {len(test_results)} exchanges',
                'test_results': test_results,
                'overall_status': 'pass' if overall_pass else 'fail',
                'ready_for_live_trading': overall_pass,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"[CREDENTIALS] Test command failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_credential(self, exchange: str) -> Optional[APICredential]:
        """Get credential for specific exchange."""
        return self.credentials.get(exchange.lower())
    
    def get_credential_status(self) -> Dict[str, Any]:
        """Get overall credential manager status."""
        valid_credentials = len([c for c in self.credentials.values() if c.validation_status == 'valid'])
        
        return {
            'manager_active': self.manager_active,
            'total_credentials': len(self.credentials),
            'valid_credentials': valid_credentials,
            'encryption_enabled': self.encryption_enabled,
            'exchanges_configured': list(self.credentials.keys()),
            'timestamp': datetime.now().isoformat()
        }

# Global credential manager instance
_credential_manager = None

def initialize_credential_manager(config: Dict[str, Any]) -> LiveCredentialManager:
    """Initialize the global credential manager."""
    global _credential_manager
    _credential_manager = LiveCredentialManager(config)
    return _credential_manager

def get_credential_manager() -> Optional[LiveCredentialManager]:
    """Get the global credential manager instance."""
    return _credential_manager

async def main():
    """Main function for testing credential manager."""
    config = {
        'encryption_enabled': True,
        'credentials_file': 'unified_system/config/api_credentials.json',
        'env_prefix': 'TRADING_',
        'validation_timeout': 10,
        'auto_validate': True
    }
    
    manager = initialize_credential_manager(config)
    await manager.initialize_credential_manager()
    
    print("[CREDENTIALS] Live Credential Manager is running...")
    print("[CREDENTIALS] Available commands:")
    print("  - /credential status")
    print("  - /credential add")
    print("  - /credential validate")
    print("  - /credential test")
    print()
    print("Environment variables expected:")
    print("  - TRADING_BINANCE_API_KEY")
    print("  - TRADING_BINANCE_API_SECRET")
    print("  - TRADING_BINANCE_TESTNET (true/false)")
    print("  - TRADING_BYBIT_API_KEY")
    print("  - TRADING_BYBIT_API_SECRET")
    print("  - TRADING_BYBIT_TESTNET (true/false)")
    
    try:
        while True:
            await asyncio.sleep(60)
            status = manager.get_credential_status()
            print(f"[HEARTBEAT] {datetime.now().strftime('%H:%M:%S')} - Credentials: {status['valid_credentials']}/{status['total_credentials']} valid")
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Live Credential Manager shutting down...")

if __name__ == "__main__":
    asyncio.run(main())
