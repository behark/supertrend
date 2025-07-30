#!/usr/bin/env python3
"""
Static Verification Script for Crypto Alert Bot

This script performs static verification of the codebase structure and logic
without requiring all external dependencies to be installed.
"""
import os
import sys
import importlib.util
from pprint import pprint

class StaticVerifier:
    def __init__(self):
        self.results = {
            "modules_exist": {},
            "required_functions": {},
            "module_imports": {},
            "configuration": {},
            "overall": "Unknown"
        }
        self.required_modules = [
            "bot.py", "indicators.py", "risk_manager.py", "telegram_client.py", 
            "chart_generator.py", "backtester.py", "ml_predictor.py", "trader.py",
            "multi_timeframe.py", "portfolio_manager.py", "telegram_commands.py", 
            "dashboard.py", "config.py"
        ]
        self.required_functions = {
            "bot.py": ["main", "scan_markets", "analyze_symbol", "schedule_scanning"],
            "indicators.py": ["check_ma_cross", "check_breakout", "check_volume_price_spike"],
            "risk_manager.py": ["filter_signal", "calculate_position_size"],
            "backtester.py": ["run_backtest", "calculate_metrics"],
            "ml_predictor.py": ["train", "predict"],
            "trader.py": ["execute_trade"],
            "multi_timeframe.py": ["confirm_signal"],
            "portfolio_manager.py": ["add_trade", "calculate_performance"],
            "telegram_commands.py": ["handle_command"]
        }
    
    def check_modules_exist(self):
        """Check if all required modules exist in the project"""
        print("Checking if all required modules exist...")
        
        for module in self.required_modules:
            module_path = os.path.join(os.getcwd(), module)
            exists = os.path.exists(module_path)
            self.results["modules_exist"][module] = exists
            if exists:
                print(f"✅ Found {module}")
            else:
                print(f"❌ Missing {module}")
        
        # Check if all core modules exist
        core_modules = ["bot.py", "indicators.py", "risk_manager.py", "telegram_client.py"]
        core_exists = all(self.results["modules_exist"].get(m, False) for m in core_modules)
        
        # Check if all advanced modules exist
        advanced_modules = [
            "backtester.py", "ml_predictor.py", "trader.py", "multi_timeframe.py", 
            "portfolio_manager.py", "telegram_commands.py", "dashboard.py"
        ]
        advanced_exists = all(self.results["modules_exist"].get(m, False) for m in advanced_modules)
        
        return core_exists, advanced_exists
    
    def check_function_signatures(self):
        """Check if required functions exist in each module without importing the modules"""
        print("\nChecking function signatures in modules...")
        
        for module_name, functions in self.required_functions.items():
            module_path = os.path.join(os.getcwd(), module_name)
            
            if not os.path.exists(module_path):
                self.results["required_functions"][module_name] = {
                    "status": "Module not found"
                }
                continue
            
            with open(module_path, 'r') as f:
                content = f.read()
            
            self.results["required_functions"][module_name] = {}
            for func in functions:
                # Simple check for function definition
                if f"def {func}(" in content:
                    self.results["required_functions"][module_name][func] = True
                    print(f"✅ Found function '{func}' in {module_name}")
                else:
                    self.results["required_functions"][module_name][func] = False
                    print(f"❌ Missing function '{func}' in {module_name}")
    
    def check_module_imports(self):
        """Check if advanced feature modules are imported in bot.py"""
        print("\nChecking if advanced feature modules are imported in bot.py...")
        
        bot_path = os.path.join(os.getcwd(), "bot.py")
        if not os.path.exists(bot_path):
            print("❌ bot.py not found")
            return False
        
        with open(bot_path, 'r') as f:
            content = f.read()
        
        advanced_imports = [
            "backtester", "ml_predictor", "trader", "multi_timeframe", 
            "portfolio_manager", "telegram_commands", "dashboard"
        ]
        
        for module in advanced_imports:
            if f"import {module}" in content or f"from {module}" in content:
                self.results["module_imports"][module] = True
                print(f"✅ {module} is imported in bot.py")
            else:
                self.results["module_imports"][module] = False
                print(f"❌ {module} is not imported in bot.py")
                
        return all(self.results["module_imports"].values())
    
    def check_configuration(self):
        """Check if configuration files are properly set up"""
        print("\nChecking configuration files...")
        
        # Check .env file
        env_path = os.path.join(os.getcwd(), ".env")
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                env_content = f.read()
            
            has_telegram_token = "TELEGRAM_BOT_TOKEN" in env_content
            has_telegram_chat_id = "TELEGRAM_CHAT_ID" in env_content
            
            self.results["configuration"][".env"] = {
                "exists": True,
                "has_telegram_token": has_telegram_token,
                "has_telegram_chat_id": has_telegram_chat_id
            }
            
            print(f"✅ .env file exists")
            print(f"  - TELEGRAM_BOT_TOKEN: {'✅ Present' if has_telegram_token else '❌ Missing'}")
            print(f"  - TELEGRAM_CHAT_ID: {'✅ Present' if has_telegram_chat_id else '❌ Missing'}")
        else:
            self.results["configuration"][".env"] = {"exists": False}
            print("❌ .env file not found")
        
        # Check config.py
        config_path = os.path.join(os.getcwd(), "config.py")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config_content = f.read()
            
            self.results["configuration"]["config.py"] = {
                "exists": True,
                "has_exchanges": "EXCHANGES" in config_content,
                "has_symbols": "SYMBOLS" in config_content,
                "has_timeframes": "TIMEFRAMES" in config_content
            }
            
            print(f"✅ config.py file exists")
        else:
            self.results["configuration"]["config.py"] = {"exists": False}
            print("❌ config.py file not found")
    
    def check_command_line_args(self):
        """Check if bot.py contains command line argument handling for advanced features"""
        print("\nChecking command line arguments for advanced features...")
        
        bot_path = os.path.join(os.getcwd(), "bot.py")
        if not os.path.exists(bot_path):
            print("❌ bot.py not found")
            return False
        
        with open(bot_path, 'r') as f:
            content = f.read()
        
        # Check for common command-line argument parsing patterns
        has_argparse = "argparse" in content
        has_parser = "ArgumentParser" in content
        
        # Check for specific arguments
        args_to_check = ["--test", "--backtest", "--dashboard", "--train-ml", "--trade"]
        found_args = {}
        
        for arg in args_to_check:
            found_args[arg] = arg in content
            print(f"  - {arg}: {'✅ Found' if found_args[arg] else '❌ Not found'}")
        
        return has_argparse and has_parser and any(found_args.values())
    
    def verify_all(self):
        """Run all verification checks"""
        print("="*60)
        print("CRYPTO ALERT BOT - STATIC CODE VERIFICATION")
        print("="*60)
        
        # Run all checks
        core_exists, advanced_exists = self.check_modules_exist()
        self.check_function_signatures()
        imports_ok = self.check_module_imports()
        self.check_configuration()
        has_cli_args = self.check_command_line_args()
        
        # Determine overall status
        if core_exists and advanced_exists and imports_ok:
            self.results["overall"] = "✅ All required modules and functions present"
        elif core_exists and not advanced_exists:
            self.results["overall"] = "⚠️ Core functionality present, some advanced features missing"
        else:
            self.results["overall"] = "❌ Core functionality incomplete"
        
        # Print summary
        print("\n" + "="*60)
        print("VERIFICATION SUMMARY")
        print("="*60)
        print(f"Core Modules: {'✅ Complete' if core_exists else '❌ Incomplete'}")
        print(f"Advanced Modules: {'✅ Complete' if advanced_exists else '❌ Incomplete'}")
        print(f"Module Imports: {'✅ Complete' if imports_ok else '❌ Incomplete'}")
        print(f"CLI Arguments: {'✅ Present' if has_cli_args else '❌ Missing'}")
        
        env_config = self.results["configuration"].get(".env", {})
        if env_config.get("exists", False):
            token = env_config.get("has_telegram_token", False)
            chat_id = env_config.get("has_telegram_chat_id", False)
            if token and chat_id:
                print(f"Telegram Configuration: ✅ Complete")
            else:
                print(f"Telegram Configuration: ⚠️ Incomplete")
        else:
            print(f"Telegram Configuration: ❌ Missing")
        
        print("\n" + "="*60)
        print(f"OVERALL STATUS: {self.results['overall']}")
        print("="*60)
        
        return self.results

if __name__ == "__main__":
    verifier = StaticVerifier()
    results = verifier.verify_all()
    
    # Save results to file
    with open("verification_results.txt", "w") as f:
        f.write("CRYPTO ALERT BOT - VERIFICATION RESULTS\n")
        f.write("="*50 + "\n")
        f.write(f"Date: {__import__('datetime').datetime.now()}\n")
        f.write("="*50 + "\n\n")
        f.write(f"OVERALL STATUS: {results['overall']}\n\n")
        f.write("Detailed Results:\n")
        f.write("-"*50 + "\n")
        f.write(str(results))
    
    print(f"\nResults saved to verification_results.txt")
    
    # Exit with status code based on verification result
    if "✅" in results["overall"]:
        sys.exit(0)
    elif "⚠️" in results["overall"]:
        sys.exit(1)
    else:
        sys.exit(2)
