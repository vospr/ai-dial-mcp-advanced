#!/usr/bin/env python3
"""
Advanced MCP - Cross-platform Test Runner
This script sets up the environment and runs the test suite
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

# Colors for output
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
CYAN = '\033[0;36m'
NC = '\033[0m'  # No Color

# Disable colors on Windows if not supported
if platform.system() == 'Windows':
    try:
        import colorama
        colorama.init()
    except ImportError:
        GREEN = RED = YELLOW = CYAN = NC = ''


def print_colored(message, color=NC):
    """Print colored message"""
    print(f"{color}{message}{NC}")


def run_command(cmd, check=True, shell=False):
    """Run a command and return the result"""
    try:
        if isinstance(cmd, str) and not shell:
            cmd = cmd.split()
        result = subprocess.run(
            cmd,
            check=check,
            shell=shell,
            capture_output=True,
            text=True
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr
    except Exception as e:
        return False, "", str(e)


def check_service(url, method="GET", data=None, headers=None):
    """Check if a service is running"""
    try:
        import requests
        if method == "GET":
            response = requests.get(url, timeout=5)
        else:
            response = requests.post(url, json=data, headers=headers, timeout=5)
        return response.status_code in [200, 202]
    except Exception:
        return False


def main():
    script_dir = Path(__file__).parent.resolve()
    os.chdir(script_dir)
    
    print_colored("=" * 50, CYAN)
    print_colored("Advanced MCP - Test Runner", CYAN)
    print_colored("=" * 50, CYAN)
    print()
    
    # Check Python version
    if sys.version_info < (3, 11):
        print_colored("❌ Python 3.11 or higher is required", RED)
        sys.exit(1)
    
    # Check if virtual environment exists
    venv_path = script_dir / ".venv"
    if not venv_path.exists():
        print_colored("Virtual environment not found. Creating...", YELLOW)
        success, _, _ = run_command([sys.executable, "-m", "venv", ".venv"])
        if not success:
            print_colored("❌ Failed to create virtual environment", RED)
            sys.exit(1)
    
    # Activate virtual environment and get Python path
    if platform.system() == "Windows":
        python_exe = venv_path / "Scripts" / "python.exe"
        pip_exe = venv_path / "Scripts" / "pip.exe"
    else:
        python_exe = venv_path / "bin" / "python"
        pip_exe = venv_path / "bin" / "pip"
    
    # Install/upgrade dependencies
    print_colored("Installing dependencies...", CYAN)
    run_command([str(pip_exe), "install", "--quiet", "--upgrade", "pip"], check=False)
    run_command([str(pip_exe), "install", "--quiet", "-r", "requirements.txt"], check=False)
    
    # Check Docker service
    print()
    print_colored("Checking Docker User Service (port 8041)...", CYAN)
    if check_service("http://localhost:8041/health"):
        print_colored("✅ Docker User Service is running", GREEN)
    else:
        print_colored("❌ Docker User Service is NOT running", RED)
        print()
        print_colored("Starting Docker services...", YELLOW)
        run_command(["docker", "compose", "up", "-d"], check=False)
        import time
        time.sleep(5)
        
        if check_service("http://localhost:8041/health"):
            print_colored("✅ Docker User Service is now running", GREEN)
        else:
            print_colored("❌ Failed to start Docker User Service", RED)
            print_colored("Please check Docker and try: docker compose up -d", YELLOW)
            response = input("Continue anyway? (y/n): ")
            if response.lower() != 'y':
                sys.exit(1)
    
    # Check MCP Server
    print()
    print_colored("Checking MCP Server (port 8006)...", CYAN)
    mcp_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }
    mcp_data = {
        "jsonrpc": "2.0",
        "id": "health-check",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0"}
        }
    }
    
    if check_service("http://localhost:8006/mcp", method="POST", data=mcp_data, headers=mcp_headers):
        print_colored("✅ MCP Server is running", GREEN)
    else:
        print_colored("⚠️  MCP Server is NOT running", YELLOW)
        print()
        print_colored("Please start the MCP server in a separate terminal:", YELLOW)
        if platform.system() == "Windows":
            print_colored(f"  cd {script_dir}", YELLOW)
            print_colored("  .venv\\Scripts\\Activate.ps1", YELLOW)
            print_colored("  $env:DIAL_API_KEY='your_api_key'", YELLOW)
        else:
            print_colored(f"  cd {script_dir}", YELLOW)
            print_colored("  source .venv/bin/activate", YELLOW)
            print_colored("  export DIAL_API_KEY='your_api_key'", YELLOW)
        print_colored("  python mcp_server/server.py", YELLOW)
        print()
        response = input("Press Enter to continue anyway, or Ctrl+C to cancel...")
    
    # Check DIAL_API_KEY
    print()
    if not os.getenv("DIAL_API_KEY"):
        print_colored("⚠️  DIAL_API_KEY environment variable is not set", YELLOW)
        print()
        print_colored("Please set it:", YELLOW)
        if platform.system() == "Windows":
            print_colored("  $env:DIAL_API_KEY='your_dial_api_key'", YELLOW)
        else:
            print_colored("  export DIAL_API_KEY='your_dial_api_key'", YELLOW)
        print()
        response = input("Press Enter to continue anyway, or Ctrl+C to cancel...")
    else:
        api_key = os.getenv("DIAL_API_KEY")
        print_colored(f"✅ DIAL_API_KEY is set: {api_key[:10]}...", GREEN)
    
    # Run tests
    print()
    print_colored("=" * 50, CYAN)
    print_colored("Running Test Suite", CYAN)
    print_colored("=" * 50, CYAN)
    print()
    
    # Use the virtual environment's Python to run tests
    exit_code = subprocess.call([str(python_exe), "test.py"])
    
    print()
    if exit_code == 0:
        print_colored("✅ All tests completed successfully!", GREEN)
    else:
        print_colored("❌ Some tests failed", RED)
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

