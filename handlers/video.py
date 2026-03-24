import os
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import DOWNLOAD_DIR
from utils.tools import progress_for_pyrogram

# Store status message IDs to avoid spamming
status_msgs = {}

# Store state for renaming
rename_states = {}

@Client.on_message((filters.video | filters.document) & filters.private)
async def video_handler(client, message):
    user_id = message.from_user.id
    user_path = os.path.abspath(os.path.join(DOWNLOAD_DIR, str(user_id)))
    
    if not os.path.exists(user_path):
        os.makedirs(user_path)
        
    # Check if doc is video
    if message.document:
        if not (message.document.mime_type and message.document.mime_type.startswith("video/")):
            message.continue_propagation()
            return # Ignore non-video documents

    # Initial status
    status_msg = await message.reply_text("📥 Menyiapkan download...", quote=True)
    start_time = time.time()
    
    orig_file_name = (message.video.file_name if message.video else message.document.file_name) or f"video_{int(time.time())}.mp4"
    file_path = os.path.join(user_path, orig_file_name)
    
    try:
        await client.download_media(
            message=message,
            file_name=file_path,
            progress=progress_for_pyrogram,
            progress_args=("⬇️ Mendownload...", status_msg, start_time)
        )
        
        # Count files
        count = len([f for f in os.listdir(user_path) if f.lower().endswith(('.mp4', '.mkv', '.mov', '.avi'))])
        
        status_text = f"✅ **Berhasil disimpan!**\n📄 Nama: `{orig_file_name}`\n📂 Total: `{count}` file\n\nKetik /merge jika sudah selesai."
        
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Rename File Ini", callback_data=f"rename_{orig_file_name}")]
        ])

        # Check if we should edit the PREVIOUS global status message or the CURRENT one
        if user_id in status_msgs:
            try:
                await status_msg.delete()
                await client.edit_message_text(user_id, status_msgs[user_id], status_text, reply_markup=markup)
            except:
                status_msgs[user_id] = status_msg.id
                await status_msg.edit(status_text, reply_markup=markup)
        else:
            status_msgs[user_id] = status_msg.id
            await status_msg.edit(status_text, reply_markup=markup)
            
    except Exception as e:
        await status_msg.edit(f"❌ Gagal mendownload: {str(e)}")

@Client.on_callback_query(filters.regex("^rename_"))
async def rename_callback(client, callback_query):
    user_id = callback_query.from_user.id
    old_name = callback_query.data.replace("rename_", "")
    
    rename_states[user_id] = {"old_name": old_name, "msg_id": callback_query.message.id}
    
    await callback_query.message.edit(
        f"📝 **Masukkan nama baru untuk file:**\n`{old_name}`\n\n(Berikan nama lengkap dengan ekstensi, misal: `episode1.mp4`)",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Batal", callback_data="cancel_rename")]])
    )

@Client.on_callback_query(filters.regex("cancel_rename"))
async def cancel_rename(client, callback_query):
    user_id = callback_query.from_user.id
    rename_states.pop(user_id, None)
    await callback_query.message.edit("❌ Rename dibatalkan. Gunakan /merge untuk lanjut.")

# Handle text for renaming
@Client.on_message(filters.private & filters.text & ~filters.command)
async def rename_text_handler(client, message):
    user_id = message.from_user.id
    if user_id not in rename_states:
        message.continue_propagation()
        return
    
    state = rename_states[user_id]
    old_name = state["old_name"]
    new_name = message.text.strip()
    
    user_path = os.path.abspath(os.path.join(DOWNLOAD_DIR, str(user_id)))
    old_path = os.path.join(user_path, old_name)
    new_path = os.path.join(user_path, new_name)
    
    if os.path.exists(old_path):
        try:
            os.rename(old_path, new_path)
            await client.edit_message_text(
                user_id, state["msg_id"], 
                f"✅ File berhasil di-rename!\nOld: `{old_name}`\nNew: `{new_name}`\n\nKetik /merge jika sudah selesai."
            )
        except Exception as e:
            await message.reply_text(f"❌ Gagal me-rename: {str(e)}")
    else:
        await message.reply_text("❌ File lama tidak ditemukan. Mungkin sudah dihapus atau sesi berakhir.")
    
    rename_states.pop(user_id, None)
