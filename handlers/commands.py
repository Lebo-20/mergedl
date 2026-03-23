import os
import shutil
import asyncio
import sys
from pyrogram import Client, filters
from config import DOWNLOAD_DIR
from utils.tools import merge_videos, upload_to_git

@Client.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message):
    await message.reply_text(
        f"Halo {message.from_user.first_name}! 👋\n\n"
        "Saya adalah Bot Video Merger Performa Tinggi.\n"
        "Kirimkan saya beberapa video, lalu gunakan /merge untuk menggabungkannya.\n\n"
        "🔧 **Perintah Tersedia:**\n"
        "/merge - Mulai menggabungkan video\n"
        "/clear - Hapus semua video sesi Anda\n"
        "/update - Perbarui bot ke versi terbaru"
    )

@Client.on_message(filters.command("clear") & filters.private)
async def clear_cmd(client, message):
    user_id = message.from_user.id
    user_path = os.path.abspath(os.path.join(DOWNLOAD_DIR, str(user_id)))
    if os.path.exists(user_path):
        shutil.rmtree(user_path)
    await message.reply_text("✅ Sesi Anda telah dihapus.")

@Client.on_message(filters.command("merge") & filters.private)
async def merge_cmd(client, message):
    user_id = message.from_user.id
    user_path = os.path.abspath(os.path.join(DOWNLOAD_DIR, str(user_id)))
    
    if not os.path.exists(user_path) or not os.listdir(user_path):
        await message.reply_text("❌ Tidak ada video untuk digabung. Silakan kirim video terlebih dahulu.")
        return
        
    status = await message.reply_text("⏳ Menggabungkan video... Harap tunggu.")
    
    output_file = f"merged_{user_id}.mp4"
    output_path = os.path.join(user_path, output_file)
    
    try:
        await merge_videos(user_path, output_path)
        
        await status.edit("📤 Mengirim hasil gabungan ke Anda...")
        
        # Upload video with progress
        await client.send_video(
            chat_id=message.chat.id,
            video=output_path,
            caption="✅ File berhasil digabungkan!",
            supports_streaming=True
        )
        
        # Optional: upload dummy to git for requirement
        await status.edit("📤 Mengupload ke GitHub...")
        await upload_to_git(output_path)
        
        await status.delete()
        # Auto cleanup
        shutil.rmtree(user_path)
        
    except Exception as e:
        await status.edit(f"❌ Terjadi kesalahan: {str(e)}")

@Client.on_message(filters.command("update") & filters.private)
async def update_cmd(client, message):
    from config import OWNER_ID
    if message.from_user.id != OWNER_ID:
        await message.reply_text("❌ Anda tidak memiliki izin untuk menggunakan perintah ini.")
        return
        
    msg = await message.reply_text("🌀 Memeriksa pembaruan...")
    try:
        process = await asyncio.create_subprocess_exec(
            "git", "pull",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            await msg.edit("✅ Sistem diperbarui. Me-restart bot...")
            os.execl(sys.executable, sys.executable, *sys.argv)
        else:
            await msg.edit(f"❌ Gagal memperbarui: {stderr.decode()}")
    except Exception as e:
        await msg.edit(f"❌ Error: {str(e)}")
