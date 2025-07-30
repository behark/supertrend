#!/usr/bin/env python3
"""
Test runner for SuperTrend trading bot
"""
import sys
import os
import subprocess
import argparse
from pathlib import Path

def run_tests(test_type='all', verbose=False, coverage=False):
    """Run tests with specified options"""
    
    # Get project root
    project_root = Path(__file__).parent.parent
    
    # Build pytest command - use virtual environment if available
    venv_python = project_root / 'venv' / 'bin' / 'python'
    if venv_python.exists():
        cmd = [str(venv_python), '-m', 'pytest']
    else:
        cmd = ['python', '-m', 'pytest']
    
    if verbose:
        cmd.append('-v')
    
    if coverage:
        cmd.extend(['--cov=src', '--cov-report=html', '--cov-report=term'])
    
    # Add test paths based on type
    if test_type == 'unit':
        cmd.append('tests/unit/')
    elif test_type == 'integration':
        cmd.append('tests/integration/')
    elif test_type == 'e2e':
        cmd.append('tests/e2e/')
    elif test_type == 'comprehensive':
        cmd.append('tests/test_comprehensive_suite.py')
    else:  # all
        cmd.append('tests/')
    
    # Add project root to Python path
    env = os.environ.copy()
    env['PYTHONPATH'] = f"{project_root}:{project_root}/src:{env.get('PYTHONPATH', '')}"
    
    print(f"Running {test_type} tests...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, env=env, cwd=project_root)
        return result.returncode
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1

def main():
    """Main test runner function"""
    parser = argparse.ArgumentParser(description='Run SuperTrend tests')
    parser.add_argument(
        '--type', 
        choices=['all', 'unit', 'integration', 'e2e', 'comprehensive'],
        default='all',
        help='Type of tests to run'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    parser.add_argument(
        '--coverage', '-c',
        action='store_true',
        help='Generate coverage report'
    )
    
    args = parser.parse_args()
    
    # Check if pytest is installed
    try:
        import pytest
    except ImportError:
        print("pytest not found. Please install it in your virtual environment:")
        print("source venv/bin/activate && pip install pytest")
        return 1
    
    # Check if responses is installed (for integration tests)
    try:
        import responses
    except ImportError:
        print("responses not found. Please install it in your virtual environment:")
        print("source venv/bin/activate && pip install responses")
        return 1
    
    # Run tests
    exit_code = run_tests(args.type, args.verbose, args.coverage)
    
    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")
    
    sys.exit(exit_code)

if __name__ == '__main__':
    main() 