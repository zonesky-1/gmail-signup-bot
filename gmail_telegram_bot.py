#!/usr/bin/env python3
"""
gmail_telegram_bot.py — Bot Telegram Otomatisasi Pendaftaran Akun Gmail via Patchright.
Owner-only (7998819216).
Mendukung:
  - Step-by-step wizard (/daftar)
  - Random profile quick signup (/acak)
  - Satu baris komando (/quick)
  - Real-time in-place status edit
  - Prompt OTP interaktif di chat Telegram
  - Capture screenshot & upload otomatis ke chat
  - Simpan riwayat ke akun_gmail.txt
"""
import os
import sys
import time
import json
import random
import string
import re
import threading
import subprocess
from datetime import datetime
import urllib.request
import urllib.parse
import requests

from patchright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(HERE, "farmaoalah_token.txt")
TOKEN = open(TOKEN_FILE).read().strip() if os.path.exists(TOKEN_FILE) else "8934049361:AAEG134iXICEZNFgprYJjCfT_oRAwFNMo9c"
OWNER = 7998819216

OUT_FILE = os.path.join(HERE, "akun_gmail.txt")
SCREENSHOT_FILE = os.path.join(HERE, "debug_gmail_bot.png")

API = f"https://api.telegram.org/bot{TOKEN}/"
_last_offset = 0

# Random generator data
NAMA_DEPAN = [
    "Aditya", "Bayu", "Budi", "Dimas", "Eko", "Fajar", "Gilang", "Hendra",
    "Indra", "Joko", "Kevin", "Lukman", "Maulana", "Naufal", "Pratama",
    "Rian", "Rizky", "Satria", "Tegar", "Wahyu", "Yusuf", "Annisa",
    "Citra", "Dewi", "Fitri", "Indah", "Lestari", "Mega", "Nadia", "Putri",
    "Rina", "Sari", "Tiara", "Wulan"
]
NAMA_BELAKANG = [
    "Kusuma", "Pratama", "Saputra", "Wijaya", "Santoso", "Hidayat",
    "Nugroho", "Utomo", "Setiawan", "Wibowo", "Ramadhan", "Permana",
    "Firmansyah", "Kurniawan", "Gunawan"
]

# State session
SESSION = {
    "state": "IDLE",
    "form": {},
    "otp_event": threading.Event(),
    "otp_code": None,
    "status_mid": None,
    "cancel_requested": False,
    "browser": None
}

def ensure_xvfb():
    try:
        r = subprocess.run("DISPLAY=:99 xdpyinfo >/dev/null 2>&1", shell=True, timeout=3)
        if r.returncode != 0:
            subprocess.Popen(["Xvfb", ":99", "-screen", "0", "1366x768x24"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.5)
    except Exception:
        pass
    return True

def api(method, data=None, timeout=35):
    url = API + method
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def send(chat, text, kb=None, edit_mid=None, parse_mode="Markdown"):
    payload = {"chat_id": chat, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if edit_mid:
        payload["message_id"] = edit_mid
        method = "editMessageText"
    else:
        method = "sendMessage"
    if kb:
        payload["reply_markup"] = json.dumps({"inline_keyboard": kb})
    try:
        return api(method, payload)
    except Exception as e:
        err_str = str(e).lower()
        if "not modified" in err_str:
            return {"ok": True}
        if "parse" in err_str:
            payload.pop("parse_mode", None)
            try:
                return api(method, payload)
            except Exception:
                pass
        if edit_mid:
            payload.pop("message_id", None)
            try:
                return api("sendMessage", payload)
            except Exception:
                pass
        return {"ok": False, "err": str(e)}

def send_photo(chat, photo_path, caption=None):
    if not os.path.exists(photo_path):
        return {"ok": False, "err": "File not found"}
    url = API + "sendPhoto"
    data = {"chat_id": chat}
    if caption:
        data["caption"] = caption
        data["parse_mode"] = "Markdown"
    try:
        with open(photo_path, "rb") as f:
            res = requests.post(url, data=data, files={"photo": f}, timeout=30).json()
            if not res.get("ok") and "parse" in str(res.get("description", "")).lower():
                data.pop("parse_mode", None)
                f.seek(0)
                return requests.post(url, data=data, files={"photo": f}, timeout=30).json()
            return res
    except Exception as e:
        return {"ok": False, "err": str(e)}

def answer_cb(cb_id, text=None):
    payload = {"callback_query_id": cb_id}
    if text:
        payload["text"] = text
    try:
        api("answerCallbackQuery", payload)
    except Exception:
        pass

def kb_main():
    return [
        [{"text": "📝 Wizard Daftar", "callback_data": "btn_wizard"},
         {"text": "🎲 Daftar Cepat (Acak)", "callback_data": "btn_quick_rnd"}],
        [{"text": "📋 Daftar Akun Tersimpan", "callback_data": "btn_accounts"},
         {"text": "🖥️ Cek Display :99", "callback_data": "btn_display"}],
        [{"text": "❓ Bantuan / Format", "callback_data": "btn_help"}]
    ]

def kb_gender():
    return [
        [{"text": "👨 Pria (Male)", "callback_data": "gen_male"},
         {"text": "👩 Wanita (Female)", "callback_data": "gen_female"}],
        [{"text": "🤐 Rahasia (Rather not say)", "callback_data": "gen_none"}],
        [{"text": "❌ Batal", "callback_data": "btn_cancel"}]
    ]

def sleep_r(a=0.6, b=1.8):
    time.sleep(random.uniform(a, b))

def human_type(page, el, text):
    try:
        el.click()
        sleep_r(0.2, 0.4)
        for ch in text:
            page.keyboard.type(ch)
            time.sleep(random.uniform(0.04, 0.16))
        sleep_r()
    except Exception:
        page.keyboard.type(text)

def first_visible(page, selectors, timeout=2500):
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=timeout):
                return loc
        except Exception:
            continue
    return None

def click_any(page, selectors=(), texts=()):
    loc = first_visible(page, selectors, timeout=1500)
    if loc:
        loc.click()
        sleep_r()
        return True
    for t in texts:
        for sel in (f"button:has-text('{t}')", f"[role=button]:has-text('{t}')",
                    f"div[role=button]:has-text('{t}')", f"a:has-text('{t}')"):
            try:
                loc = page.locator(sel).first
                if loc.is_visible(timeout=1200):
                    loc.click()
                    sleep_r()
                    return True
            except Exception:
                continue
    return False

def check_google_blocked(page):
    try:
        body = page.inner_text("body")[:3000].lower()
    except Exception:
        return None
    for pat in ("browser or app may not be secure", "unusual traffic",
                "couldn't create your account", "browser atau aplikasi mungkin tidak aman",
                "lalu lintas yang tidak biasa", "tidak dapat membuat akun", "this page isn't available"):
        if pat in body:
            return pat
    return None

def generate_random_profile():
    fn = random.choice(NAMA_DEPAN)
    ln = random.choice(NAMA_BELAKANG)
    rnum = random.randint(100, 9999)
    username = f"{fn.lower()}{ln.lower()}{rnum}"
    chars = string.ascii_letters + string.digits + "!@#$"
    pwd = "".join(random.choice(chars) for _ in range(12)) + "A1!"
    day = str(random.randint(1, 28))
    month = str(random.randint(1, 12))
    year = str(random.randint(1993, 2003))
    return {
        "first": fn,
        "last": ln,
        "username": username,
        "password": pwd,
        "day": day,
        "month": month,
        "year": year,
        "gender": "rather_not_say"
    }

# ── WORKER AUTOMATION ──────────────────────────────────────────────────

def run_signup_worker(chat_id, status_mid, form_data):
    global SESSION
    SESSION["cancel_requested"] = False
    SESSION["otp_code"] = None
    SESSION["otp_event"].clear()

    def update_status(txt, kb=None):
        send(chat_id, txt, kb=kb, edit_mid=status_mid)

    os.environ["DISPLAY"] = ":99"
    ensure_xvfb()

    first = form_data["first"]
    last = form_data["last"]
    username = form_data["username"]
    password = form_data["password"]
    phone = form_data["phone"]
    day = form_data["day"]
    month = form_data["month"]
    year = form_data["year"]
    gender = form_data.get("gender", "rather_not_say")
    proxy = form_data.get("proxy")

    browser = None
    page = None
    try:
        with sync_playwright() as p:
            update_status("⏳ *[1/8] Menyiapkan browser Patchright di :99...*")
            browser_args = ["--disable-blink-features=AutomationControlled"]
            browser = p.chromium.launch(headless=False, args=browser_args)
            SESSION["browser"] = browser

            ctx_kw = {"locale": "en-US", "viewport": {"width": 1366, "height": 900}}
            if proxy:
                ctx_kw["proxy"] = {"server": proxy}
            ctx = browser.new_context(**ctx_kw)
            page = ctx.new_page()

            if SESSION["cancel_requested"]:
                raise Exception("Dibatalkan pengguna.")

            update_status(f"🌐 *[1/8] Membuka Google Signup...*\nTarget: `{username}@gmail.com`")
            page.goto("https://accounts.google.com/signup/v2/webcreateaccount?flowName=GlifWebSignIn&flowEntry=SignUp&hl=en",
                      wait_until="domcontentloaded", timeout=45000)
            sleep_r(2, 3)

            blk = check_google_blocked(page)
            if blk:
                raise RuntimeError(f"Google Risk Engine mendeteksi: `{blk}`")

            # Check recovery screen
            if page.locator("#recoveryEmailId").first.is_visible(timeout=2000):
                click_any(page, texts=("Skip", "Lewati"))
                sleep_r(1, 2)

            if SESSION["cancel_requested"]:
                raise Exception("Dibatalkan pengguna.")

            update_status(f"✍️ *[2/8] Mengisi nama: {first} {last}...*",
                          kb=[[{"text": "❌ Batalkan", "callback_data": "btn_cancel"}]])
            human_type(page, page.locator("#firstName").first, first)
            human_type(page, page.locator("#lastName").first, last)
            click_any(page, selectors=("#accountDetailsNext",), texts=("Next", "Berikutnya"))

            if SESSION["cancel_requested"]:
                raise Exception("Dibatalkan pengguna.")

            update_status("📅 *[3/8] Mengisi tanggal lahir & gender...*",
                          kb=[[{"text": "❌ Batalkan", "callback_data": "btn_cancel"}]])
            page.wait_for_selector("#day, input#day", timeout=20000)
            sleep_r(0.8, 1.2)
            try:
                page.locator("#month").first.select_option(index=int(month))
            except Exception:
                human_type(page, page.locator("#month").first, str(month))
            sleep_r(0.3, 0.6)
            human_type(page, page.locator("#day").first, str(day))
            human_type(page, page.locator("#year").first, str(year))

            gval = {"male": "Male", "female": "Female"}.get(gender.lower(), "Rather not say")
            try:
                page.locator("#gender").first.select_option(label=gval)
            except Exception:
                pass
            sleep_r(0.3, 0.6)
            click_any(page, selectors=("#genderSelectionNext", "#next"), texts=("Next", "Berikutnya"))

            if SESSION["cancel_requested"]:
                raise Exception("Dibatalkan pengguna.")

            update_status(f"👤 *[4/8] Memilih username: {username}...*",
                          kb=[[{"text": "❌ Batalkan", "callback_data": "btn_cancel"}]])
            sleep_r(1.5, 2.0)
            click_any(page, texts=("Create your own Gmail address", "Buat alamat Gmail sendiri"))
            sleep_r(0.6, 1.0)
            if page.locator("#username").first.is_visible(timeout=4000):
                human_type(page, page.locator("#username").first, username)
                click_any(page, selectors=("#next",), texts=("Next", "Berikutnya"))
                sleep_r(1.5, 2.0)
                if page.locator("#username").first.is_visible(timeout=2500):
                    err = page.inner_text("body")[:400]
                    if "taken" in err.lower() or "sudah dipakai" in err.lower():
                        raise RuntimeError(f"Username `{username}` sudah dipakai orang lain.")
            else:
                fallback = first_visible(page, ["#username", "input[type=email]"], timeout=4000)
                if fallback:
                    human_type(page, fallback, username)
                    click_any(page, selectors=("#next",), texts=("Next", "Berikutnya"))

            if SESSION["cancel_requested"]:
                raise Exception("Dibatalkan pengguna.")

            update_status("🔒 *[5/8] Mengisi password...*",
                          kb=[[{"text": "❌ Batalkan", "callback_data": "btn_cancel"}]])
            page.wait_for_selector("#passwd", timeout=20000)
            human_type(page, page.locator("#passwd").first, password)
            human_type(page, page.locator("#confirmPasswd").first, password)
            click_any(page, selectors=("#create-password-next",), texts=("Next", "Berikutnya"))

            if SESSION["cancel_requested"]:
                raise Exception("Dibatalkan pengguna.")

            update_status("📱 *[6/8] Memeriksa verifikasi nomor HP...*")
            if page.locator("#phoneNumberId").first.is_visible(timeout=15000):
                human_type(page, page.locator("#phoneNumberId").first, phone)
                click_any(page, selectors=("#sendVerifyCodeButton", "#next"),
                          texts=("Get a verification code", "Dapatkan kode verifikasi", "Verify", "Verifikasi", "Next", "Berikutnya"))
                sleep_r(2, 3)

                blk = check_google_blocked(page)
                if blk:
                    raise RuntimeError(f"Google Risk Engine memblokir nomor: `{blk}`")

                otp_el = first_visible(page, ["#code", "input[type=tel]"], timeout=20000)
                if otp_el is None:
                    page.screenshot(path=SCREENSHOT_FILE)
                    raise RuntimeError("Field OTP tidak muncul. Cek screenshot.")

                # MINTA OTP KE TELEGRAM CHAT
                SESSION["state"] = "WAITING_OTP"
                SESSION["otp_event"].clear()
                update_status(
                    f"📩 *KODE OTP DIBUTUHKAN!*\n\n"
                    f"Google sudah mengirim SMS kode verifikasi ke `{phone}`.\n\n"
                    f"👉 *Ketik 6 digit kode OTP langsung di chat ini* (contoh: `123456`):\n"
                    f"*(Waktu tunggu 180 detik)*",
                    kb=[[{"text": "❌ Batalkan", "callback_data": "btn_cancel"}]]
                )

                signaled = SESSION["otp_event"].wait(timeout=180)
                if SESSION["cancel_requested"]:
                    raise Exception("Dibatalkan pengguna.")
                if not signaled or not SESSION.get("otp_code"):
                    raise RuntimeError("Waktu tunggu OTP habis (3 menit) atau tidak ada input.")

                otp = SESSION["otp_code"]
                update_status(f"⏳ *[6/8] Memasukkan kode OTP: `{otp}`...*")
                human_type(page, otp_el, otp)
                click_any(page, selectors=("#verifyCodeButton",), texts=("Verify", "Verifikasi", "Next", "Berikutnya"))
                sleep_r(2.5, 3.5)
            else:
                update_status("⏩ Google tidak meminta verifikasi nomor HP.")

            if SESSION["cancel_requested"]:
                raise Exception("Dibatalkan pengguna.")

            update_status("📜 *[7/8] Menyetujui Persyaratan Layanan (ToS)...*")
            sleep_r(1.5, 2.0)
            click_any(page, texts=("Yes, I'm in", "Ya, saya ikut"))
            sleep_r(1.5, 2.0)
            click_any(page, texts=("Skip", "Lewati"))
            sleep_r(1.5, 2.0)
            click_any(page, selectors=("#termAgree",), texts=("I agree", "Saya setuju"))
            sleep_r(3, 4)

            blk = check_google_blocked(page)
            if blk:
                raise RuntimeError(f"Google Risk Engine memblokir ToS: `{blk}`")

            update_status("🔍 *[8/8] Memverifikasi akun...*")
            url = page.url
            try:
                body = page.inner_text("body")[:600]
            except Exception:
                body = ""

            ok = ("myaccount.google.com" in url) or ("Welcome" in body) or ("Selamat datang" in body)
            page.screenshot(path=SCREENSHOT_FILE)

            email = f"{username}@gmail.com"
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if ok:
                with open(OUT_FILE, "a") as f:
                    f.write(f"{email}|{password}|{phone}|{ts}\n")
                msg = (
                    f"🎉 *PENDAFTARAN GMAIL SUKSES!*\n"
                    f"──────────────────────\n"
                    f"📧 *Email:* `{email}`\n"
                    f"🔑 *Password:* `{password}`\n"
                    f"📱 *Nomor HP:* `{phone}`\n"
                    f"📅 *Waktu:* `{ts}`\n"
                    f"──────────────────────\n"
                    f"💾 *Tersimpan di:* `akun_gmail.txt`"
                )
                update_status(msg, kb=kb_main())
                send_photo(chat_id, SCREENSHOT_FILE, caption=f"✅ Bukti signup berhasil: `{email}`")
            else:
                with open(OUT_FILE, "a") as f:
                    f.write(f"{email} (cek_manual)|{password}|{phone}|{ts}\n")
                msg = (
                    f"⚠️ *Status Akun Belum Terkonfirmasi*\n"
                    f"──────────────────────\n"
                    f"📧 Target: `{email}`\n"
                    f"🌐 URL Akhir: `{url}`\n"
                    f"Cek screenshot untuk detail layar terakhir Google."
                )
                update_status(msg, kb=kb_main())
                send_photo(chat_id, SCREENSHOT_FILE, caption=f"📸 Layar Google: `{email}`")

    except Exception as e:
        err_msg = str(e)
        try:
            if page:
                page.screenshot(path=SCREENSHOT_FILE)
        except Exception:
            pass
        send(chat_id,
             f"❌ *Pendaftaran Gagal*\n\n"
             f"Error: `{err_msg}`\n\n"
             f"💡 *Catatan:* Jika terblokir Risk Engine Google, gunakan Residential Proxy via parameter proxy atau coba jeda beberapa saat.",
             kb=kb_main(), edit_mid=status_mid)
        if os.path.exists(SCREENSHOT_FILE):
            send_photo(chat_id, SCREENSHOT_FILE, caption="📸 Tangkapan layar browser saat gagal")

    finally:
        SESSION["state"] = "IDLE"
        SESSION["browser"] = None
        SESSION["otp_code"] = None
        if browser:
            try:
                browser.close()
            except Exception:
                pass

# ── TELEGRAM HANDLERS ──────────────────────────────────────────────────

def handle_callback(cb):
    chat = cb["message"]["chat"]["id"]
    mid = cb["message"]["message_id"]
    uid = cb["from"]["id"]
    data = cb.get("data", "")
    answer_cb(cb["id"])

    if uid != OWNER:
        return

    if data == "btn_wizard":
        SESSION["form"] = {}
        SESSION["state"] = "WIZ_NAME"
        send(chat, "👤 *[Step 1/6: Nama]*\n\nKetik nama depan & belakang (contoh: `Budi Santoso`):",
             kb=[[{"text": "❌ Batal", "callback_data": "btn_cancel"}]], edit_mid=mid)

    elif data == "btn_quick_rnd":
        prof = generate_random_profile()
        SESSION["form"] = prof
        SESSION["state"] = "QUICK_PHONE"
        txt = (
            "🎲 *PROFIL ACAK DIGENERATE!*\n"
            "──────────────────────\n"
            f"Nama: `{prof['first']} {prof['last']}`\n"
            f"Target: `{prof['username']}@gmail.com`\n"
            f"Password: `{prof['password']}`\n"
            f"TTL: `{prof['day']}/{prof['month']}/{prof['year']}`\n"
            "──────────────────────\n\n"
            "👉 *Ketik Nomor HP lo sekarang* (format `+62812xxx` atau `0812xxx`):"
        )
        send(chat, txt, kb=[[{"text": "❌ Batal", "callback_data": "btn_cancel"}]], edit_mid=mid)

    elif data == "btn_accounts":
        if not os.path.exists(OUT_FILE):
            send(chat, "Belum ada akun tersimpan di `akun_gmail.txt`.", kb=kb_main(), edit_mid=mid)
            return
        lines = [l.strip() for l in open(OUT_FILE) if l.strip()]
        if not lines:
            send(chat, "File `akun_gmail.txt` masih kosong.", kb=kb_main(), edit_mid=mid)
            return
        last_accounts = lines[-10:]
        txt = f"📋 *DAFTAR AKUN GMAIL (Total: {len(lines)})*\n──────────────────────\n"
        for idx, acc in enumerate(last_accounts, 1):
            txt += f"{idx}. `{acc}`\n"
        send(chat, txt, kb=kb_main(), edit_mid=mid)

    elif data == "btn_display":
        res = subprocess.run("DISPLAY=:99 xdpyinfo >/dev/null 2>&1 && echo OK || echo FAIL",
                             shell=True, capture_output=True, text=True)
        st = "🟢 AKTIF" if "OK" in res.stdout else "🔴 NONAKTIF (Auto-start saat signup)"
        send(chat, f"🖥️ *Status Virtual Display :99*\n\nStatus: {st}", kb=kb_main(), edit_mid=mid)

    elif data == "btn_help":
        txt = (
            "📖 *PANDUAN GMAIL SIGNUP BOT*\n"
            "──────────────────────\n"
            "1. *Wizard (/daftar)*: Input detail satu per satu secara interaktif.\n"
            "2. *Cepat Acak (/acak)*: Otomatis generate nama, target user & password kuat, cukup ketik nomor HP.\n"
            "3. *Perintah Instan (/quick)*:\n"
            "`/quick Budi | Santoso | budisantoso88 | Password123! | +6281234567890`\n\n"
            "Saat Google kirim SMS OTP, bot otomatis minta kode 6 digit di chat ini."
        )
        send(chat, txt, kb=kb_main(), edit_mid=mid)

    elif data.startswith("gen_"):
        mapping = {"gen_male": "Male", "gen_female": "Female", "gen_none": "Rather not say"}
        SESSION["form"]["gender"] = mapping.get(data, "Rather not say")
        form = SESSION["form"]
        SESSION["state"] = "CONFIRM"
        txt = (
            "📋 *KONFIRMASI PENDAFTARAN*\n"
            "──────────────────────\n"
            f"Nama: `{form['first']} {form['last']}`\n"
            f"Email: `{form['username']}@gmail.com`\n"
            f"Password: `{form['password']}`\n"
            f"Nomor HP: `{form['phone']}`\n"
            f"TTL: `{form['day']}/{form['month']}/{form['year']}`\n"
            f"Gender: `{form['gender']}`\n"
            "──────────────────────\n"
            "Siap dijalankan di browser :99?"
        )
        send(chat, txt, kb=[
            [{"text": "🚀 Gas Daftar Sekarang", "callback_data": "btn_start_run"}],
            [{"text": "❌ Batal", "callback_data": "btn_cancel"}]
        ], edit_mid=mid)

    elif data == "btn_start_run":
        SESSION["state"] = "RUNNING"
        sm = send(chat, "🚀 *Memulai pendaftaran Gmail...*", edit_mid=mid)
        status_mid = sm.get("result", {}).get("message_id", mid)
        t = threading.Thread(target=run_signup_worker, args=(chat, status_mid, SESSION["form"]))
        t.daemon = True
        t.start()

    elif data == "btn_cancel":
        SESSION["cancel_requested"] = True
        if SESSION["browser"]:
            try:
                SESSION["browser"].close()
            except Exception:
                pass
        SESSION["otp_event"].set()
        SESSION["state"] = "IDLE"
        send(chat, "❌ *Operasi dibatalkan.*", kb=kb_main(), edit_mid=mid)

def handle_message(msg):
    global _last_offset
    if "text" not in msg:
        return
    chat = msg["chat"]["id"]
    uid = msg.get("from", {}).get("id")
    text = msg["text"].strip()

    if uid != OWNER:
        send(chat, "Maaf, bot ini private. Khusus owner.")
        return

    state = SESSION.get("state", "IDLE")

    if text.startswith("/cancel"):
        SESSION["cancel_requested"] = True
        if SESSION["browser"]:
            try:
                SESSION["browser"].close()
            except Exception:
                pass
        SESSION["otp_event"].set()
        SESSION["state"] = "IDLE"
        send(chat, "❌ *Pendaftaran dibatalkan.*", kb=kb_main())
        return

    # Handle OTP input saat browser menunggu
    if state == "WAITING_OTP":
        m = re.search(r"\b\d{6}\b", text)
        if m:
            otp_val = m.group(0)
            SESSION["otp_code"] = otp_val
            SESSION["otp_event"].set()
            send(chat, f"⏳ *Kode OTP `{otp_val}` diterima.* Meneruskan ke Google...")
        else:
            send(chat, "⚠️ Masukkan tepat 6 angka OTP (contoh: `123456`) atau /cancel:")
        return

    if text.startswith("/start") or text.startswith("/menu"):
        SESSION["state"] = "IDLE"
        send(chat,
             "🤖 *GMAIL SIGNUP BOT — CONTROL PANEL*\n"
             "──────────────────────\n"
             "Bot otomatisasi pembuatan akun Google via Patchright Chromium.\n\n"
             "Pilih mode dari tombol menu di bawah:",
             kb=kb_main())
        return

    if text.startswith("/daftar"):
        SESSION["form"] = {}
        SESSION["state"] = "WIZ_NAME"
        send(chat, "👤 *[Step 1/6: Nama]*\n\nKetik nama depan & belakang (contoh: `Budi Santoso`):",
             kb=[[{"text": "❌ Batal", "callback_data": "btn_cancel"}]])
        return

    if text.startswith("/acak"):
        prof = generate_random_profile()
        SESSION["form"] = prof
        SESSION["state"] = "QUICK_PHONE"
        txt = (
            "🎲 *PROFIL ACAK DIGENERATE!*\n"
            "──────────────────────\n"
            f"Nama: `{prof['first']} {prof['last']}`\n"
            f"Target: `{prof['username']}@gmail.com`\n"
            f"Password: `{prof['password']}`\n"
            f"TTL: `{prof['day']}/{prof['month']}/{prof['year']}`\n"
            "──────────────────────\n\n"
            "👉 *Ketik Nomor HP lo sekarang* (format `+62812xxx`):"
        )
        send(chat, txt, kb=[[{"text": "❌ Batal", "callback_data": "btn_cancel"}]])
        return

    if text.startswith("/quick"):
        parts = [p.strip() for p in text.replace("/quick", "").split("|") if p.strip()]
        if len(parts) < 5:
            send(chat, "⚠️ Format salah.\nGunakan: `/quick First | Last | username | pass | +628xxx`")
            return
        first, last, uname, pwd, ph = parts[0], parts[1], parts[2], parts[3], parts[4]
        if not ph.startswith("+"):
            ph = "+62" + ph.lstrip("0")
        SESSION["form"] = {
            "first": first, "last": last,
            "username": uname.replace("@gmail.com", ""),
            "password": pwd, "phone": ph,
            "day": "15", "month": "06", "year": "1998", "gender": "rather_not_say"
        }
        SESSION["state"] = "RUNNING"
        sm = send(chat, "🚀 *Menjalankan pendaftaran via Quick Command...*")
        status_mid = sm.get("result", {}).get("message_id")
        t = threading.Thread(target=run_signup_worker, args=(chat, status_mid, SESSION["form"]))
        t.daemon = True
        t.start()
        return

    # Wizard state transitions
    if state == "WIZ_NAME":
        parts = text.split()
        first = parts[0]
        last = " ".join(parts[1:]) if len(parts) > 1 else "Pratama"
        SESSION["form"]["first"] = first
        SESSION["form"]["last"] = last
        SESSION["state"] = "WIZ_USER"
        send(chat, f"✅ Nama: `{first} {last}`\n\n👤 *[Step 2/6: Username]*\nKetik username Gmail yang diinginkan (tanpa @gmail.com):",
             kb=[[{"text": "❌ Batal", "callback_data": "btn_cancel"}]])

    elif state == "WIZ_USER":
        uname = text.replace("@gmail.com", "").replace(" ", "").lower()
        SESSION["form"]["username"] = uname
        SESSION["state"] = "WIZ_PASS"
        chars = string.ascii_letters + string.digits + "!@#$"
        rnd_pass = "".join(random.choice(chars) for _ in range(12)) + "A1!"
        send(chat, f"✅ Target: `{uname}@gmail.com`\n\n🔒 *[Step 3/6: Password]*\nKetik password (atau ketik `acak` untuk password otomatis `{rnd_pass}`):",
             kb=[[{"text": "❌ Batal", "callback_data": "btn_cancel"}]])

    elif state == "WIZ_PASS":
        if text.lower() == "acak":
            chars = string.ascii_letters + string.digits + "!@#$"
            pwd = "".join(random.choice(chars) for _ in range(12)) + "A1!"
        else:
            pwd = text
        SESSION["form"]["password"] = pwd
        SESSION["state"] = "WIZ_PHONE"
        send(chat, f"✅ Password diatur.\n\n📱 *[Step 4/6: Nomor HP]*\nKetik nomor HP verifikasi (+62812xxx atau 0812xxx):",
             kb=[[{"text": "❌ Batal", "callback_data": "btn_cancel"}]])

    elif state == "WIZ_PHONE":
        ph = text.replace(" ", "").replace("-", "")
        if not ph.startswith("+"):
            ph = "+62" + ph.lstrip("0")
        SESSION["form"]["phone"] = ph
        SESSION["state"] = "WIZ_DOB"
        send(chat, f"✅ Nomor HP: `{ph}`\n\n📅 *[Step 5/6: Tanggal Lahir]*\nKetik format `DD/MM/YYYY` (contoh: `15/08/1998`) atau ketik `acak`:",
             kb=[[{"text": "❌ Batal", "callback_data": "btn_cancel"}]])

    elif state == "WIZ_DOB":
        if text.lower() == "acak":
            d, m, y = str(random.randint(1, 28)), str(random.randint(1, 12)), str(random.randint(1993, 2003))
        else:
            pts = text.split("/")
            if len(pts) == 3:
                d, m, y = pts[0].strip(), pts[1].strip(), pts[2].strip()
            else:
                d, m, y = "15", "06", "1998"
        SESSION["form"]["day"] = d
        SESSION["form"]["month"] = m
        SESSION["form"]["year"] = y
        SESSION["state"] = "WIZ_GENDER"
        send(chat, f"✅ TTL: `{d}/{m}/{y}`\n\n🚻 *[Step 6/6: Pilih Gender]*", kb=kb_gender())

    elif state == "QUICK_PHONE":
        ph = text.replace(" ", "").replace("-", "")
        if not ph.startswith("+"):
            ph = "+62" + ph.lstrip("0")
        SESSION["form"]["phone"] = ph
        SESSION["state"] = "RUNNING"
        sm = send(chat, f"🚀 *Menjalankan pendaftaran akun acak...*\nNo HP: `{ph}`")
        status_mid = sm.get("result", {}).get("message_id")
        t = threading.Thread(target=run_signup_worker, args=(chat, status_mid, SESSION["form"]))
        t.daemon = True
        t.start()

def main():
    global _last_offset
    ensure_xvfb()
    me = api("getMe")
    uname = me.get("result", {}).get("username", "Unknown")
    print(f"Bot Gmail Signup live: @{uname}", flush=True)
    while True:
        try:
            updates = api("getUpdates", {"offset": _last_offset, "timeout": 30}, timeout=40)
            for u in updates.get("result", []):
                _last_offset = u["update_id"] + 1
                if "callback_query" in u:
                    handle_callback(u["callback_query"])
                elif "message" in u:
                    handle_message(u["message"])
        except Exception as e:
            time.sleep(3)

if __name__ == "__main__":
    main()
