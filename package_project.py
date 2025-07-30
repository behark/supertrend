#!/usr/bin/env python3
"""
Package Crypto Alert Bot for Delivery

This script prepares the project for delivery by:
1. Creating a clean project directory structure
2. Including all necessary files
3. Generating a final report on project structure
"""
import os
import sys
import shutil
import datetime
import zipfile
import json
from pathlib import Path

class ProjectPackager:
    def __init__(self):
        self.project_dir = os.getcwd()
        self.output_dir = os.path.join(self.project_dir, "delivery")
        self.zip_name = f"crypto-alert-bot-{datetime.datetime.now().strftime('%Y%m%d')}.zip"
        self.zip_path = os.path.join(self.project_dir, self.zip_name)
        
        # Core files that must be included
        self.core_files = [
            "bot.py", "indicators.py", "risk_manager.py", "telegram_client.py",
            "chart_generator.py", "config.py", "requirements.txt", ".env.example",
            "README.md"
        ]
        
        # Advanced feature files
        self.advanced_files = [
            "backtester.py", "ml_predictor.py", "trader.py", "multi_timeframe.py",
            "portfolio_manager.py", "telegram_commands.py", "dashboard.py"
        ]
        
        # Documentation and deployment files
        self.doc_files = [
            "VERIFICATION.md", "TROUBLESHOOTING.md", "FINAL_CHECKLIST.md",
            "crypto-bot.service", "Dockerfile"
        ]
        
        # Test files
        self.test_files = [
            "test_features.py", "test_telegram_only.py", "static_verify.py"
        ]
        
        # Directories to create
        self.directories = [
            "data", "models", "logs", "charts"
        ]
        
        self.stats = {
            "core_files_found": 0,
            "advanced_files_found": 0,
            "doc_files_found": 0,
            "test_files_found": 0,
            "extra_files_found": 0,
            "directories_created": 0
        }

    def clean_output_dir(self):
        """Create or clean the output directory"""
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        os.makedirs(self.output_dir)
        print(f"✅ Created clean output directory: {self.output_dir}")
        
        # Create necessary subdirectories
        for dir_name in self.directories:
            os.makedirs(os.path.join(self.output_dir, dir_name), exist_ok=True)
            self.stats["directories_created"] += 1
        print(f"✅ Created {self.stats['directories_created']} subdirectories")

    def copy_project_files(self):
        """Copy all project files to the output directory"""
        all_files = self.core_files + self.advanced_files + self.doc_files + self.test_files
        
        print("\nCopying project files...")
        
        # Copy core files
        print("\nCore files:")
        for file_name in self.core_files:
            src = os.path.join(self.project_dir, file_name)
            dst = os.path.join(self.output_dir, file_name)
            if os.path.exists(src):
                shutil.copy2(src, dst)
                print(f"  ✅ {file_name}")
                self.stats["core_files_found"] += 1
            else:
                print(f"  ❌ {file_name} (not found)")
        
        # Copy advanced feature files
        print("\nAdvanced feature files:")
        for file_name in self.advanced_files:
            src = os.path.join(self.project_dir, file_name)
            dst = os.path.join(self.output_dir, file_name)
            if os.path.exists(src):
                shutil.copy2(src, dst)
                print(f"  ✅ {file_name}")
                self.stats["advanced_files_found"] += 1
            else:
                print(f"  ❌ {file_name} (not found)")
        
        # Copy documentation files
        print("\nDocumentation and deployment files:")
        for file_name in self.doc_files:
            src = os.path.join(self.project_dir, file_name)
            dst = os.path.join(self.output_dir, file_name)
            if os.path.exists(src):
                shutil.copy2(src, dst)
                print(f"  ✅ {file_name}")
                self.stats["doc_files_found"] += 1
            else:
                print(f"  ❌ {file_name} (not found)")
        
        # Copy test files
        print("\nTest files:")
        for file_name in self.test_files:
            src = os.path.join(self.project_dir, file_name)
            dst = os.path.join(self.output_dir, file_name)
            if os.path.exists(src):
                shutil.copy2(src, dst)
                print(f"  ✅ {file_name}")
                self.stats["test_files_found"] += 1
            else:
                print(f"  ❌ {file_name} (not found)")
        
        # Find and copy any additional Python files not explicitly listed
        print("\nChecking for additional project files...")
        for file_name in os.listdir(self.project_dir):
            if file_name.endswith('.py') and file_name not in all_files:
                src = os.path.join(self.project_dir, file_name)
                dst = os.path.join(self.output_dir, file_name)
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                    print(f"  ✅ {file_name} (additional file)")
                    self.stats["extra_files_found"] += 1
    
    def create_zip(self):
        """Create a ZIP archive of the project"""
        print("\nCreating ZIP archive...")
        with zipfile.ZipFile(self.zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(self.output_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(
                        file_path, 
                        os.path.relpath(file_path, self.output_dir)
                    )
        
        print(f"✅ Project packaged as: {self.zip_name}")
    
    def create_project_summary(self):
        """Generate a project structure and statistics summary"""
        summary_path = os.path.join(self.output_dir, "PROJECT_SUMMARY.md")
        
        with open(summary_path, 'w') as f:
            f.write("# Crypto Alert Bot - Project Structure Summary\n\n")
            f.write(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # File statistics
            f.write("## Project Statistics\n\n")
            f.write(f"- Core Files: {self.stats['core_files_found']}/{len(self.core_files)}\n")
            f.write(f"- Advanced Feature Files: {self.stats['advanced_files_found']}/{len(self.advanced_files)}\n")
            f.write(f"- Documentation Files: {self.stats['doc_files_found']}/{len(self.doc_files)}\n")
            f.write(f"- Test Files: {self.stats['test_files_found']}/{len(self.test_files)}\n")
            f.write(f"- Additional Files: {self.stats['extra_files_found']}\n")
            f.write(f"- Directories: {self.stats['directories_created']}\n\n")
            
            # Project structure
            f.write("## Project Structure\n\n")
            f.write("```\n")
            
            for root, dirs, files in os.walk(self.output_dir):
                level = root.replace(self.output_dir, '').count(os.sep)
                indent = ' ' * 2 * level
                f.write(f"{indent}{os.path.basename(root)}/\n")
                for file in files:
                    sub_indent = ' ' * 2 * (level + 1)
                    f.write(f"{sub_indent}{file}\n")
            
            f.write("```\n\n")
            
            # Deployment options
            f.write("## Deployment Options\n\n")
            f.write("1. **Standard Python**: Install dependencies from requirements.txt\n")
            f.write("2. **Docker**: Use the included Dockerfile\n")
            f.write("3. **Systemd Service**: Use the included crypto-bot.service file\n\n")
            
            # Python compatibility
            f.write("## Python Compatibility\n\n")
            f.write("- Recommended: Python 3.10 or 3.11\n")
            f.write("- Note: Python 3.13 has compatibility issues with python-telegram-bot package\n\n")
            
            f.write("## Next Steps\n\n")
            f.write("1. Review FINAL_CHECKLIST.md for project status\n")
            f.write("2. Follow setup instructions in README.md\n")
            f.write("3. Verify functionality using VERIFICATION.md\n")
        
        print(f"✅ Created project summary: PROJECT_SUMMARY.md")
        
        # Also create a JSON file with project statistics
        stats_path = os.path.join(self.output_dir, "project_stats.json")
        with open(stats_path, 'w') as f:
            json.dump(self.stats, f, indent=2)
    
    def run(self):
        """Run the full packaging process"""
        print("="*60)
        print("PACKAGING CRYPTO ALERT BOT FOR DELIVERY")
        print("="*60)
        
        self.clean_output_dir()
        self.copy_project_files()
        self.create_project_summary()
        self.create_zip()
        
        print("\n" + "="*60)
        print("PACKAGING COMPLETE")
        print("="*60)
        print(f"Project packaged as: {self.zip_name}")
        print(f"Delivery directory: {self.output_dir}")
        print("\nStatistics:")
        print(f"- Core Files: {self.stats['core_files_found']}/{len(self.core_files)}")
        print(f"- Advanced Feature Files: {self.stats['advanced_files_found']}/{len(self.advanced_files)}")
        print(f"- Documentation Files: {self.stats['doc_files_found']}/{len(self.doc_files)}")
        print(f"- Test Files: {self.stats['test_files_found']}/{len(self.test_files)}")
        print(f"- Additional Files: {self.stats['extra_files_found']}")
        print(f"- Directories: {self.stats['directories_created']}")
        
        return self.stats

if __name__ == "__main__":
    packager = ProjectPackager()
    packager.run()
