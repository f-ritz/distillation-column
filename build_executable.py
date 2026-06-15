#!/usr/bin/env python3
"""
Build standalone executable for Distillation Calculator

Usage:
    python build_executable.py

Supported targets (run this script on the target OS for best results):
- Windows (produces .exe)
- macOS (produces .app / executable)

Linux support is dropped for now (user request).

Icon handling:
- icon.png (in project root) is always bundled and used at runtime for the window title bar
  and taskbar/dock on all platforms.
- For the best OS-level icon on the executable itself:
    - Windows: provide icon.ico in the root and it will be used for the .exe
    - macOS: provide icon.icns in the root and it will be used for the .app bundle
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
        "--name", "Distillation_Calculator",
        # Always bundle icon.png for runtime icon (title bar + taskbar/dock)
        "--add-data", f"core{os.pathsep}core",
        "--add-data", f"icon.png{os.pathsep}.",
        "--hidden-import", "customtkinter",
        "--hidden-import", "pandas",
        "--hidden-import", "numpy",
        "--hidden-import", "chemicals",
        "--hidden-import", "pubchempy",
    ]

    # Bundle icon.ico for runtime use on Windows (for iconbitmap inside the app)
    if os.path.exists("icon.ico"):
        args.append(f"--add-data=icon.ico{os.pathsep}.")
    
    # Use platform icon for the .exe / .app file icon (strongly recommended)
    # This makes the icon show in Explorer/Finder and helps the taskbar.
    if platform.system() == "Darwin":  # macOS
        if os.path.exists("icon.icns"):
            args.extend(["--icon", "icon.icns"])
    elif platform.system() == "Windows":
        if os.path.exists("icon.ico"):
            args.extend(["--icon", "icon.ico"])
        # If no .ico, the runtime icon.png will still be used inside the running app via iconphoto.
    
    PyInstaller.__main__.run(args)
    print("\nBuild complete! Check the 'dist' folder for the executable.")

if __name__ == "__main__":
    build()