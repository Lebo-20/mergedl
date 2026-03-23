import os
import time
from pyrogram import Client, filters
from config import DOWNLOAD_DIR
from utils.tools import progress_for_pyrogram

# Store status message IDs to avoid spamming
status_msgs = {}

@Client.on_message((filters.video | filters.document) & filters.private)
async def video_handler(client, message):
    user_id = message.from_user.id
    user_path = os.path.abspath(os.path.join(DOWNLOAD_DIR, str(user_id)))
    
    if not os.path.exists(user_path):
        os.makedirs(user_path)
        
    # Check if doc is video
    if message.document:
        if not (message.document.mime_type and message.document.mime_type.startswith("video/")):
            return # Ignore non-video documents

    # Initial status
    status_msg = await message.reply_text("📥 Menyiapkan download...", quote=True)
    start_time = time.time()
    
    file_name = (message.video.file_name if message.video else message.document.file_name) or f"video_{int(time.time())}.mp4"
    file_path = os.path.join(user_path, file_name)
    
    try:
        await client.download_media(
            message=message,
            file_name=file_path,
            progress=progress_for_pyrogram,
            progress_args=("⬇️ Mendownload...", status_msg, start_time)
        )
        
        # Count files
        count = len([f for f in os.listdir(user_path) if f.lower().endswith(('.mp4', '.mkv', '.mov', '.avi'))])
        
        status_text = f"✅ **Berhasil disimpan!**\n📂 Total dalam antrean: `{count}` file\n\nKetik /merge jika sudah selesai."
        
        # Check if we should edit the PREVIOUS global status message or the CURRENT one
        if user_id in status_msgs:
            try:
                # Delete current and edit the old one to keep it at the bottom
                await status_msg.delete()
                await client.edit_message_text(user_id, status_msgs[user_id], status_text)
            except:
                # If editing old fails (e.g. deleted), send new
                status_msgs[user_id] = status_msg.id
                await status_msg.edit(status_text)
        else:
            status_msgs[user_id] = status_msg.id
            await status_msg.edit(status_text)
            
    except Exception as e:
        await status_msg.edit(f"❌ Gagal mendownload: {str(e)}")
