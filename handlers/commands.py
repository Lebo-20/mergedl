import os
import shutil
import asyncio
import sys
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import DOWNLOAD_DIR
from utils.tools import merge_videos, upload_to_git, get_video_subtitles, extract_subtitle, natural_sort_key

@Client.on_message(filters.command("id") & filters.private)
async def id_cmd(client, message):
    await message.reply_text(f"🆔 **ID Telegram Anda:** `{message.from_user.id}`")

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

# Store user states for multi-step process
user_states = {}

@Client.on_message(filters.command("merge") & filters.private)
async def merge_cmd(client, message):
    user_id = message.from_user.id
    user_path = os.path.abspath(os.path.join(DOWNLOAD_DIR, str(user_id)))
    
    if not os.path.exists(user_path) or not os.listdir(user_path):
        await message.reply_text("❌ Tidak ada video untuk digabung. Silakan kirim video terlebih dahulu.")
        return
        
    user_states[user_id] = {
        "sub_type": "none", 
        "preset": "veryfast", 
        "crf": "22", 
        "watermark": False,
        "output_name": f"merged_{user_id}.mp4",
        "state": ""
    }

    await message.reply_text(
        "Pilih metode Merge:",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Copy (Cepat - Tanpa Sub)", callback_data="merge_copy"),
                InlineKeyboardButton("Hardsub (Burn-in)", callback_data="merge_sub_hard")
            ],
            [
                InlineKeyboardButton("Softsub (Pilih Track)", callback_data="merge_sub_soft")
            ]
        ])
    )

@Client.on_callback_query(filters.regex("^(merge_|mset_)"))
async def merge_callback(client, callback_query):
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    if user_id not in user_states:
        user_states[user_id] = {
            "sub_type": "none", 
            "preset": "veryfast", 
            "crf": "22", 
            "watermark": False,
            "output_name": f"merged_{user_id}.mp4",
            "state": ""
        }

    if data == "merge_copy":
        user_states[user_id]["sub_type"] = "none"
        await ask_preset(client, callback_query.message, user_id)
    elif data == "merge_sub_hard":
        user_states[user_id]["sub_type"] = "hardsub"
        await ask_subtitle(client, callback_query.message, user_id)
    elif data == "merge_sub_soft":
        user_states[user_id]["sub_type"] = "softsub"
        await ask_subtitle(client, callback_query.message, user_id)
    elif data.startswith("mset_preset_"):
        user_states[user_id]["preset"] = data.split("_")[-1]
        await ask_crf(client, callback_query.message, user_id)
    elif data.startswith("mset_crf_"):
        user_states[user_id]["crf"] = data.split("_")[-1]
        await ask_watermark(client, callback_query.message, user_id)
    elif data == "mset_wm_yes":
        user_states[user_id]["watermark"] = True
        await ask_filename(client, callback_query.message, user_id)
    elif data == "mset_wm_no":
        user_states[user_id]["watermark"] = False
        await ask_filename(client, callback_query.message, user_id)
    elif data.startswith("mset_ext_sub_"):
        # Selected internal track to extract
        stream_index = int(data.split("_")[-1])
        user_path = os.path.join(DOWNLOAD_DIR, str(user_id))
        valid_extensions = ('.mp4', '.mkv', '.mov', '.avi')
        files = [f for f in os.listdir(user_path) if f.lower().endswith(valid_extensions)]
        files.sort(key=natural_sort_key)
        
        if files:
            video_path = os.path.join(user_path, files[0])
            ext_msg = await callback_query.message.edit("⚙️ Sedang mengekstrak subtitle internal...")
            sub_path = await extract_subtitle(video_path, stream_index)
            if sub_path:
                user_states[user_id]["sub_path"] = sub_path
                user_states[user_id]["state"] = ""
                await ask_preset(client, callback_query.message, user_id)
            else:
                await callback_query.answer("❌ Gagal mengekstrak subtitle.", show_alert=True)
        else:
            await callback_query.answer("❌ File video tidak ditemukan.", show_alert=True)

    elif data == "mset_skip_sub":
        user_states[user_id]["state"] = ""
        user_states[user_id]["sub_type"] = "none"
        await ask_preset(client, callback_query.message, user_id)

async def ask_subtitle(client, message, user_id):
    user_path = os.path.join(DOWNLOAD_DIR, str(user_id))
    valid_extensions = ('.mp4', '.mkv', '.mov', '.avi')
    files = [f for f in os.listdir(user_path) if f.lower().endswith(valid_extensions)]
    files.sort(key=natural_sort_key)
    
    buttons = []
    text = "📂 **Silakan kirim file subtitle (.srt atau .ass)**\n\nPastikan format file benar."
    
    if files:
        video_path = os.path.join(user_path, files[0])
        subs = await get_video_subtitles(video_path)
        if subs:
            text += "\n\nAtau **pilih subtitle internal** dari video:"
            for stream in subs:
                idx = stream.get('index')
                lang = stream.get('tags', {}).get('language', 'und')
                title = stream.get('tags', {}).get('title', f"Track {idx}")
                codec = stream.get('codec_name', 'sub')
                buttons.append([InlineKeyboardButton(f"🎬 {title} ({lang}/{codec})", callback_data=f"mset_ext_sub_{idx}")])

    buttons.append([InlineKeyboardButton("Batal / Lewati", callback_data="mset_skip_sub")])

    await message.edit(
        text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    user_states[user_id]["state"] = "AWAIT_SUB"

async def ask_preset(client, message, user_id):
    await message.edit(
        "⚙️ **Pilih Preset Encoding:**\nLower preset = Slower but better quality/smaller size",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Veryfast (Cepat)", callback_data="mset_preset_veryfast")],
            [InlineKeyboardButton("Medium (Seimbang)", callback_data="mset_preset_medium")],
            [InlineKeyboardButton("Slow (Terbaik / Lambat)", callback_data="mset_preset_slow")]
        ])
    )

async def ask_crf(client, message, user_id):
    await message.edit(
        "💎 **Pilih Kualitas (CRF):**\nLower CRF = Higher quality, Larger file",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("20 (High)", callback_data="mset_crf_20"), 
             InlineKeyboardButton("21", callback_data="mset_crf_21")],
            [InlineKeyboardButton("22 (Medium)", callback_data="mset_crf_22"), 
             InlineKeyboardButton("23 (Efficient)", callback_data="mset_crf_23")]
        ])
    )

async def ask_watermark(client, message, user_id):
    await message.edit(
        "💧 **Tambahkan Watermark (@ShortTeamDl_bot)?**",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Ya", callback_data="mset_wm_yes"), 
             InlineKeyboardButton("❌ Tidak", callback_data="mset_wm_no")]
        ])
    )

async def ask_filename(client, message, user_id):
    await message.edit(
        "📝 **Masukkan nama file output (tanpa ekstensi):**\nKetik 'default' untuk nama standar."
    )
    user_states[user_id]["state"] = "AWAIT_FILENAME"

# Handler for text messages (to capture filename) and documents (for subtitles)
@Client.on_message(filters.private & (filters.text | filters.document) & ~filters.regex(r"^/"))
async def state_handler(client, message):
    user_id = message.from_user.id
    if user_id not in user_states:
        message.continue_propagation()
        return
    
    state = str(user_states[user_id].get("state", ""))
    if not state:
        message.continue_propagation()
        return
    
    if state == "AWAIT_SUB":
        if message.document and (message.document.file_name.lower().endswith(('.srt', '.ass'))):
            user_path = os.path.join(DOWNLOAD_DIR, str(user_id))
            sub_path = os.path.join(user_path, message.document.file_name)
            await message.download(sub_path)
            user_states[user_id]["sub_path"] = sub_path
            user_states[user_id]["state"] = ""
            await ask_preset(client, message, user_id)
        else:
            message.continue_propagation() # Might be a video document?

    elif state == "AWAIT_FILENAME":
        filename = (message.text or "default").strip()
        if filename.lower() != 'default':
            # Sanitize filename
            filename = "".join([c for c in filename if c.isalnum() or c in (' ', '.', '_', '-')]).strip()
            if not filename:
                filename = f"merged_{user_id}"
            user_states[user_id]["output_name"] = f"{filename}.mp4"
        
        user_states[user_id]["state"] = ""
        # Start the merge process after filename is set
        await start_merge_process(client, message, user_id)

async def start_merge_process(client, message, user_id):
    status = await message.reply_text("⏳ Memulai proses merge... Harap tunggu.")
    
    user_path = os.path.abspath(os.path.join(DOWNLOAD_DIR, str(user_id)))
    data = user_states[user_id]
    
    output_name = str(data["output_name"])
    output_path = os.path.join(user_path, output_name)
    
    try:
        sub_type = str(data["sub_type"])
        preset = str(data["preset"])
        crf = int(data["crf"])
        sub_path = data.get("sub_path")
        if sub_path:
            sub_path = str(sub_path)
        use_watermark = bool(data.get("watermark", False))

        # Check if we need re-encoding or copy
        if sub_type == 'none' and not use_watermark:
             await merge_videos(user_path, output_path, sub_type='none', preset=preset, crf=crf, use_watermark=False)
        else:
             await merge_videos(
                 user_path, output_path, 
                 sub_type=sub_type, 
                 sub_path=sub_path,
                 preset=preset,
                 crf=crf,
                 use_watermark=use_watermark
             )
        
        # Determine actual output extension (softsub might have changed it to .mkv)
        actual_output = output_path
        if not os.path.exists(actual_output):
            mkv_path = output_path.rsplit('.', 1)[0] + ".mkv"
            if os.path.exists(mkv_path):
                actual_output = mkv_path

        await status.edit("📤 Mengirim hasil ke Anda...")
        
        await client.send_video(
            chat_id=user_id,
            video=actual_output,
            caption=f"✅ **Proses Merge Selesai!**\n\nMetode: {sub_type.capitalize()}\nPreset: {preset}\nCRF: {crf}",
            supports_streaming=True
        )
        
        # Optional: upload to git
        try:
            await status.edit("📤 Mengupload ke repo...")
            await upload_to_git(actual_output)
        except: pass

        await status.delete()
        
    except Exception as e:
        await status.edit(f"❌ Terjadi kesalahan: {str(e)}")
            
    finally:
        # Cleanup
        if user_id in user_states:
            user_states.pop(user_id, None)
        if os.path.exists(user_path):
            try: shutil.rmtree(user_path)
            except: pass

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
