import os
import shutil
import asyncio
import sys
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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
        
    await message.reply_text(
        "Pilih metode Merge:",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Tanpa Watermark (Cepat)", callback_data="merge_no"),
                InlineKeyboardButton("Pakai Watermark (Lambat)", callback_data="merge_yes")
            ]
        ])
    )

@Client.on_callback_query(filters.regex("^merge_"))
async def merge_callback(client, callback_query):
    user_id = callback_query.from_user.id
    user_path = os.path.abspath(os.path.join(DOWNLOAD_DIR, str(user_id)))
    use_watermark = callback_query.data == "merge_yes"
    
    await callback_query.message.delete()
    status = await client.send_message(user_id, "⏳ Menggabungkan video... Harap tunggu.")
    
    output_file = f"merged_{user_id}.mp4"
    output_path = os.path.join(user_path, output_file)
    
    try:
        await merge_videos(user_path, output_path, use_watermark=use_watermark)
        
        await status.edit("📤 Mengirim hasil gabungan ke Anda...")
        
        caption = "✅ File berhasil digabungkan!"
        if use_watermark:
            caption += "\n(Metode: Dengan Watermark)"
        else:
            caption += "\n(Metode: Copy/Tanpa Re-encode)"

        # Upload video
        await client.send_video(
            chat_id=user_id,
            video=output_path,
            caption=caption,
            supports_streaming=True
        )
        
        # Optional: upload to git
        await status.edit("📤 Mengupload ke GitHub...")
        await upload_to_git(output_path)
        
        await status.delete()
        # Auto cleanup
        if os.path.exists(user_path):
            shutil.rmtree(user_path)
        
    except Exception as e:
        error_text = f"❌ Terjadi kesalahan: {str(e)}"
        if status:
            await status.edit(error_text)
        else:
            await client.send_message(user_id, error_text)
            
    finally:
        # Auto cleanup files ALWAYS (success or fail)
        if os.path.exists(user_path):
            try:
                shutil.rmtree(user_path)
            except:
                pass
        
        # Clear status tracking from video handler (if module is loaded)
        try:
            from handlers.video import status_msgs
            if user_id in status_msgs:
                del status_msgs[user_id]
        except:
            pass

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
