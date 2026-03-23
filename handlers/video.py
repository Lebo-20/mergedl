import os
import time
from pyrogram import Client, filters
from config import DOWNLOAD_DIR
from utils.tools import progress_for_pyrogram

@Client.on_message((filters.video | filters.document) & filters.private)
async def video_handler(client, message):
    user_id = message.from_user.id
    user_path = os.path.join(DOWNLOAD_DIR, str(user_id))
    
    if not os.path.exists(user_path):
        os.makedirs(user_path)
        
    # Check if doc is video
    if message.document:
        if not message.document.mime_type.startswith("video/"):
            return # Ignore non-video documents

    msg = await message.reply_text("📥 Menyiapkan download...", quote=True)
    start_time = time.time()
    
    file_name = message.video.file_name if message.video else message.document.file_name
    if not file_name:
        file_name = f"video_{int(time.time())}.mp4"
        
    file_path = os.path.join(user_path, file_name)
    
    try:
        await client.download_media(
            message=message,
            file_name=file_path,
            progress=progress_for_pyrogram,
            progress_args=("⬇️ Mendownload...", msg, start_time)
        )
        await msg.edit("✅ Berhasil disimpan! Kirim video lainnya atau ketik /merge.")
    except Exception as e:
        await msg.edit(f"❌ Gagal mendownload: {str(e)}")
