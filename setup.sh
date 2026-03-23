#!/bin/bash

# Update and Install FFmpeg & aria2
sudo apt update && sudo apt upgrade -y
sudo apt install -y ffmpeg aria2 git screen python3-pip

# Install Python requirements
pip3 install -r requirements.txt

echo "✅ Instalasi selesai! Jalankan Bot dengan: python3 main.py"
