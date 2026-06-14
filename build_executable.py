#!/usr/bin/env python3
"""
Build standalone executable for FUGK Distillation Calculator
Works on both Windows and macOS.

Usage:
    python build_executable.py
"""

import PyInstaller.__main__
import os
import sys
import platform

def build():
    print(f"Building executable for {platform.system()}...")
    
    # Path to the CustomTkinter app
    app_path = os.path.join("gui", "app.py")
    
    # Common PyInstaller arguments
    args = [
        app_path,
        "--onefile",
        "--windowed",
        "--name", "FUGK_Distillation_Calculator",
        "--add-data", f"{os.path.join('core', 'fug.py')}{os.pathsep}core",
        "--hidden-import", "customtkinter",
        "--hidden-import", "pandas",
        "--hidden-import", "numpy",
    ]
    
    # Platform-specific tweaks
    if platform.system() == "Darwin":  # macOS
        args.extend([
            "--icon", "icon.icns",  # optional
        ])
    elif platform.system() == "Windows":
        args.extend([
            "--icon", "icon.ico",  # optional
        ])
    
    PyInstaller.__main__.run(args)
    print("\nBuild complete! Check the 'dist' folder for the executable.")

if __name__ == "__main__":
    build()