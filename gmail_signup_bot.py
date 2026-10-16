#!/usr/bin/env python3
"""
gmail_signup_bot.py — Bot pendaftaran akun Gmail otomatis (web signup).
Lo tinggal input: nama, username, password, nomor HP. Bot yang urus semua form.
Step OTP: bot minta lo tempel kode 6 digit dari HP lo ke terminal.

Cara pakai:
  pip install patchright
  patchright install chromium
  python gmail_signup_bot.py

Opsional:
  python gmail_signup_bot.py --proxy http://user:pass@host:port
  python gmail_signup_bot.py --headless   (TIDAK disarankan — Google gampang blokir)
"""
import argparse
import os
import random
import re
import sys
import time

from patchright.sync_api import sync_playwright

OUT_FILE = "akun_gmail.txt"

# ── util ──────────────────────────────────────────────────────────────

def sleep(a=0.6, b=1.8):
    time.sleep(random.uniform(a, b))


def human_type(page, el, text):
    """Ketik per-karakter dengan jeda manusiawi."""
    el.click()
    sleep(0.2, 0.5)
    for ch in text:
        page.keyboard.type(ch)
        time.sleep(random.uniform(0.04, 0.20))
    sleep()


def first_visible(page, selectors, timeout=2500):
    """Coba beberapa selector; return Locator pertama yang kelihatan."""
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=timeout):
                return loc
        except Exception:
            continue
    return None


def click_any(page, selectors=(), texts=()):
    """Klik elemen tombol via selector CSS atau teks (EN + ID fallback)."""
    loc = first_visible(page, selectors, timeout=1500)
    if loc:
        loc.click()
        sleep()
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
                    sleep()
                    return True
            except Exception:
                continue
    return False


def fail_if_blocked(page):
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
                "GOOGLE NGE-BLOK sesi ini (risk engine). "
                "Solusi: jalankan dari jaringan rumah/HP (bukan datacenter/VPN), "
                "pakai --proxy resi kalau ada, atau jeda beberapa jam."
            )


def append_account(email, pw, phone):
    with open(OUT_FILE, "a") as f:
        f.write(f"{email}|{pw}|{phone}\n")
    print(f"[💾] Tersimpan ke {OUT_FILE}: {email}")


# ── alur signup 1 akun ────────────────────────────────────────────────

def create_one(browser, proxy=None):
    ctx_kw = {"locale": "en-US", "viewport": {"width": 1366, "height": 900}}
    if proxy:
        ctx_kw["proxy"] = {"server": proxy}
    ctx = browser.new_context(**ctx_kw)
    page = ctx.new_page()

    # input user
    first = input("Nama depan           : ").strip()
    last = input("Nama belakang        : ").strip()
    username = input("Username Gmail (tanpa @gmail.com): ").strip().replace("@gmail.com", "")
    password = input("Password             : ").strip()
    phone = input("Nomor HP (dgn kode negara, contoh +62812xxx): ").strip()
    if not all([first, last, username, password, phone]):
        print("[!] Ada input kosong, batal.")
        return False

    day = input("Tanggal lahir (DD)   : ").strip()
    month = input("Bulan lahir (MM angka): ").strip()
    year = input("Tahun lahir (YYYY)   : ").strip()
    gender = input("Gender (male/female/rather_not_say): ").strip() or "rather_not_say"

    print("\n[1/8] Buka halaman signup Google ...")
    page.goto(
        "https://accounts.google.com/signup/v2/webcreateaccount"
        "?flowName=GlifWebSignIn&flowEntry=SignUp&hl=en",
        wait_until="domcontentloaded", timeout=45000,
    )
    sleep(2, 3)
    fail_if_blocked(page)

    # halaman pemulihan mungkin muncul duluan
    if page.locator("#recoveryEmailId").first.is_visible(timeout=2000):
        print("      Halaman recovery email → Skip.")
        click_any(page, texts=("Skip", "Lewati"))
        sleep(1, 2)

    print("[2/8] Isi nama ...")
    human_type(page, page.locator("#firstName").first, first)
    human_type(page, page.locator("#lastName").first, last)
    click_any(page, selectors=("#accountDetailsNext",), texts=("Next", "Berikutnya"))

    print("[3/8] Isi tanggal lahir + gender ...")
    page.wait_for_selector("#day, input#day", timeout=20000)
    sleep(1)
    try:
        page.locator("#month").first.select_option(index=int(month))
    except Exception:
        human_type(page, page.locator("#month").first, month)
    sleep(0.4)
    human_type(page, page.locator("#day").first, day)
    human_type(page, page.locator("#year").first, year)
    gval = {"male": "Male", "female": "Female"}.get(gender.lower(), "Rather not say")
    try:
        page.locator("#gender").first.select_option(label=gval)
    except Exception:
        pass
    sleep(0.4)
    click_any(page, selectors=("#genderSelectionNext", "#next"), texts=("Next", "Berikutnya"))

    print("[4/8] Pilih username ...")
    # Google sering nawarin daftar saran dulu → pilih "Create your own"
    sleep(1.5)
    own = click_any(page, texts=("Create your own Gmail address", "Buat alamat Gmail sendiri"))
    sleep(0.6)
    if page.locator("#username").first.is_visible(timeout=4000):
        human_type(page, page.locator("#username").first, username)
        click_any(page, selectors=("#next",), texts=("Next", "Berikutnya"))
        sleep(1.5)
        # kalau username dipakai, Google balik lagi ke step ini
        if page.locator("#username").first.is_visible(timeout=2500):
            err = page.inner_text("body")[:400]
            if "taken" in err.lower() or "sudah dipakai" in err.lower():
                print("[!] Username sudah dipakai orang. Batal — coba lagi dgn username lain.")
                return False
    else:
        # tampilan lama: input field username biasa
        fallback = first_visible(page, ["#username", "input[type=email]"], timeout=4000)
        if fallback:
            human_type(page, fallback, username)
            click_any(page, selectors=("#next",), texts=("Next", "Berikutnya"))

    print("[5/8] Isi password ...")
    page.wait_for_selector("#passwd", timeout=20000)
    human_type(page, page.locator("#passwd").first, password)
    human_type(page, page.locator("#confirmPasswd").first, password)
    click_any(page, selectors=("#create-password-next",), texts=("Next", "Berikutnya"))

    print("[6/8] Verifikasi nomor HP ...")
    # kadang ada halaman "Add phone recovery" dulu → isi juga (aman utk akun sendiri)
    if page.locator("#phoneNumberId").first.is_visible(timeout=15000):
        human_type(page, page.locator("#phoneNumberId").first, phone)
        clicked = click_any(
            page,
            selectors=("#sendVerifyCodeButton", "#next"),
            texts=("Get a verification code", "Dapatkan kode verifikasi", "Verify", "Verifikasi", "Next", "Berikutnya"),
        )
        sleep(2, 3)
        fail_if_blocked(page)
        # input OTP
        otp_el = first_visible(page, ["#code", "input[type=tel]"], timeout=20000)
        if otp_el is None:
            print("[!] Field OTP tidak muncul — screenshot disimpan utk diagnosa.")
            page.screenshot(path="debug_gmail_bot.png")
            return False
        otp = ""
        while not re.fullmatch(r"\d{6}", otp):
            otp = input(">>> Kode OTP dari HP lo (6 digit): ").strip()
        human_type(page, otp_el, otp)
        click_any(page, selectors=("#verifyCodeButton",), texts=("Verify", "Verifikasi", "Next", "Berikutnya"))
        sleep(2, 3)
    else:
        print("      Google tidak minta verifikasi HP di flow ini — lanjut.")

    print("[7/8] Setuju ToS ...")
    sleep(2)
    click_any(page, texts=("Yes, I'm in", "Ya, saya ikut"))
    sleep(1.5)
    click_any(page, texts=("Skip", "Lewati"))   # optional recovery screen
    sleep(1.5)
    click_any(page, selectors=("#termAgree",), texts=("I agree", "Saya setuju"))
    sleep(3, 4)
    fail_if_blocked(page)

    print("[8/8] Cek hasil ...")
    url = page.url
    try:
        body = page.inner_text("body")[:600]
    except Exception:
        body = ""
    ok = ("myaccount.google.com" in url) or ("Welcome" in body) or ("Selamat datang" in body)
    page.screenshot(path="debug_gmail_bot.png")
    ctx.close()

    if ok:
        email = f"{username}@gmail.com"
        print(f"\n[✅] AKUN BERHASIL DIBUAT: {email}")
        append_account(email, password, phone)
        return True

    print(f"\n[⚠️] Belum pasti berhasil (URL: {url}). Cek screenshot debug_gmail_bot.png")
    append_account(f"{username}@gmail.com (cek manual)", password, phone)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proxy", help="opsional: http://user:pass@host:port")
    ap.add_argument("--headless", action="store_true", help="TIDAK disarankan utk Google")
    args = ap.parse_args()

    print("=" * 56)
    print(" GMAIL SIGNUP BOT — input manual, bot yang daftarin")
    print(" File hasil:", OUT_FILE)
    print("=" * 56)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=args.headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            while True:
                try:
                    create_one(browser, proxy=args.proxy)
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    print(f"[!] Gagal: {e}")
                    try:
                        browser.close()
                    except Exception:
                        pass
                    browser = p.chromium.launch(
                        headless=args.headless,
                        args=["--disable-blink-features=AutomationControlled"],
                    )
                again = input("\nBuat akun lagi? (y/n): ").strip().lower()
                if again != "y":
                    break
        finally:
            try:
                browser.close()
            except Exception:
                pass
    print("Selesai.")


if __name__ == "__main__":
    main()
