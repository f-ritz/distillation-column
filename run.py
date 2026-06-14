#!/usr/bin/env python3
"""
Launcher for FUGK Distillation Calculator
Run this file to start the CustomTkinter GUI.
"""

import subprocess
import sys
import os

def main():
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(script_dir, "gui", "app.py")
    
    print("Starting FUGK Distillation Calculator...")
    print("The application will open in a desktop window.\n")
    
    try:
        subprocess.run([sys.executable, app_path])
    except KeyboardInterrupt:
        print("\nShutting down...")

if __name__ == "__main__":
    main()