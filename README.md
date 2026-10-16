# 📧 Gmail Signup Bot (Patchright Automation)

Bot otomatisasi pendaftaran akun Gmail via browser menggunakan **Patchright** (Playwright stealth fork) dengan simulasi pengetikan manusia (*human typing*), penanganan alur registrasi Google modern, dan bypass deteksi otomasi.

---

## 🚀 Fitur Utama

- **Human-like Typing & Delay:** Pengetikan karakter dengan jeda acak (*jitter*) untuk menghindari deteksi heuristik anti-bot Google.
- **Smart Form Navigator:** Otomatis mendeteksi dan mengisi form nama, tanggal lahir, gender, pemilihan alamat Gmail (*custom address*), serta password.
- **Interactive OTP Handling:** Mendukung verifikasi nomor HP dan input OTP langsung via prompt terminal.
- **Fail-safe Risk Detection:** Otomatis mendeteksi pemblokiran dini Google (*unusual traffic* / *browser or app may not be secure*) dan menyimpan screenshot (`debug_gmail_bot.png`) untuk analisis.
- **Auto-export Hasil:** Menyimpan akun yang berhasil dibuat ke dalam `akun_gmail.txt` dengan format `email|password|phone`.
- **Proxy Support:** Mendukung HTTP/SOCKS5 proxy per sesi.

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

### 1. Menjalankan Mode Standar (Visible Browser - Sangat Disarankan)
```bash
python gmail_signup_bot.py
```
> *Catatan:* Google sangat sensitif terhadap headless browser. Menjalankan dalam mode visible dengan IP residensial/koneksi HP memberikan tingkat keberhasilan tertinggi.

### 2. Menjalankan dengan Proxy
```bash
python gmail_signup_bot.py --proxy http://user:pass@host:port
```

### 3. Mode Headless (Hanya untuk Testing / VPS Ber-display Virtual)
```bash
python gmail_signup_bot.py --headless
```

---

## 📄 Format Output (`akun_gmail.txt`)

Akun yang berhasil dibuat otomatis ditambahkan ke berkas `akun_gmail.txt`:
```text
username@gmail.com|Password123!|+6281234567890
```

---

## ⚠️ Catatan Keamanan & Praktik Terbaik

- **Reputasi IP:** Gunakan jaringan seluler (*tethering* HP) atau rotating residential proxy untuk menghindari trigger blokir Google.
- **Nomor Telepon:** Gunakan nomor telepon aktif untuk verifikasi OTP saat diminta.
- Simpan berkas hasil dan kredensial secara aman. Repositori ini otomatis mengabaikan file `akun_gmail.txt` via `.gitignore`.
