#!/usr/bin/env python3
"""
=============================================================================
             GMAIL SIGNUP AUTOMATION ENGINE (GlifWebSignIn 2026)
=============================================================================
Arsitektur:
1. Headless=False via Xvfb Virtual Display (:99) + Patchright Chromium Stealth.
2. Gateway: YouTube Mobile via Facebook IAB Referrer (Trust context Google).
3. Modern Dynamic DOM Handling:
   - Google Material Combobox (Bulan & Gender via Navigasi Keyboard).
   - Auto-Click 'Buat alamat Gmail' & Auto-Select Radio Rekomendasi (Anti-Bentrok).
   - Pengisian Password Kuat & Konfirmasi.
4. Checkpoint Mobile Verification:
   - Ekstraksi otomatis gambar Base64 QR Code.
   - Decoding instan ke Link Web Verifikasi langsung via `zbarimg`.
   - Pengiriman Link & QR ke Telegram Operator secara real-time.
   - Auto-Listener State: Mendeteksi saat verifikasi selesai dari ponsel.
   - Auto-Bypass Recovery (Lewati) & Auto-Accept ToS (Saya setuju).
   - Menyimpan akun aktif ke `akun_gmail.txt` & konfirmasi Telegram.
=============================================================================
"""

import os
import sys
import time
import random
import string
import base64
import subprocess
import urllib.request
import json
from patchright.sync_api import sync_playwright

# ── KONFIGURASI LINGKUNGAN ───────────────────────────────────────────────
os.environ["DISPLAY"] = ":99"

BOT_TOKEN = "8934049361:AAH8N_u3uQ-F7u_Jqf4qJz_X3sZ8X9X0_X0"
# Ambil token aktif jika ada
TOKEN_FILE = "/home/agentuser/gmail-signup-bot/farmaoalah_token.txt"
if os.path.exists(TOKEN_FILE):
    try:
        BOT_TOKEN = open(TOKEN_FILE).read().strip()
    except Exception:
        pass

CHAT_ID = "7998819216"
BASE_DIR = "/home/agentuser/gmail-signup-bot"
OUT_FILE = os.path.join(BASE_DIR, "akun_gmail.txt")
SCREENSHOT_DIR = os.path.join(BASE_DIR, "manual_screens")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

NAMA_DEPAN = ["Budi", "Rafi", "Indra", "Dimas", "Aditya", "Reza", "Fajar", "Bayu", "Rian", "Wahyu", "Bagas", "Gilang"]
NAMA_BELAKANG = ["Santoso", "Pratama", "Setiawan", "Nugroho", "Saputra", "Utomo", "Kusuma", "Hidayat", "Wijaya", "Siregar"]

# ── TELEGRAM NOTIFIER ────────────────────────────────────────────────────

def tg_send(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[-] Telegram send error: {e}", flush=True)

def tg_photo(photo_path, caption=""):
    try:
        boundary = "----WebKitFormBoundary" + "".join(random.choices(string.ascii_letters + string.digits, k=16))
        body = []
        body.append(f"--{boundary}".encode())
        body.append(f'Content-Disposition: form-data; name="chat_id"'.encode())
        body.append(b"")
        body.append(str(CHAT_ID).encode())
        if caption:
            body.append(f"--{boundary}".encode())
            body.append(f'Content-Disposition: form-data; name="caption"'.encode())
            body.append(b"")
            body.append(caption.encode())
        body.append(f"--{boundary}".encode())
        fname = os.path.basename(photo_path)
        body.append(f'Content-Disposition: form-data; name="photo"; filename="{fname}"'.encode())
        body.append(b"Content-Type: image/png")
        body.append(b"")
        with open(photo_path, "rb") as f:
            body.append(f.read())
        body.append(f"--{boundary}--".encode())
        body.append(b"")
        payload = b"\r\n".join(body)
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        urllib.request.urlopen(req, timeout=20)
    except Exception as e:
        print(f"[-] Telegram photo error: {e}", flush=True)

# ── CORE REGISTRATION ENGINE ─────────────────────────────────────────────

def create_gmail_account():
    fn = random.choice(NAMA_DEPAN)
    ln = random.choice(NAMA_BELAKANG)
    chars = string.ascii_letters + string.digits + "!@#$"
    raw_pass = "".join(random.choice(chars) for _ in range(12)) + "A1!"
    day = str(random.randint(1, 28))
    month = random.randint(1, 12)
    year = str(random.randint(1995, 2002))
    
    print(f"\n=======================================================", flush=True)
    print(f"🚀 MEMULAI PROSES PENDAFTARAN GOOGLE", flush=True)
    print(f"Profil: {fn} {ln} | TTL: {day}/{month}/{year} | Gender: Pria", flush=True)
    print(f"=======================================================\n", flush=True)
    
    tg_send(f"🚀 *[1/5] Memulai sesi registrasi Google di VPS...*\nNama: `{fn} {ln}`\nTTL: `{day}/{month}/{year}`")
    
    # Konfigurasi proxy residential (bila diperlukan)
    proxy_cfg = {"server": "http://tw-tai.pvdata.host:8080", "username": "g2rTXpNfPdcw2fzGtWKp62yH", "password": "nizar1elad2"}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"]
        )
        ctx = browser.new_context(
            locale="id-ID",
            proxy=proxy_cfg,
            viewport={"width": 1366, "height": 900},
            extra_http_headers={"Referer": "https://l.facebook.com/"}
        )
        page = ctx.new_page()
        
        # 1. Gateway Pendaftaran
        yt_gate = "https://accounts.google.com/signup/v2/webcreateaccount?flowName=GlifWebSignIn&flowEntry=SignUp&continue=https%3A%2F%2Fm.youtube.com%2F%40YKXXXXC&service=youtube&hl=id"
        print("[1] Membuka URL pendaftaran...", flush=True)
        page.goto(yt_gate, wait_until="domcontentloaded", timeout=45000)
        time.sleep(2.5)
        
        # 2. Pengisian Nama
        print("[2] Mengisi nama depan & belakang...", flush=True)
        page.locator('#firstName').fill(fn)
        page.locator('#lastName').fill(ln)
        time.sleep(0.3)
        page.locator("button:has-text('Berikutnya'), button:has-text('Next')").first.click()
        
        # 3. Tanggal Lahir & Gender (Google Material Combobox)
        print("[3] Menunggu halaman Tanggal Lahir & Gender...", flush=True)
        m_el = page.locator('#month').first
        m_el.wait_for(state="visible", timeout=20000)
        time.sleep(0.5)
        m_el.click()
        time.sleep(0.3)
        for _ in range(month):
            page.keyboard.press("ArrowDown")
            time.sleep(0.03)
        page.keyboard.press("Enter")
        time.sleep(0.2)
        
        page.locator('#day').first.fill(day)
        page.locator('#year').first.fill(year)
        time.sleep(0.2)
        
        # Gender Pria: ArrowDown 2x
        g_el = page.locator('#gender').first
        g_el.click()
        time.sleep(0.3)
        page.keyboard.press("ArrowDown")
        page.keyboard.press("ArrowDown")
        page.keyboard.press("Enter")
        time.sleep(0.2)
        
        page.locator("button:has-text('Berikutnya'), button:has-text('Next')").first.click()
        time.sleep(2.5)
        
        # 4. Pemilihan Alamat Gmail (Radio Saran Google)
        print("[4] Memilih alamat Gmail rekomendasi...", flush=True)
        btn_buat_gmail = page.locator("button:has-text('Buat alamat Gmail'), [role='button']:has-text('Gmail')").first
        if btn_buat_gmail.is_visible(timeout=3000):
            btn_buat_gmail.click()
            time.sleep(2.0)
            
        chosen_email = None
        radios = page.locator("input[type='radio'], input[name='usernameRadio']").all()
        if radios:
            try:
                txt = radios[0].evaluate("el => el.closest('div').innerText").strip()
                for w in txt.split():
                    if "@gmail.com" in w:
                        chosen_email = w.strip()
                        break
            except Exception:
                pass
            radios[0].click(force=True)
            time.sleep(0.4)
        else:
            u_in = page.locator("input[name='Username']").first
            chosen_email = f"{fn.lower()}{ln.lower()}{random.randint(10000, 99999)}@gmail.com"
            u_in.fill(chosen_email.split('@')[0])
            time.sleep(0.4)
            
        if not chosen_email:
            chosen_email = f"{fn.lower()}{ln.lower()}{random.randint(10000, 99999)}@gmail.com"
            
        print(f"[+] Alamat Gmail Terpilih: {chosen_email}", flush=True)
        page.locator("button:has-text('Berikutnya'), button:has-text('Next')").first.click()
        
        # 5. Pengisian Password
        print(f"[5] Mengisi password kuat: {raw_pass}...", flush=True)
        pwd = page.locator("input[name='Passwd'], input[type='password']").first
        pwd.wait_for(state="visible", timeout=20000)
        pwd.fill(raw_pass)
        time.sleep(0.3)
        pwd_again = page.locator("input[name='PasswdAgain']").first
        if pwd_again.is_visible(timeout=2000):
            pwd_again.fill(raw_pass)
        time.sleep(0.3)
        page.locator("button:has-text('Berikutnya'), button:has-text('Next')").first.click()
        time.sleep(4.5)
        
        # 6. Checkpoint Verifikasi & Ekstraksi QR Code
        print(f"[6] Sampai di checkpoint verifikasi: {page.url}", flush=True)
        qr_shot = os.path.join(SCREENSHOT_DIR, "live_checkpoint.png")
        page.screenshot(path=qr_shot)
        
        qr_img_data = page.evaluate('''() => {
            const img = document.querySelector('img[src*="data:image/png;base64"]');
            return img ? img.src : null;
        }''')
        
        qr_link = None
        if qr_img_data:
            b64_str = qr_img_data.split("base64,")[-1]
            qr_file = "/tmp/cur_qr.png"
            with open(qr_file, "wb") as f:
                f.write(base64.b64decode(b64_str))
            try:
                r = subprocess.run(["zbarimg", qr_file], capture_output=True, text=True)
                for line in r.stdout.splitlines():
                    if "QR-Code:" in line:
                        qr_link = line.split("QR-Code:")[-1].strip()
                        break
            except Exception:
                pass
                
        link_md = f"\n👉 [KLIK LINK INI DARI HP (TAB INCOGNITO)]({qr_link})\n" if qr_link else ""
        tg_send(
            f"📱 *KODE VERIFIKASI SMS DIBUTUHKAN!*\n\n"
            f"Target Akun: `{chosen_email}`\n"
            f"Password: `{raw_pass}`\n"
            f"{link_md}\n"
            f"*(Sesi aktif ditahan di server selama 10 menit menunggu SMS terkirim)*"
        )
        if os.path.exists(qr_shot):
            tg_photo(qr_shot, caption="📸 Layar verifikasi saat ini")
            
        # 7. Polling Sesi Hingga Verifikasi Diterima
        print("[7] Menunggu verifikasi SMS lolos di browser (timeout 600s)...", flush=True)
        start_w = time.time()
        passed = False
        while time.time() - start_w < 600:
            cur_url = page.url
            if any(k in cur_url for k in ["recovery", "terms", "ManageAccount", "myaccount", "speedbump", "voiceandvideo"]):
                print(f"[+] Verifikasi lolos! URL berpindah ke: {cur_url}", flush=True)
                passed = True
                break
            if "crossflowverification" not in cur_url and "signup/password" not in cur_url:
                print(f"[+] Verifikasi lolos! URL berpindah ke: {cur_url}", flush=True)
                passed = True
                break
                
            if page.locator("button:has-text('Lewati'), button:has-text('Skip')").first.is_visible(timeout=300) or \
               page.locator("button:has-text('Saya setuju'), button:has-text('I agree')").first.is_visible(timeout=300):
                print("[+] Tombol lanjutan terdeteksi! Melanjutkan...", flush=True)
                passed = True
                break
                
            time.sleep(2)
            
        if not passed:
            tg_send("❌ *Waktu tunggu verifikasi habis.* Pendaftaran dibatalkan.")
            browser.close()
            return None
            
        # 8. Selesaikan Form Sisa (Lewati Recovery & Agree ToS)
        print("[8] Menyelesaikan Terms of Service & Recovery...", flush=True)
        for step_idx in range(6):
            time.sleep(2.5)
            cur_u = page.url
            if "myaccount.google.com" in cur_u or "ManageAccount" in cur_u:
                break
                
            skip_b = page.locator("button:has-text('Lewati'), button:has-text('Skip')").first
            if skip_b.is_visible(timeout=2000):
                skip_b.click()
                time.sleep(2.0)
                continue
                
            next_b = page.locator("button:has-text('Berikutnya'), button:has-text('Next')").first
            if next_b.is_visible(timeout=2000):
                next_b.click()
                time.sleep(2.0)
                continue
                
            agree_b = page.locator("button:has-text('Saya setuju'), button:has-text('I agree')").first
            if agree_b.is_visible(timeout=2000):
                agree_b.click()
                time.sleep(4.0)
                break
                
        # 9. Penyimpanan Hasil Akun
        final_shot = os.path.join(SCREENSHOT_DIR, "account_created_success.png")
        page.screenshot(path=final_shot)
        
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(OUT_FILE, "a") as f:
            f.write(f"{chosen_email}|{raw_pass}|{ts}\n")
            
        success_msg = (
            f"🎉 *AKUN GMAIL BERHASIL DIBUAT!*\n"
            f"──────────────────────\n"
            f"📧 *Email:* `{chosen_email}`\n"
            f"🔑 *Password:* `{raw_pass}`\n"
            f"📅 *Waktu:* `{ts}`\n"
            f"──────────────────────\n"
            f"💾 *Tersimpan di:* `akun_gmail.txt`"
        )
        print(success_msg, flush=True)
        tg_send(success_msg)
        if os.path.exists(final_shot):
            tg_photo(final_shot, caption=f"✅ Akun Google Aktif: {chosen_email}")
            
        browser.close()
        return {"email": chosen_email, "password": raw_pass}

if __name__ == "__main__":
    create_gmail_account()
