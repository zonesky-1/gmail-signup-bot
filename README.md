# 📧 Gmail Signup Bot & Telegram Control (Patchright Automation)

Bot otomatisasi pendaftaran akun Gmail via browser menggunakan **Patchright** (Playwright stealth fork) dengan simulasi pengetikan manusia (*human typing*), penanganan alur registrasi Google modern, dan bypass deteksi otomasi. Tersedia dalam mode **Telegram Bot** interaktif dan **CLI Terminal**.

---

## 🚀 Fitur Utama

- **Telegram Bot Control (`gmail_telegram_bot.py`):**
  - Kendalikan pendaftaran langsung dari Telegram (menu inline, status live per tahap).
  - Mode **⚡ Auto Generate (`/auto <no_hp>`)**: Otomatis generate identitas nama Indonesia, username, password kuat, dan TTL acak.
  - Verifikasi OTP interaktif via chat Telegram (cukup balas chat dengan 6 angka OTP).
  - Bukti screenshot aktivasi akun (`debug_gmail_bot.png`) dikirim langsung ke chat Telegram.
  - Owner-Only Protection (terkunci khusus Telegram ID Owner: `7998819216`).
- **CLI Terminal Runner (`gmail_signup_bot.py`):** Mode terminal interaktif lokal.
- **Human-like Typing & Delay:** Pengetikan karakter dengan jeda acak (*jitter*) untuk menghindari deteksi heuristik anti-bot Google.
- **Smart Form Navigator:** Otomatis mendeteksi dan mengisi form nama, tanggal lahir, gender, pemilihan alamat Gmail (*custom address*), serta password.
- **Fail-safe Risk Detection:** Otomatis mendeteksi pemblokiran dini Google (*unusual traffic* / *browser or app may not be secure*) dan menyimpan screenshot untuk analisis.
- **Auto-export Hasil:** Menyimpan akun yang berhasil dibuat ke dalam `akun_gmail.txt` dengan format `email|password|phone|timestamp`.

---

## 📦 Instalasi

1. **Clone Repositori:**
   ```bash
   git clone https://github.com/zonesky-1/gmail-signup-bot.git
   cd gmail-signup-bot
   ```

2. **Pasang Dependensi:**
   ```bash
   pip install -r requirements.txt
   patchright install chromium
   ```

---

## 🛠️ Penggunaan

### 1. Mode Bot Telegram (Rekomendasi)
Simpan bot token Anda di `telegram_token.txt` atau ekspor environment variable `TELEGRAM_BOT_TOKEN`, lalu jalankan:
```bash
python gmail_telegram_bot.py
```
Perintah di Telegram:
* `/start` atau `/menu` — Membuka panel tombol interaktif.
* `/auto +6281234567890` — Mulai pendaftaran instan (identitas otomatis).
* `/daftar` — Panduan pendaftaran manual bertahap.
* `/list` — Melihat daftar akun yang tersimpan.
* `/batal` — Membatalkan sesi pendaftaran aktif dan menutup browser.

### 2. Mode Terminal (CLI)
```bash
python gmail_signup_bot.py
```
Opsional:
```bash
python gmail_signup_bot.py --proxy http://user:pass@host:port
```

---

## 📄 Format Output (`akun_gmail.txt`)

Akun yang berhasil dibuat otomatis ditambahkan ke berkas `akun_gmail.txt`:
```text
username@gmail.com|Password123!|+6281234567890|2026-10-16 20:15:00
```

---

## ⚠️ Catatan Keamanan & Praktik Terbaik

- **Reputasi IP:** Gunakan jaringan seluler (*tethering* HP) atau rotating residential proxy untuk menghindari trigger blokir Google.
- **Display Server:** Di lingkungan Linux/VPS tanpa monitor, pastikan `Xvfb` aktif (misal `export DISPLAY=:99`) agar browser berjalan dalam mode visual virtual tanpa memicu deteksi headless Google.
