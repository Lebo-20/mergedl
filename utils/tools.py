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

async def get_video_duration(file_path):
    cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', file_path
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    try:
        return float(stdout.decode().strip())
    except:
        return 0

async def merge_videos(input_dir, output_file, sub_type='none', sub_path=None, preset='veryfast', crf=22, use_watermark=False, status_msg=None):
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

    # 4. Total Duration for progress bar (PARALLEL PROBING for speed)
    if status_msg:
        try: await status_msg.edit(f"🔍 Memindai durasi {len(files)} file...")
        except: pass
        
    tasks = [get_video_duration(os.path.join(input_dir, f)) for f in files]
    durations = await asyncio.gather(*tasks)
    total_duration = sum(durations)
    
    # 5. Create list.txt
    list_file_path = os.path.join(input_dir, 'list.txt')
    with open(list_file_path, 'w', encoding='utf-8') as f:
        for file in files:
            abs_video_path = os.path.join(input_dir, file)
            escaped_path = abs_video_path.replace("'", "'\\''")
            f.write(f"file '{escaped_path}'\n")
            
    # 6. FFmpeg command building
    cmd = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', 'list.txt', '-progress', 'pipe:1']
    
    # Subtitle handling
    if sub_type != 'none' and sub_path and os.path.exists(sub_path):
        sub_filename = os.path.basename(sub_path)
        sub_dir = os.path.dirname(os.path.abspath(sub_path))
        if sub_dir != input_dir:
            temp_sub_path = os.path.join(input_dir, sub_filename)
            import shutil
            shutil.copy2(sub_path, temp_sub_path)
        
        if sub_type == 'hardsub':
            style = "Fontname=Standard Symbols PS,Fontsize=10,PrimaryColour=&H00FFFFFF,BorderStyle=1,Outline=1,Shadow=0,Alignment=2,MarginV=90,Bold=1"
            sub_filename_escaped = sub_filename.replace("'", "\\'")
            vf_filters = [f"subtitles='{sub_filename_escaped}':force_style='{style}'"]
            if use_watermark:
                watermark_text = "@ShortTeamDl_bot"
                vf_filters.append(f"drawtext=text='{watermark_text}':fontcolor=white@0.4:fontsize=20:x=(w-text_w)/2:y=h-th-20")
            cmd.extend(['-vf', ",".join(vf_filters)])
            cmd.extend(['-c:v', 'libx264', '-preset', preset, '-crf', str(crf), '-profile:v', 'high', '-c:a', 'aac', '-b:a', '128k', '-ac', '2'])
            
        elif sub_type == 'softsub':
            cmd.extend(['-i', sub_filename])
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
        watermark_text = "@ShortTeamDl_bot"
        cmd.extend(['-vf', f"drawtext=text='{watermark_text}':fontcolor=white@0.4:fontsize=20:x=(w-text_w)/2:y=h-th-20", '-c:v', 'libx264', '-preset', preset, '-crf', str(crf), '-c:a', 'copy'])
    else:
        cmd.extend(['-c', 'copy'])

    abs_output = os.path.abspath(output_file)
    cmd.append(abs_output)
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=input_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    # Monitor progress
    start_time = time.time()
    last_update = 0
    
    while True:
        line = await process.stdout.readline()
        if not line:
            break
        
        line_str = line.decode().strip()
        if line_str.startswith("out_time_ms="):
            out_time_ms = int(line_str.split("=")[1])
            processed_seconds = out_time_ms / 1000000.0
            
            if status_msg and total_duration > 0:
                current_time = time.time()
                # Update every 5 seconds to avoid flooding
                if current_time - last_update > 5:
                    percentage = (processed_seconds / total_duration) * 100
                    percentage = min(percentage, 100) # Clamp to 100
                    
                    diff = current_time - start_time
                    speed = processed_seconds / diff if diff > 0 else 0
                    eta = (total_duration - processed_seconds) / speed if speed > 0 else 0
                    
                    progress_p = "[{0}{1}] \nP: {2}%\n".format(
                        "".join([FINISHED_PROGRESS_STR for i in range(math.floor(percentage / 5))]),
                        "".join([UNFINISHED_PROGRESS_STR for i in range(20 - math.floor(percentage / 5))]),
                        round(percentage, 2))
                        
                    tmp = progress_p + "Time: {0} of {1}\nSpeed: {2}x\nETA: {3}\n".format(
                        TimeFormatter(processed_seconds * 1000),
                        TimeFormatter(total_duration * 1000),
                        round(speed, 2),
                        TimeFormatter(eta * 1000)
                    )
                    
                    try:
                        await status_msg.edit(f"🔄 **Sedang diproses...**\n{tmp}")
                        last_update = current_time
                    except:
                        pass

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

async def get_video_subtitles(file_path):
    cmd = [
        'ffprobe', '-v', 'error', '-select_streams', 's',
        '-show_entries', 'stream=index,codec_name:stream_tags=language,title',
        '-of', 'json', file_path
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        return []
    import json
    try:
        data = json.loads(stdout)
        return data.get('streams', [])
    except:
        return []

async def extract_and_join_subtitles(input_dir, files, stream_index, status_msg=None):
    import datetime
    
    valid_files = []
    cumulative_duration = 0
    final_content = []
    sub_format = 'srt'
    
    for i, file in enumerate(files):
        video_path = os.path.join(input_dir, file)
        
        # Determine format from first video
        if i == 0:
            subs = await get_video_subtitles(video_path)
            for s in subs:
                if s.get('index') == stream_index:
                    sub_format = 'ass' if s.get('codec_name') == 'ass' else 'srt'
                    break
        
        temp_name = f"temp_sub_{i}.{sub_format}"
        temp_path = os.path.join(input_dir, temp_name)
        
        if status_msg:
            try: await status_msg.edit(f"📥 Mengekstrak sub dari part {i+1}...")
            except: pass
            
        cmd = ['ffmpeg', '-y', '-i', video_path, '-map', f'0:{stream_index}', temp_path]
        process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await process.communicate()
        
        if os.path.exists(temp_path):
            with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            if sub_format == 'srt':
                # Shift SRT
                shifted = shift_srt(content, cumulative_duration)
                final_content.append(shifted)
            else:
                # Shift ASS
                shifted = shift_ass(content, cumulative_duration, i == 0)
                final_content.append(shifted)
                
            os.remove(temp_path)
            
        duration = await get_video_duration(video_path)
        cumulative_duration += duration

    if not final_content:
        return None
        
    final_sub_path = os.path.join(input_dir, f"internal_joined.{sub_format}")
    with open(final_sub_path, 'w', encoding='utf-8') as f:
        if sub_format == 'ass':
            # Join ASS: First one contains header, others only events
            f.write("\n".join(final_content))
        else:
            # Join SRT: Concat is fine
            f.write("\n".join(final_content))
            
    return final_sub_path

def shift_srt(content, offset_seconds):
    if offset_seconds == 0:
        return content
    
    def shift_match(match):
        start = shift_srt_time(match.group(1), offset_seconds)
        end = shift_srt_time(match.group(2), offset_seconds)
        return f"{start} --> {end}"

    pattern = r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})"
    return re.sub(pattern, shift_match, content)

def shift_srt_time(time_str, offset_seconds):
    try:
        h, m, s_ms = time_str.split(':')
        s, ms = s_ms.split(',')
        total_seconds = int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000.0
        new_total = total_seconds + offset_seconds
        
        sh, rem = divmod(new_total, 3600)
        sm, ss = divmod(rem, 60)
        sms = (ss - int(ss)) * 1000
        return f"{int(sh):02}:{int(sm):02}:{int(ss):02},{int(round(sms)):03}"
    except:
        return time_str

def shift_ass(content, offset_seconds, is_first):
    lines = content.split('\n')
    new_lines = []
    
    if not is_first:
        # Only keep [Events] section lines
        in_events = False
        for line in lines:
            if line.strip().lower() == '[events]':
                in_events = True
                continue
            if in_events and line.startswith('Dialogue:'):
                new_lines.append(shift_ass_line(line, offset_seconds))
        return "\n".join(new_lines)
    else:
        # Keep everything but shift times in Dialogue lines
        for line in lines:
            if line.startswith('Dialogue:'):
                new_lines.append(shift_ass_line(line, offset_seconds))
            else:
                new_lines.append(line)
        return "\n".join(new_lines)

def shift_ass_line(line, offset_seconds):
    if offset_seconds == 0:
        return line
    try:
        parts = line.split(',', 9)
        if len(parts) < 10: return line
        
        parts[1] = shift_ass_time(parts[1], offset_seconds) # Start
        parts[2] = shift_ass_time(parts[2], offset_seconds) # End
        return ",".join(parts)
    except:
        return line

def shift_ass_time(time_str, offset_seconds):
    try:
        h, m, s_cs = time_str.split(':')
        s, cs = s_cs.split('.')
        total_seconds = int(h)*3600 + int(m)*60 + int(s) + int(cs)/100.0
        new_total = total_seconds + offset_seconds
        
        sh, rem = divmod(new_total, 3600)
        sm, ss = divmod(rem, 60)
        scs = (ss - int(ss)) * 100
        return f"{int(sh)}:{int(sm):02}:{int(ss):02}.{int(round(scs)):02}"
    except:
        return time_str

async def extract_subtitle(video_path, stream_index, output_format='srt'):
    # Extract to a temp file in the same directory
    output_path = video_path.rsplit('.', 1)[0] + f"_internal.{output_format}"
    cmd = [
        'ffmpeg', '-y', '-i', video_path,
        '-map', f'0:{stream_index}', output_path
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await process.communicate()
    if os.path.exists(output_path):
        return output_path
    return None
