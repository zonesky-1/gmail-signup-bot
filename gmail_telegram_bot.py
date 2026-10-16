#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚡ Gmail Signup Telegram Bot (Patchright Engine)
================================================
Bot Telegram untuk otomasi pendaftaran akun Gmail berbasis Patchright.
Semua alur (pengisian form, bypass, input OTP, notifikasi hasil) dikendalikan
langsung via antarmuka chat Telegram.

Owner-Only: Khusus akun Telegram Owner (USER_ID: 7998819216).
"""

import json
import os
import random
import re
import string
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TOKEN_FILE = BASE_DIR / "telegram_token.txt"
OUT_FILE = BASE_DIR / "akun_gmail.txt"
SCREENSHOT_PATH = BASE_DIR / "debug_gmail_bot.png"

# Load Telegram Bot Token
DEFAULT_TOKEN = "8934049361:AAEG134iXICEZNFgprYJjCfT_oRAwFNMo9c"
if TOKEN_FILE.exists():
    BOT_TOKEN = TOKEN_FILE.read_text(encoding="utf-8").strip() or DEFAULT_TOKEN
else:
    BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", DEFAULT_TOKEN)

OWNER_ID = 7998819216
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"

# Default Virtual Display untuk Headless Server Linux (Xvfb :99)
if sys.platform.startswith("linux") and "DISPLAY" not in os.environ:
    os.environ["DISPLAY"] = ":99"

# ── Telegram API Helpers ─────────────────────────────────────────────

def telegram_api(method: str, data: dict | None = None, timeout: int = 35) -> dict:
    url = API_URL + method
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=body)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        return {"ok": False, "error": str(e)}


def send_message(chat_id: int, text: str, reply_markup: dict | None = None, parse_mode: str | None = "Markdown") -> dict:
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    res = telegram_api("sendMessage", payload)
    if not res.get("ok") and parse_mode:
        payload.pop("parse_mode", None)
        res = telegram_api("sendMessage", payload)
    return res


def edit_message(chat_id: int, message_id: int, text: str, reply_markup: dict | None = None, parse_mode: str | None = "Markdown") -> dict:
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    res = telegram_api("editMessageText", payload)
    if not res.get("ok") and "message is not modified" in str(res.get("error", "")).lower():
        return {"ok": True}
    if not res.get("ok") and parse_mode:
        payload.pop("parse_mode", None)
        res = telegram_api("editMessageText", payload)
    return res


def send_photo(chat_id: int, photo_path: Path, caption: str = "") -> bool:
    if not photo_path.exists():
        return False
    cmd = [
        "curl", "-s",
        "-F", f"chat_id={chat_id}",
        "-F", f"photo=@{photo_path.resolve()}",
    ]
    if caption:
        cmd.extend(["-F", f"caption={caption}"])
    cmd.append(f"{API_URL}sendPhoto")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return '"ok":true' in r.stdout.lower()
    except Exception:
        return False


def answer_callback(callback_query_id: str, text: str | None = None):
    payload: dict[str, str] = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    telegram_api("answerCallbackQuery", payload)


def main_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "⚡ Auto Daftar (Cukup No. HP)", "callback_data": "btn_auto"},
             {"text": "📝 Daftar Manual", "callback_data": "btn_manual"}],
            [{"text": "📋 Daftar Akun Tersimpan", "callback_data": "btn_list"},
             {"text": "ℹ️ Info Server & Status", "callback_data": "btn_status"}],
            [{"text": "🛑 Batalkan Sesi", "callback_data": "btn_cancel"}]
        ]
    }


# ── Generator Identitas Acak (Realistis Indonesia) ───────────────────

FIRST_NAMES = [
    "Aditya", "Bagas", "Bima", "Dimas", "Fajar", "Galih", "Hendra", "Ilham",
    "Kurnia", "Mahesa", "Naufal", "Pratama", "Raditya", "Satria", "Wahyu",
    "Yoga", "Annisa", "Cantika", "Dewi", "Eka", "Fitri", "Gita", "Indah",
    "Lestari", "Maya", "Nadia", "Putri", "Rani", "Sari", "Tiara", "Wulandari"
]

LAST_NAMES = [
    "Santoso", "Saputra", "Wijaya", "Kusuma", "Nugroho", "Hidayat", "Wibowo",
    "Setiawan", "Utomo", "Permana", "Firmansyah", "Ramadhan", "Gunawan", "Susanto"
]

def generate_random_identity(phone: str) -> dict:
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    suffix = "".join(random.choices(string.digits, k=3)) + random.choice(string.ascii_lowercase)
    username = f"{first.lower()}{last.lower()}{suffix}"
    
    # Password kuat: Huruf kapital, huruf kecil, angka, simbol
    pwd_stem = f"{first.capitalize()}{random.randint(100, 999)}"
    password = f"{pwd_stem}!#x"
    
    day = str(random.randint(1, 28))
    month = str(random.randint(1, 12))
    year = str(random.randint(1996, 2004))
    gender = random.choice(["male", "female"])
    
    return {
        "first": first,
        "last": last,
        "username": username,
        "password": password,
        "phone": phone,
        "day": day,
        "month": month,
        "year": year,
        "gender": gender
    }


# ── Active Session Manager ───────────────────────────────────────────

class SignupSession:
    def __init__(self, chat_id: int, account_data: dict, proxy: str | None = None):
        self.chat_id = chat_id
        self.data = account_data
        self.proxy = proxy
        self.status_msg_id = None
        self.otp_event = threading.Event()
        self.otp_code = None
        self.is_cancelled = False
        self.browser = None
        self.context = None
        self.page = None


CURRENT_SESSION: SignupSession | None = None
SESSION_LOCK = threading.Lock()
USER_STATE = {}  # chat_id -> state dict


def save_account_result(email: str, password: str, phone: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{email}|{password}|{phone}|{ts}\n"
    with open(OUT_FILE, "a", encoding="utf-8") as f:
        f.write(line)


# ── Browser Automation (Patchright Engine) ───────────────────────────

def human_type(page, el, text: str):
    el.click()
    time.sleep(random.uniform(0.15, 0.35))
    for ch in text:
        page.keyboard.type(ch)
        time.sleep(random.uniform(0.04, 0.18))
    time.sleep(random.uniform(0.3, 0.6))


def first_visible(page, selectors: list[str], timeout: int = 2500):
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=timeout):
                return loc
        except Exception:
            continue
    return None


def click_any(page, selectors: tuple = (), texts: tuple = ()) -> bool:
    loc = first_visible(page, list(selectors), timeout=1500)
    if loc:
        loc.click()
        time.sleep(random.uniform(0.5, 1.2))
        return True
    for t in texts:
        for sel in (
            f"button:has-text('{t}')",
            f"[role=button]:has-text('{t}')",
            f"div[role=button]:has-text('{t}')",
            f"a:has-text('{t}')",
        ):
            try:
                loc = page.locator(sel).first
                if loc.is_visible(timeout=1200):
                    loc.click()
                    time.sleep(random.uniform(0.5, 1.2))
                    return True
            except Exception:
                continue
    return False


def check_google_blocks(page):
    try:
        body = page.inner_text("body")[:3000].lower()
    except Exception:
        return
    for pat in (
        "browser or app may not be secure",
        "unusual traffic",
        "couldn't create your account",
        "browser atau aplikasi mungkin tidak aman",
        "lalu lintas yang tidak biasa",
        "tidak dapat membuat akun",
        "this page isn't available",
    ):
        if pat in body:
            raise RuntimeError(
                f"Google memblokir sesi ini (Risk Engine / WAF).\nIndikasi: '{pat}'.\n"
                "Saran: Gunakan koneksi seluler/residential proxy atau jeda beberapa saat."
            )


def update_progress(session: SignupSession, step: int, total: int, title: str, details: str = ""):
    txt = (
        f"🤖 *PROGRES PENDAFTARAN GMAIL*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 *Langkah [{step}/{total}]*: {title}\n"
    )
    if details:
        txt += f"ℹ️ _{details}_\n"
    txt += (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Target: `{session.data['username']}@gmail.com`\n"
        f"📱 No HP : `{session.data['phone']}`\n"
        f"⏳ Status : Sedang diproses oleh browser..."
    )
    if session.status_msg_id:
        edit_message(session.chat_id, session.status_msg_id, txt)
    else:
        res = send_message(session.chat_id, txt)
        if res.get("ok"):
            session.status_msg_id = res["result"]["message_id"]


def run_signup_worker(session: SignupSession):
    global CURRENT_SESSION
    from patchright.sync_api import sync_playwright

    chat_id = session.chat_id
    data = session.data
    total_steps = 7

    try:
        update_progress(session, 1, total_steps, "Inisialisasi Browser Anti-Deteksi", "Memuat Patchright Chromium Engine...")
        
        with sync_playwright() as p:
            # Gunakan mode visual virtual jika ada DISPLAY
            is_headless = "DISPLAY" not in os.environ
            session.browser = p.chromium.launch(
                headless=is_headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage"
                ]
            )
            
            ctx_kw = {
                "locale": "en-US",
                "viewport": {"width": 1366, "height": 900},
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            }
            if session.proxy:
                ctx_kw["proxy"] = {"server": session.proxy}
                
            session.context = session.browser.new_context(**ctx_kw)
            page = session.context.new_page()
            session.page = page

            if session.is_cancelled:
                return

            # [1/7] Buka Halaman
            update_progress(session, 1, total_steps, "Membuka Halaman Registrasi Google", "Menghubungkan ke accounts.google.com...")
            page.goto(
                "https://accounts.google.com/signup/v2/webcreateaccount?flowName=GlifWebSignIn&flowEntry=SignUp&hl=en",
                wait_until="domcontentloaded",
                timeout=45000
            )
            time.sleep(2)
            check_google_blocks(page)

            # Lewati recovery email jika muncul
            if page.locator("#recoveryEmailId").first.is_visible(timeout=2000):
                click_any(page, texts=("Skip", "Lewati"))
                time.sleep(1)

            if session.is_cancelled:
                return

            # [2/7] Isi Nama
            update_progress(session, 2, total_steps, "Mengisi Identitas Diri", f"Nama: {data['first']} {data['last']}")
            human_type(page, page.locator("#firstName").first, data["first"])
            human_type(page, page.locator("#lastName").first, data["last"])
            click_any(page, selectors=("#accountDetailsNext",), texts=("Next", "Berikutnya"))

            # [3/7] Isi Tanggal Lahir & Gender
            update_progress(session, 3, total_steps, "Mengisi Tanggal Lahir & Gender", f"TTL: {data['day']}/{data['month']}/{data['year']}")
            page.wait_for_selector("#day, input#day", timeout=20000)
            time.sleep(0.8)
            try:
                page.locator("#month").first.select_option(index=int(data["month"]))
            except Exception:
                human_type(page, page.locator("#month").first, data["month"])
            time.sleep(0.3)
            human_type(page, page.locator("#day").first, data["day"])
            human_type(page, page.locator("#year").first, data["year"])
            
            gval = {"male": "Male", "female": "Female"}.get(data["gender"].lower(), "Rather not say")
            try:
                page.locator("#gender").first.select_option(label=gval)
            except Exception:
                pass
            time.sleep(0.4)
            click_any(page, selectors=("#genderSelectionNext", "#next"), texts=("Next", "Berikutnya"))

            if session.is_cancelled:
                return

            # [4/7] Tentukan Username
            update_progress(session, 4, total_steps, "Menentukan Alamat Gmail", f"Username: {data['username']}@gmail.com")
            time.sleep(1.5)
            click_any(page, texts=("Create your own Gmail address", "Buat alamat Gmail sendiri"))
            time.sleep(0.6)
            
            if page.locator("#username").first.is_visible(timeout=4000):
                human_type(page, page.locator("#username").first, data["username"])
                click_any(page, selectors=("#next",), texts=("Next", "Berikutnya"))
                time.sleep(1.5)
                # Cek jika username sudah dipakai
                if page.locator("#username").first.is_visible(timeout=2500):
                    err = page.inner_text("body")[:400].lower()
                    if "taken" in err or "sudah dipakai" in err:
                        raise RuntimeError(f"Username '{data['username']}' sudah dipakai orang lain. Coba username lain.")
            else:
                fallback = first_visible(page, ["#username", "input[type=email]"], timeout=4000)
                if fallback:
                    human_type(page, fallback, data["username"])
                    click_any(page, selectors=("#next",), texts=("Next", "Berikutnya"))

            if session.is_cancelled:
                return

            # [5/7] Isi Password
            update_progress(session, 5, total_steps, "Mengamankan Kata Sandi", "Mengisi password...")
            page.wait_for_selector("#passwd", timeout=20000)
            human_type(page, page.locator("#passwd").first, data["password"])
            human_type(page, page.locator("#confirmPasswd").first, data["password"])
            click_any(page, selectors=("#create-password-next",), texts=("Next", "Berikutnya"))
            time.sleep(2)
            check_google_blocks(page)

            if session.is_cancelled:
                return

            # [6/7] Verifikasi Nomor HP & Tunggu OTP
            update_progress(session, 6, total_steps, "Verifikasi Nomor Telepon", f"Kirim SMS ke: {data['phone']}")
            if page.locator("#phoneNumberId").first.is_visible(timeout=15000):
                human_type(page, page.locator("#phoneNumberId").first, data["phone"])
                click_any(
                    page,
                    selectors=("#sendVerifyCodeButton", "#next"),
                    texts=("Get a verification code", "Dapatkan kode verifikasi", "Verify", "Verifikasi", "Next", "Berikutnya")
                )
                time.sleep(2.5)
                check_google_blocks(page)

                otp_el = first_visible(page, ["#code", "input[type=tel]"], timeout=20000)
                if not otp_el:
                    page.screenshot(path=str(SCREENSHOT_PATH))
                    raise RuntimeError("Kolom isian OTP tidak muncul pada formulir Google.")

                # Minta OTP ke Telegram
                otp_prompt = (
                    "📲 *KODE OTP GOOGLE DIBUTUHKAN!*\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"SMS verifikasi telah dikirim ke: `{data['phone']}`\n\n"
                    "👉 *Ketik dan balas chat ini langsung dengan 6 digit kode OTP!*\n"
                    "Contoh: `654321`\n\n"
                    "⏱️ _Waktu tunggu: 2 menit sebelum sesi kedaluwarsa._"
                )
                send_message(chat_id, otp_prompt)

                # Tunggu sinyal OTP dari handler Telegram
                got_otp = session.otp_event.wait(timeout=120)
                if not got_otp or not session.otp_code:
                    raise TimeoutError("Waktu pengisian OTP habis (120 detik tanpa respons).")

                if session.is_cancelled:
                    return

                update_progress(session, 6, total_steps, "Memverifikasi Kode OTP", f"Memasukkan kode: {session.otp_code}...")
                human_type(page, otp_el, session.otp_code)
                click_any(page, selectors=("#verifyCodeButton",), texts=("Verify", "Verifikasi", "Next", "Berikutnya"))
                time.sleep(3)
                check_google_blocks(page)
            else:
                update_progress(session, 6, total_steps, "Verifikasi Nomor Telepon", "Google tidak meminta verifikasi nomor (Lolos Cepat).")

            if session.is_cancelled:
                return

            # [7/7] Persetujuan Syarat & Privasi
            update_progress(session, 7, total_steps, "Menyetujui Ketentuan Layanan", "Menyelesaikan pendaftaran akun...")
            time.sleep(2)
            click_any(page, texts=("Yes, I'm in", "Ya, saya ikut"))
            time.sleep(1.5)
            click_any(page, texts=("Skip", "Lewati"))
            time.sleep(1.5)
            click_any(page, selectors=("#termAgree",), texts=("I agree", "Saya setuju"))
            time.sleep(4)
            check_google_blocks(page)

            # Cek Hasil Akhir
            url = page.url
            body = page.inner_text("body")[:800]
            page.screenshot(path=str(SCREENSHOT_PATH))

            is_success = ("myaccount.google.com" in url) or ("Welcome" in body) or ("Selamat datang" in body)
            full_email = f"{data['username']}@gmail.com"

            if is_success:
                save_account_result(full_email, data["password"], data["phone"])
                success_card = (
                    "🎉 *AKUN GMAIL BERHASIL DIBUAT!*\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📧 *Email*    : `{full_email}`\n"
                    f"🔑 *Password* : `{data['password']}`\n"
                    f"📱 *No. HP*   : `{data['phone']}`\n"
                    f"📅 *TTL*      : `{data['day']}-{data['month']}-{data['year']}`\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"💾 _Tersimpan permanen di akun_gmail.txt_"
                )
                send_message(chat_id, success_card, reply_markup=main_keyboard())
                send_photo(chat_id, SCREENSHOT_PATH, caption=f"Bukti akun aktif: {full_email}")
            else:
                save_account_result(f"{full_email} (cek manual)", data["password"], data["phone"])
                warn_msg = (
                    "⚠️ *STATUS BELUM DAPAT DIPASTIKAN*\n"
                    f"URL Terakhir: `{url}`\n"
                    "Tangkapan layar browser dikirimkan di bawah untuk verifikasi visual."
                )
                send_message(chat_id, warn_msg, reply_markup=main_keyboard())
                send_photo(chat_id, SCREENSHOT_PATH, caption="Tangkapan layar status pendaftaran")

    except Exception as e:
        err_msg = str(e)
        fail_card = (
            "❌ *PENDAFTARAN GAGAL*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ *Kendala*: {err_msg}\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "Silakan coba kembali atau ganti nomor HP / proxy."
        )
        send_message(chat_id, fail_card, reply_markup=main_keyboard())
        if session.page:
            try:
                session.page.screenshot(path=str(SCREENSHOT_PATH))
                send_photo(chat_id, SCREENSHOT_PATH, caption=f"Kondisi browser saat gagal: {err_msg[:100]}")
            except Exception:
                pass
    finally:
        with SESSION_LOCK:
            if session.browser:
                try:
                    session.browser.close()
                except Exception:
                    pass
            CURRENT_SESSION = None


# ── Telegram Message Handler ─────────────────────────────────────────

def handle_update(u: dict):
    global CURRENT_SESSION

    # 1. Callback Query (Tombol Inline)
    if "callback_query" in u:
        cb = u["callback_query"]
        answer_callback(cb["id"])
        chat_id = cb["message"]["chat"]["id"]
        from_id = cb["from"]["id"]
        data = cb.get("data", "")

        if from_id != OWNER_ID:
            send_message(chat_id, "⛔ *Akses Ditolak*. Bot ini bersifat privat untuk Owner.")
            return

        if data == "btn_auto":
            USER_STATE[chat_id] = {"state": "AWAIT_AUTO_PHONE"}
            msg = (
                "⚡ *MODE DAFTAR CEPAT (AUTO GENERATE)*\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "Nama, username, password, dan TTL akan dibuat secara otomatis.\n\n"
                "👉 *Masukkan nomor HP Anda* (wajib aktif untuk menerima SMS OTP):\n"
                "Contoh: `+6281234567890`"
            )
            send_message(chat_id, msg)

        elif data == "btn_manual":
            USER_STATE[chat_id] = {"state": "AWAIT_MANUAL_NAME"}
            msg = (
                "📝 *MODE DAFTAR MANUAL*\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "👉 *Masukkan Nama Depan dan Belakang* (dipisah spasi):\n"
                "Contoh: `Budi Santoso`"
            )
            send_message(chat_id, msg)

        elif data == "btn_list":
            if not OUT_FILE.exists():
                send_message(chat_id, "📋 Belum ada akun yang tersimpan di `akun_gmail.txt`.", reply_markup=main_keyboard())
                return
            lines = [l.strip() for l in OUT_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
            if not lines:
                send_message(chat_id, "📋 Berkas `akun_gmail.txt` masih kosong.", reply_markup=main_keyboard())
                return
            
            txt = f"📋 *DAFTAR AKUN TERSIMPAN ({len(lines)} Akun)*\n━━━━━━━━━━━━━━━━━━━━━━\n"
            for i, item in enumerate(lines[-15:], 1):  # 15 akun terakhir
                parts = item.split("|")
                email = parts[0]
                pw = parts[1] if len(parts) > 1 else "-"
                phone = parts[2] if len(parts) > 2 else "-"
                txt += f"{i}. `{email}` | `{pw}` | `{phone}`\n"
            txt += "━━━━━━━━━━━━━━━━━━━━━━"
            send_message(chat_id, txt, reply_markup=main_keyboard())

        elif data == "btn_status":
            disp = os.environ.get("DISPLAY", "None")
            active = "Sedang Mendaftar ⏳" if CURRENT_SESSION else "Siap / Idle 🟢"
            txt = (
                "ℹ️ *STATUS SISTEM BOT GMAIL*\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🤖 Status Engine : `{active}`\n"
                f"🖥️ Virtual Display: `{disp}`\n"
                f"🛠️ Driver        : `Patchright Chromium (Stealth)`\n"
                f"👑 Owner ID      : `{OWNER_ID}`\n"
                f"🕒 Server Time   : `{time.strftime('%Y-%m-%d %H:%M:%S')}`\n"
                "━━━━━━━━━━━━━━━━━━━━━━"
            )
            send_message(chat_id, txt, reply_markup=main_keyboard())

        elif data == "btn_cancel":
            with SESSION_LOCK:
                if CURRENT_SESSION:
                    CURRENT_SESSION.is_cancelled = True
                    CURRENT_SESSION.otp_event.set()
                    send_message(chat_id, "🛑 Sesi pendaftaran browser berhasil dibatalkan.")
                else:
                    send_message(chat_id, "ℹ️ Tidak ada sesi pendaftaran aktif yang sedang berjalan.")
            USER_STATE.pop(chat_id, None)
        return

    # 2. Pesan Teks
    msg = u.get("message", {})
    if "text" not in msg:
        return

    chat_id = msg["chat"]["id"]
    from_id = msg.get("from", {}).get("id")
    text = msg["text"].strip()

    if from_id != OWNER_ID:
        send_message(chat_id, "⛔ *Akses Ditolak*. Bot ini bersifat privat untuk Owner.")
        return

    # Cek jika ada sesi pendaftaran yang sedang MENUNGGU OTP
    with SESSION_LOCK:
        if CURRENT_SESSION and CURRENT_SESSION.chat_id == chat_id:
            # Jika user mengirimkan kode 6 angka
            clean_otp = text.replace("-", "").strip()
            if re.fullmatch(r"\d{6}", clean_otp):
                CURRENT_SESSION.otp_code = clean_otp
                CURRENT_SESSION.otp_event.set()
                send_message(chat_id, f"📥 Menerima kode OTP: `{clean_otp}`. Memasukkan ke Google...")
                return

    # Perintah Utama
    if text in ("/start", "/menu"):
        USER_STATE.pop(chat_id, None)
        welcome = (
            "🤖 *Selamat Datang di Gmail Signup Bot (Patchright)*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "Bot otomatisasi pembuatan akun Gmail menggunakan browser stealth Patchright.\n"
            "Dukungan bypass deteksi Google, simulasi ketikan manusia, dan verifikasi SMS langsung via Telegram.\n\n"
            "Silakan pilih menu aksi di bawah:"
        )
        send_message(chat_id, welcome, reply_markup=main_keyboard())
        return

    if text == "/batal":
        with SESSION_LOCK:
            if CURRENT_SESSION:
                CURRENT_SESSION.is_cancelled = True
                CURRENT_SESSION.otp_event.set()
                send_message(chat_id, "🛑 Sesi pendaftaran aktif berhasil dibatalkan.", reply_markup=main_keyboard())
            else:
                send_message(chat_id, "ℹ️ Tidak ada sesi yang sedang berjalan.", reply_markup=main_keyboard())
        USER_STATE.pop(chat_id, None)
        return

    if text.startswith("/auto"):
        parts = text.split(maxsplit=1)
        if len(parts) > 1 and re.search(r"\+?\d{8,15}", parts[1]):
            phone = parts[1].strip()
            start_auto_signup(chat_id, phone)
        else:
            USER_STATE[chat_id] = {"state": "AWAIT_AUTO_PHONE"}
            send_message(chat_id, "👉 *Ketik nomor HP yang akan didaftarkan* (contoh: `+6281234567890`):")
        return

    # State Machine Input User
    state_data = USER_STATE.get(chat_id, {})
    state = state_data.get("state")

    if state == "AWAIT_AUTO_PHONE":
        phone_match = re.search(r"(\+?\d{9,16})", text.replace(" ", "").replace("-", ""))
        if not phone_match:
            send_message(chat_id, "⚠️ Format nomor HP tidak valid. Harap gunakan format internasional (contoh: `+6281234567890`).")
            return
        phone = phone_match.group(1)
        if not phone.startswith("+"):
            if phone.startswith("08"):
                phone = "+628" + phone[2:]
            elif phone.startswith("62"):
                phone = "+" + phone
        USER_STATE.pop(chat_id, None)
        start_auto_signup(chat_id, phone)
        return

    # Mode Manual Wizard
    if state == "AWAIT_MANUAL_NAME":
        names = text.split(maxsplit=1)
        first = names[0].capitalize()
        last = names[1].capitalize() if len(names) > 1 else "Saputra"
        USER_STATE[chat_id] = {
            "state": "AWAIT_MANUAL_USER",
            "first": first,
            "last": last
        }
        send_message(chat_id, f"✅ Nama: *{first} {last}*\n\n👉 Sekarang masukkan *Username Gmail* yang diinginkan (tanpa @gmail.com):")
        return

    if state == "AWAIT_MANUAL_USER":
        u_name = text.replace("@gmail.com", "").strip().lower()
        USER_STATE[chat_id]["username"] = u_name
        USER_STATE[chat_id]["state"] = "AWAIT_MANUAL_PASS"
        send_message(chat_id, f"✅ Username: `{u_name}@gmail.com`\n\n👉 Masukkan *Password* akun:")
        return

    if state == "AWAIT_MANUAL_PASS":
        pwd = text.strip()
        if len(pwd) < 8:
            send_message(chat_id, "⚠️ Password minimal 8 karakter demi keamanan Google.")
            return
        USER_STATE[chat_id]["password"] = pwd
        USER_STATE[chat_id]["state"] = "AWAIT_MANUAL_PHONE"
        send_message(chat_id, "✅ Password tersimpan.\n\n👉 Masukkan *Nomor HP* (+62...):")
        return

    if state == "AWAIT_MANUAL_PHONE":
        phone = text.strip()
        if not phone.startswith("+") and phone.startswith("08"):
            phone = "+628" + phone[2:]
        data = USER_STATE[chat_id]
        data["phone"] = phone
        data["day"] = "15"
        data["month"] = "8"
        data["year"] = "2000"
        data["gender"] = "male"
        USER_STATE.pop(chat_id, None)
        launch_registration(chat_id, data)
        return

    # Fallback jika chat bebas
    send_message(chat_id, "Perintah tidak dikenali. Ketik /menu untuk membuka daftar pilihan.", reply_markup=main_keyboard())


def start_auto_signup(chat_id: int, phone: str):
    data = generate_random_identity(phone)
    preview = (
        "⚡ *MEMULAI AUTO REGISTRASI GMAIL*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *Nama*     : {data['first']} {data['last']}\n"
        f"📧 *Username* : `{data['username']}@gmail.com`\n"
        f"🔑 *Password* : `{data['password']}`\n"
        f"📱 *No. HP*   : `{data['phone']}`\n"
        f"📅 *TTL*      : `{data['day']}-{data['month']}-{data['year']}`\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🚀 _Meluncurkan browser Patchright..._"
    )
    send_message(chat_id, preview)
    launch_registration(chat_id, data)


def launch_registration(chat_id: int, account_data: dict, proxy: str | None = None):
    global CURRENT_SESSION
    with SESSION_LOCK:
        if CURRENT_SESSION:
            send_message(chat_id, "⚠️ Masih ada proses pendaftaran akun lain yang aktif. Selesaikan atau ketik /batal terlebih dahulu.")
            return
        CURRENT_SESSION = SignupSession(chat_id, account_data, proxy)
    
    t = threading.Thread(target=run_signup_worker, args=(CURRENT_SESSION,), daemon=True)
    t.start()


# ── Bot Main Runner ──────────────────────────────────────────────────

def main():
    print("=" * 60)
    print(" ⚡ GMAIL SIGNUP TELEGRAM BOT (PATCHRIGHT ENGINE)")
    print(f" 👑 Target Owner ID: {OWNER_ID}")
    print("=" * 60)

    # Validasi Koneksi Token
    me = telegram_api("getMe")
    if not me.get("ok"):
        print(f"[-] Gagal terhubung ke Telegram API dengan token: {me.get('error')}")
        sys.exit(1)

    bot_user = me["result"]["username"]
    print(f"[✓] Bot online dan siap menerima perintah: @{bot_user}")

    last_offset = 0
    while True:
        try:
            updates = telegram_api("getUpdates", {"offset": last_offset, "timeout": 30}, timeout=40)
            for u in updates.get("result", []):
                last_offset = u["update_id"] + 1
                try:
                    handle_update(u)
                except Exception as e:
                    print(f"[-] Error menangani update: {e}")
        except Exception as e:
            print(f"[!] Network polling error: {e}")
            time.sleep(3)


if __name__ == "__main__":
    main()
