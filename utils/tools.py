import math
import time
import os
import re
import subprocess
import asyncio
from config import FINISHED_PROGRESS_STR, UNFINISHED_PROGRESS_STR

async def progress_for_pyrogram(current, total, ud_type, message, start):
    now = time.time()
    diff = now - start
    if round(diff % 10.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff
        elapsed_time = round(diff) * 1000
        time_to_completion = round((total - current) / speed) * 1000
        estimated_total_time = elapsed_time + time_to_completion

        elapsed_time = TimeFormatter(milliseconds=elapsed_time)
        estimated_total_time = TimeFormatter(milliseconds=estimated_total_time)

        progress = "[{0}{1}] \nP: {2}%\n".format(
            "".join([FINISHED_PROGRESS_STR for i in range(math.floor(percentage / 5))]),
            "".join([UNFINISHED_PROGRESS_STR for i in range(20 - math.floor(percentage / 5))]),
            round(percentage, 2))

        tmp = progress + "{0} of {1}\nSpeed: {2}/s\nETA: {3}\n".format(
            humanbytes(current),
            humanbytes(total),
            humanbytes(speed),
            estimated_total_time if estimated_total_time != '' else "0 s"
        )
        try:
            await message.edit(
                text="{}\n {}".format(ud_type, tmp)
            )
        except:
            pass

def humanbytes(size):
    if not size:
        return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'

def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
        ((str(hours) + "h, ") if hours else "") + \
        ((str(minutes) + "m, ") if minutes else "") + \
        ((str(seconds) + "s, ") if seconds else "") + \
        ((str(milliseconds) + "ms, ") if milliseconds else "")
    return tmp[:-2] if tmp.endswith(", ") else tmp

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', s)]

async def merge_videos(input_dir, output_file):
    # Absolute paths
    input_dir = os.path.abspath(input_dir)
    output_file = os.path.abspath(output_file)
    
    # 1. Scanning files correctly (Case-insensitive)
    valid_extensions = ('.mp4', '.mkv', '.mov', '.avi')
    files = [f for f in os.listdir(input_dir) if f.lower().endswith(valid_extensions)]
    
    # Debug: Print files found
    print(f"DEBUG: Files found in {input_dir}: {files}")
    
    # 2. Validation
    if not files:
        raise Exception("❌ Tidak ada file video yang ditemukan untuk digabung.")
    
    # 3. Sorting (Natural sorting based on numbers)
    files.sort(key=natural_sort_key)
    print(f"DEBUG: Sorted files: {files}")
    
    # 4. Create list.txt with ABSOLUTE paths and single quotes
    list_file_path = os.path.join(input_dir, 'list.txt')
    with open(list_file_path, 'w', encoding='utf-8') as f:
        for file in files:
            abs_video_path = os.path.join(input_dir, file)
            # Escape single quotes in filenames if any
            escaped_path = abs_video_path.replace("'", "'\\''")
            f.write(f"file '{escaped_path}'\n")
            
    # Debug: Print list.txt content
    with open(list_file_path, 'r') as f:
        print(f"DEBUG: list.txt content:\n{f.read()}")
            
    # 5. FFmpeg command with Watermark (RE-ENCODING REQUIRED)
    # Using libx264 with ultrafast preset for maximum speed
    watermark_text = "@ShortTeamDl_bot"
    cmd = [
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
        '-i', list_file_path,
        '-vf', f"drawtext=text='{watermark_text}':fontcolor=white@0.4:fontsize=14:x=(w-text_w)/2:y=h-th-20",
        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
        '-c:a', 'copy',
        output_file
    ]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        error_msg = stderr.decode()
        print(f"DEBUG: FFmpeg Error: {error_msg}")
        raise Exception(f"FFmpeg failed (Return Code {process.returncode}):\n{error_msg}")
    
    return output_file

async def upload_to_git(file_path):
    try:
        # This assumes the bot is running in a git repo already or you want to push to a specific one
        # For simplicity, we'll just show the logic to add, commit, push
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", f"Add merged video: {os.path.basename(file_path)}"], check=True)
        subprocess.run(["git", "push"], check=True)
        return True
    except Exception as e:
        print(f"Git upload failed: {e}")
        return False

async def download_aria2(url, download_path):
    cmd = [
        'aria2c',
        '--seed-time=0',
        '--max-connection-per-server=16',
        '--split=16',
        '--min-split-size=1M',
        '-d', os.path.dirname(download_path),
        '-o', os.path.basename(download_path),
        url
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise Exception(f"Aria2 failed: {stderr.decode()}")
    return download_path
