# 🚀 Telegram Video Merger Bot - Deploy Guide

Bot ini sudah dioptimasi untuk kecepatan tinggi menggunakan Pyrogram, FFmpeg (concat mode), dan aria2c.

## 🛠️ Persiapan Awal
1. **Dapatkan Bot Token** dari [@BotFather](https://t.me/BotFather).
2. **Setup Server** (VPS Linux disarankan, Ubuntu 20.04+).

## 📦 Instalasi
Jalankan perintah berikut di VPS Anda:
```bash
git clone https://github.com/Lebo-20/mergedl.git
cd mergedl
chmod +x setup.sh
./setup.sh
```

## ⚙️ Konfigurasi
Edit file `config.py` dan masukkan bot token Anda:
```python
BOT_TOKEN = "TOKEN_ANDA_DISINI"
```

## 🚀 Menjalankan Bot

### Opsi 1: Menggunakan Screen (Paling Mudah)
Agar bot tetap berjalan saat Anda keluar dari terminal:
```bash
screen -S mergerbot
python3 main.py
# Tekan CTRL+A lalu D untuk keluar (detach)
# Ketik 'screen -r mergerbot' untuk masuk kembali
```

### Opsi 2: Menggunakan Systemd (Profesional)
Buat file service:
```bash
sudo nano /etc/systemd/system/mergerbot.service
```
Isi dengan:
```ini
[Unit]
Description=Telegram Video Merger Bot
After=network.target

[Service]
User=root
WorkingDirectory=/root/mergedl
ExecStart=/usr/bin/python3 main.py
Restart=always

[Install]
WantedBy=multi-user.target
```
Jalankan service:
```bash
sudo systemctl enable mergerbot
sudo systemctl start mergerbot
```

## 🔧 Fitur
- **Merge Tanpa Re-encode:** Sangat cepat dan tidak mengurangi kualitas.
- **Support File Besar:** Mendukung video hingga 2GB+.
- **Penanganan Multi-User:** Setiap user memiliki folder download sendiri.
- **Auto-Sort:** Mengurutkan file berdasarkan angka di nama file secara otomatis.
