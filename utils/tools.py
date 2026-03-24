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

async def merge_videos(input_dir, output_file, sub_type='none', sub_path=None, preset='veryfast', crf=22, use_watermark=False):
    # Absolute paths
    input_dir = os.path.abspath(input_dir)
    output_file = os.path.abspath(output_file)
    
    # 1. Scanning files correctly (Case-insensitive)
    valid_extensions = ('.mp4', '.mkv', '.mov', '.avi')
    files = [f for f in os.listdir(input_dir) if f.lower().endswith(valid_extensions)]
    
    # 2. Validation
    if not files:
        raise Exception("❌ Tidak ada file video yang ditemukan untuk digabung.")
    
    # 3. Sorting (Natural sorting based on numbers)
    files.sort(key=natural_sort_key)
    
    # 4. Create list.txt with ABSOLUTE paths and single quotes
    list_file_path = os.path.join(input_dir, 'list.txt')
    with open(list_file_path, 'w', encoding='utf-8') as f:
        for file in files:
            abs_video_path = os.path.join(input_dir, file)
            # Escape single quotes in filenames if any
            escaped_path = abs_video_path.replace("'", "'\\''")
            f.write(f"file '{escaped_path}'\n")
            
    # FFmpeg command building
    cmd = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', 'list.txt']
    
    # Subtitle handling
    if sub_type != 'none' and sub_path and os.path.exists(sub_path):
        # Move to input_dir if not there
        sub_filename = os.path.basename(sub_path)
        sub_dir = os.path.dirname(os.path.abspath(sub_path))
        if sub_dir != input_dir:
            temp_sub_path = os.path.join(input_dir, sub_filename)
            import shutil
            shutil.copy2(sub_path, temp_sub_path)
        
        if sub_type == 'hardsub':
            # Burning subtitles
            style = (
                "Fontname=Standard Symbols PS,Fontsize=10,PrimaryColour=&H00FFFFFF,"
                "BorderStyle=1,Outline=1,Shadow=0,Alignment=2,MarginV=90,Bold=1"
            )
            # Use relative filename with escaped single quotes for filter
            sub_filename_escaped = sub_filename.replace("'", "\\'")
            vf_filters = [f"subtitles='{sub_filename_escaped}':force_style='{style}'"]
            
            if use_watermark:
                watermark_text = "@ShortTeamDl_bot"
                vf_filters.append(f"drawtext=text='{watermark_text}':fontcolor=white@0.4:fontsize=14:x=(w-text_w)/2:y=h-th-20")
            
            cmd.extend(['-vf', ",".join(vf_filters)])
            cmd.extend([
                '-c:v', 'libx264',
                '-preset', preset,
                '-crf', str(crf),
                '-profile:v', 'high',
                '-c:a', 'aac', '-b:a', '128k', '-ac', '2'
            ])
            
        elif sub_type == 'softsub':
            # Softsubbing (Add as stream)
            cmd.extend(['-i', sub_filename])
            
            # Use MKV if output is MP4 but might not be compatible, or if user asked for MKV
            is_mkv = output_file.lower().endswith('.mkv')
            
            if is_mkv:
                cmd.extend(['-map', '0', '-map', '1:s', '-c', 'copy', '-c:s', 'srt'])
            else:
                if sub_filename.lower().endswith('.ass'):
                    output_file = output_file.rsplit('.', 1)[0] + ".mkv"
                    cmd.extend(['-map', '0', '-map', '1:s', '-c', 'copy', '-c:s', 'ass'])
                else:
                    cmd.extend(['-map', '0', '-map', '1:s', '-c', 'copy', '-c:s', 'mov_text'])
    
    elif use_watermark:
        # Watermark only (Re-encoding required)
        watermark_text = "@ShortTeamDl_bot"
        cmd.extend([
            '-vf', f"drawtext=text='{watermark_text}':fontcolor=white@0.4:fontsize=14:x=(w-text_w)/2:y=h-th-20",
            '-c:v', 'libx264', '-preset', preset, '-crf', str(crf),
            '-c:a', 'copy'
        ])
    else:
        # Standard Copy (NO RE-ENCODING, SUPER FAST)
        cmd.extend(['-c', 'copy'])

    # Ensure output path is absolute before running FFmpeg in cwd
    abs_output = os.path.abspath(output_file)
    cmd.append(abs_output)
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=input_dir,
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
