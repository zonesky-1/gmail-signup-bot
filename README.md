# 📧 Gmail Creator Pro (GlifWebSignIn 2026 Engine)

Automated Gmail account creation engine powered by **Patchright Stealth** & **QR-Link Mobile Verification Checkpoint Bypass**.

---

## 🚀 Fitur Unggulan

- **Gateway YouTube Mobile via Facebook IAB Referrer:**  
  Membuka alur registrasi Google via trust-context (`https://m.youtube.com/@YKXXXXC` & referrer `https://l.facebook.com/`), meminimalkan deteksi anti-bot Google.
- **Dynamic DOM Handling:**  
  Navigasi keyboard untuk komponen dinamis **Google Material Combobox** (Tanggal Lahir, Bulan, dan Gender).
- **Auto-Select Radio Rekomendasi:**  
  Otomatis memilih saran alamat Gmail pertama dari Google untuk menghindari bentrok nama pengguna (*username taken*).
- **Mobile Checkpoint Verification (QR-Link Bypass):**  
  - Ekstraksi gambar Base64 QR Code dari checkpoint verifikasi Google.
  - Decoding langsung ke URL web verifikasi menggunakan `zbarimg`.
  - Mengirim link verifikasi & tangkapan layar langsung ke Telegram Operator secara *real-time*.
- **Auto-Listener & Post-Verification Handling:**  
  - Mendeteksi perpindahan URL saat verifikasi diselesaikan dari ponsel operator.
  - Otomatis melewati konfigurasi nomor pemulihan (*Skip Recovery*).
  - Otomatis menyetujui *Terms of Service* (ToS).
- **Penyimpanan Hasil:**  
  Menyimpan akun aktif ke berkas `akun_gmail.txt` dan mengirim notifikasi sukses ke Telegram.

---

## 📦 Kebutuhan Sistem & Dependensi

1. **Paket Sistem Linux:**
   ```bash
   sudo apt-get install -y xvfb zbar-tools
   ```

2. **Paket Python:**
   ```bash
   pip install patchright
   patchright install chromium
   ```

---

## 🛠️ Cara Menjalankan

1. **Jalankan Xvfb Virtual Display (jika di VPS headless):**
   ```bash
   Xvfb :99 -screen 0 1366x768x24 &
   export DISPLAY=:99
   ```

2. **Jalankan Script:**
   ```bash
   python3 gmail_creator_pro.py
   ```

3. **Alur di Telegram:**
   - Script akan memulai registrasi profil acak.
   - Jika Google meminta verifikasi perangkat seluler, link verifikasi dan foto QR code akan langsung dikirimkan ke Telegram Anda.
   - Buka link tersebut di ponsel (disarankan mode incognito), selesaikan konfirmasi SMS di HP.
   - Server otomatis mendeteksi keberhasilan verifikasi dan menyelesaikan akun hingga selesai.

---

## 📄 Format Output (`akun_gmail.txt`)

Akun yang sukses otomatis tersimpan dengan format:
```text
email@gmail.com|PasswordKuat123!|2026-10-17 15:30:00
```
