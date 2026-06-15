#!/usr/bin/env python3
"""
Build standalone executable for Distillation Calculator

Usage:
    python build_executable.py

Supported targets (run this script on the target OS for best results):
- Windows (produces Distillation_Calculator.exe)
- macOS (produces Distillation_Calculator.app bundle - double-clickable)

Linux support is dropped for now (user request).

Icon handling:
- icon.png (in project root) is always bundled via --add-data and used at runtime
  for the window title bar and taskbar/dock on all platforms (via the code in gui/app.py).
- For the best OS-level icon on the distributed file:
    - Windows: provide icon.ico → used for the .exe itself (--icon) and runtime.
    - macOS: provide icon.icns → used for the .app bundle icon (Finder, Dock, etc.).

To create icon.icns from your icon.png (run on macOS):
    mkdir -p icon.iconset
    sips -z 16 16   icon.png --out icon.iconset/icon_16x16.png
    sips -z 32 32   icon.png --out icon.iconset/icon_32x32.png
    sips -z 64 64   icon.png --out icon.iconset/icon_64x64.png
    sips -z 128 128 icon.png --out icon.iconset/icon_128x128.png
    sips -z 256 256 icon.png --out icon.iconset/icon_256x256.png
    sips -z 512 512 icon.png --out icon.iconset/icon_512x512.png
    sips -z 1024 1024 icon.png --out icon.iconset/icon_1024x1024.png
    iconutil -c icns icon.iconset -o icon.icns
    (You can also use free online "PNG to ICNS" converters.)
"""

import PyInstaller.__main__
import os
import sys
import platform
import shutil

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

    # Post-processing for a polished macOS .app bundle (makes it feel like a real Mac app)
    if platform.system() == "Darwin":
        _create_macos_app_bundle()

    print("\nBuild complete! Check the 'dist' folder.")
    if platform.system() == "Darwin":
        print("  macOS users: open the .app (first launch: right-click → Open, or run `xattr -cr` on it).")
    else:
        print("  The executable is ready to distribute (copy to /Applications on macOS after building there).")


def _create_macos_app_bundle():
    """Wrap the PyInstaller onefile executable in a proper .app bundle with icon + Info.plist."""
    app_name = "Distillation_Calculator.app"
    bundle_path = os.path.join("dist", app_name)

    # Clean previous
    if os.path.exists(bundle_path):
        shutil.rmtree(bundle_path)

    macos_dir = os.path.join(bundle_path, "Contents", "MacOS")
    resources_dir = os.path.join(bundle_path, "Contents", "Resources")
    os.makedirs(macos_dir, exist_ok=True)
    os.makedirs(resources_dir, exist_ok=True)

    # The binary PyInstaller just produced
    exe_name = "Distillation_Calculator"
    src_exe = os.path.join("dist", exe_name)
    dst_exe = os.path.join(macos_dir, exe_name)

    if os.path.isfile(src_exe):
        shutil.move(src_exe, dst_exe)
        os.chmod(dst_exe, 0o755)
    else:
        print(f"[macOS bundle] Warning: expected executable not found at {src_exe}")
        return

    # Copy icons for the bundle (Finder/Dock uses the .icns via Info.plist)
    if os.path.exists("icon.icns"):
        shutil.copy("icon.icns", os.path.join(resources_dir, "icon.icns"))
    if os.path.exists("icon.png"):
        shutil.copy("icon.png", os.path.join(resources_dir, "icon.png"))

    # Minimal but functional Info.plist so macOS treats it as a proper GUI application
    bundle_id = "com.f-ritz.distillationcalculator"
    version = "1.0"
    plist = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>Distillation Calculator</string>
    <key>CFBundleDisplayName</key>
    <string>Distillation Calculator</string>
    <key>CFBundleIdentifier</key>
    <string>{bundle_id}</string>
    <key>CFBundleVersion</key>
    <string>{version}</string>
    <key>CFBundleShortVersionString</key>
    <string>{version}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleExecutable</key>
    <string>{exe_name}</string>
    <key>CFBundleIconFile</key>
    <string>icon.icns</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.13</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
</dict>
</plist>
'''

    with open(os.path.join(bundle_path, "Contents", "Info.plist"), "w", encoding="utf-8") as f:
        f.write(plist)

    print(f"[macOS] Created app bundle: {bundle_path}")
    print("        You can drag this into /Applications.")


if __name__ == "__main__":
    build()