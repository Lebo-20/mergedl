import math
import time
import os
import re
import subprocess
import asyncio
from asyncio import subprocess as async_subprocess
from config import FINISHED_PROGRESS_STR, UNFINISHED_PROGRESS_STR

async def progress_for_pyrogram(current, total, ud_type, message, start):
    now = time.time()
    diff = now - start
    if round(diff % 10.00) == 0 or current == total:
        percentage = current * 100 / (total if total > 0 else 1)
        speed = current / diff if diff > 0 else 0
        elapsed_time = round(diff) * 1000
        time_to_completion = round((total - current) / speed) * 1000 if speed > 0 else 0
        estimated_total_time = elapsed_time + time_to_completion

        elapsed_time_str = TimeFormatter(int(elapsed_time))
        estimated_total_time_str = TimeFormatter(int(estimated_total_time))

        progress = "[{0}{1}] \nP: {2}%\n".format(
            "".join([FINISHED_PROGRESS_STR for i in range(math.floor(percentage / 5))]),
            "".join([UNFINISHED_PROGRESS_STR for i in range(20 - math.floor(percentage / 5))]),
            round(float(percentage), 2))

        tmp = progress + "{0} of {1}\nSpeed: {2}/s\nETA: {3}\n".format(
            humanbytes(current),
            humanbytes(total),
            humanbytes(speed),
            estimated_total_time_str if estimated_total_time_str != '' else "0 s"
        )
        try:
            await message.edit(
                text="{}\n {}".format(ud_type, tmp)
            )
        except:
            pass

def humanbytes(size):
    if not size:
        return "0 B"
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power and n < 4:
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

async def get_video_duration(file_path, semaphore=None):
    if semaphore:
        async with semaphore:
            return await _get_video_duration(file_path)
    return await _get_video_duration(file_path)

async def _get_video_duration(file_path):
    cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', file_path
    ]
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=async_subprocess.PIPE,
            stderr=async_subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode == 0:
            return float(stdout.decode().strip())
    except:
        pass
    return 0.0

async def merge_videos(input_dir, output_file, sub_type='none', sub_path=None, preset='veryfast', crf=22, use_watermark=False, status_msg=None):
    input_dir = os.path.abspath(input_dir)
    output_file = os.path.abspath(output_file)
    
    valid_extensions = ('.mp4', '.mkv', '.mov', '.avi')
    files = [f for f in os.listdir(input_dir) if f.lower().endswith(valid_extensions)]
    
    if not files:
        raise Exception("❌ Tidak ada file video yang ditemukan untuk digabung.")
    
    files.sort(key=natural_sort_key)

    if status_msg:
        try: await status_msg.edit(f"🔍 Memindai durasi {len(files)} file...")
        except: pass
        
    sem = asyncio.Semaphore(10)
    tasks = [get_video_duration(os.path.join(input_dir, f), semaphore=sem) for f in files]
    durations_res = await asyncio.gather(*tasks)
    total_duration = 0.0
    for d in durations_res:
        if isinstance(d, (int, float)):
            total_duration += d
    
    list_file_path = os.path.join(input_dir, 'list.txt')
    with open(list_file_path, 'w', encoding='utf-8') as f:
        for file in files:
            abs_video_path = os.path.join(input_dir, file)
            escaped_path = abs_video_path.replace("'", "'\\''")
            f.write(f"file '{escaped_path}'\n")
            
    cmd = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', 'list.txt', '-progress', 'pipe:1']
    
    if sub_type != 'none' and sub_path and os.path.exists(sub_path):
        sub_filename = os.path.basename(sub_path)
        sub_dir = os.path.dirname(os.path.abspath(sub_path))
        if sub_dir != input_dir:
            import shutil
            shutil.copy2(sub_path, os.path.join(input_dir, sub_filename))
        
        if sub_type == 'hardsub':
            style = "Fontname=Standard Symbols PS,Fontsize=10,PrimaryColour=&H00FFFFFF,BorderStyle=1,Outline=1,Shadow=0,Alignment=2,MarginV=90,Bold=1"
            sub_filename_escaped = sub_filename.replace("'", "\\'")
            vf_filters = [f"subtitles='{sub_filename_escaped}':force_style='{style}'"]
            if use_watermark:
                vf_filters.append("drawtext=text='@ShortTeamDl_bot':fontcolor=white@0.4:fontsize=20:x=(w-text_w)/2:y=h-th-20")
            cmd.extend(['-vf', ",".join(vf_filters), '-c:v', 'libx264', '-preset', preset, '-crf', str(crf), '-c:a', 'aac', '-b:a', '128k', '-ac', '2'])
        elif sub_type == 'softsub':
            cmd.extend(['-i', sub_filename])
            if output_file.lower().endswith('.mkv'):
                cmd.extend(['-map', '0', '-map', '1:s', '-c', 'copy', '-c:s', 'srt'])
            else:
                if sub_filename.lower().endswith('.ass'):
                    output_file = output_file.rsplit('.', 1)[0] + ".mkv"
                    cmd.extend(['-map', '0', '-map', '1:s', '-c', 'copy', '-c:s', 'ass'])
                else:
                    cmd.extend(['-map', '0', '-map', '1:s', '-c', 'copy', '-c:s', 'mov_text'])
    elif use_watermark:
        cmd.extend(['-vf', "drawtext=text='@ShortTeamDl_bot':fontcolor=white@0.4:fontsize=20:x=(w-text_w)/2:y=h-th-20", '-c:v', 'libx264', '-preset', preset, '-crf', str(crf), '-c:a', 'copy'])
    else:
        cmd.extend(['-c', 'copy'])

    cmd.append(os.path.abspath(output_file))
    
    process = await asyncio.create_subprocess_exec(
        *cmd, cwd=input_dir, stdout=async_subprocess.PIPE, stderr=async_subprocess.PIPE
    )

    start_time = time.time()
    last_update = 0
    stderr_lines = []

    async def read_stderr(pipe):
        while True:
            line = await pipe.readline()
            if not line: break
            stderr_lines.append(line.decode(errors='ignore'))

    stderr_task = asyncio.create_task(read_stderr(process.stderr))
    
    try:
        while True:
            line = await process.stdout.readline()
            if not line: break
            
            line_str = line.decode().strip()
            if line_str.startswith("out_time_ms="):
                try:
                    out_time_ms = int(line_str.split("=")[1])
                    processed_seconds = out_time_ms / 1000000.0
                    
                    if status_msg and total_duration > 0:
                        current_time = time.time()
                        if current_time - last_update > 5:
                            percentage = min((processed_seconds / total_duration) * 100, 100)
                            diff = current_time - start_time
                            speed = processed_seconds / diff if diff > 0 else 0
                            eta = (total_duration - processed_seconds) / speed if speed > 0 else 0
                            
                            p_str = "[{0}{1}] \nP: {2}%\n".format(
                                "".join([FINISHED_PROGRESS_STR for i in range(math.floor(percentage / 5))]),
                                "".join([UNFINISHED_PROGRESS_STR for i in range(20 - math.floor(percentage / 5))]),
                                round(float(percentage), 2))
                            
                            t_str = p_str + f"Time: {TimeFormatter(int(processed_seconds*1000))} of {TimeFormatter(int(total_duration*1000))}\n" \
                                           f"Speed: {round(float(speed), 2)}x\n" \
                                           f"ETA: {TimeFormatter(int(eta*1000))}\n"
                            
                            try: await status_msg.edit(f"🔄 **Sedang diproses...**\n{t_str}")
                            except: pass
                            last_update = current_time
                except: pass
    finally:
        await process.wait()
        await stderr_task

    if process.returncode != 0:
        error_msg = "".join(stderr_lines)
        raise Exception(f"FFmpeg failed ({process.returncode}):\n{error_msg[:500]}")
    
    return output_file

async def upload_to_git(file_path):
    try:
        for git_cmd in [["git", "add", "."], ["git", "commit", "-m", f"Add merged video: {os.path.basename(file_path)}"], ["git", "push"]]:
            p = await asyncio.create_subprocess_exec(*git_cmd, stdout=async_subprocess.PIPE, stderr=async_subprocess.PIPE)
            await p.communicate()
        return True
    except: return False

async def download_aria2(url, download_path):
    cmd = ['aria2c', '--seed-time=0', '--max-connection-per-server=16', '--split=16', '--min-split-size=1M', '-d', os.path.dirname(download_path), '-o', os.path.basename(download_path), url]
    process = await asyncio.create_subprocess_exec(*cmd, stdout=async_subprocess.PIPE, stderr=async_subprocess.PIPE)
    stdout, stderr = await process.communicate()
    if process.returncode != 0: raise Exception(f"Aria2 failed: {stderr.decode()}")
    return download_path

async def get_video_subtitles(file_path):
    cmd = ['ffprobe', '-v', 'error', '-select_streams', 's', '-show_entries', 'stream=index,codec_name:stream_tags=language,title', '-of', 'json', file_path]
    process = await asyncio.create_subprocess_exec(*cmd, stdout=async_subprocess.PIPE, stderr=async_subprocess.PIPE)
    stdout, stderr = await process.communicate()
    if process.returncode != 0: return []
    import json
    try: return json.loads(stdout).get('streams', [])
    except: return []

async def extract_and_join_subtitles(input_dir, files, stream_index, status_msg=None):
    cumulative_duration = 0.0
    final_content = []
    sub_format = 'srt'
    
    for i, file in enumerate(files):
        video_path = os.path.join(input_dir, file)
        if i == 0:
            subs = await get_video_subtitles(video_path)
            for s in subs:
                if s.get('index') == stream_index:
                    sub_format = 'ass' if s.get('codec_name') == 'ass' else 'srt'
                    break
        
        temp_path = os.path.join(input_dir, f"temp_sub_{i}.{sub_format}")
        if status_msg:
            try: await status_msg.edit(f"📥 Mengekstrak sub dari part {i+1}...")
            except: pass
            
        cmd = ['ffmpeg', '-y', '-i', video_path, '-map', f'0:{stream_index}', temp_path]
        process = await asyncio.create_subprocess_exec(*cmd, stdout=async_subprocess.PIPE, stderr=async_subprocess.PIPE)
        await process.communicate()
        
        if os.path.exists(temp_path):
            with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            final_content.append(shift_srt(content, cumulative_duration) if sub_format == 'srt' else shift_ass(content, cumulative_duration, i == 0))
            os.remove(temp_path)
            
        duration = await get_video_duration(video_path)
        cumulative_duration += float(duration)

    if not final_content: return None
    final_sub_path = os.path.join(input_dir, f"internal_joined.{sub_format}")
    with open(final_sub_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(final_content))
    return final_sub_path

def shift_srt(content, offset_seconds):
    if offset_seconds == 0: return content
    def shift_match(match):
        return f"{shift_srt_time(match.group(1), offset_seconds)} --> {shift_srt_time(match.group(2), offset_seconds)}"
    return re.sub(r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})", shift_match, content)

def shift_srt_time(time_str, offset_seconds):
    try:
        h, m, s_ms = time_str.split(':')
        s, ms = s_ms.split(',')
        new_total = int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000.0 + offset_seconds
        sh, rem = divmod(new_total, 3600)
        sm, ss = divmod(rem, 60)
        sms = (ss - int(ss)) * 1000
        return f"{int(sh):02}:{int(sm):02}:{int(ss):02},{int(round(sms)):03}"
    except: return time_str

def shift_ass(content, offset_seconds, is_first):
    lines = content.split('\n')
    new_lines = []
    if not is_first:
        in_events = False
        for line in lines:
            if line.strip().lower() == '[events]': in_events = True; continue
            if in_events and line.startswith('Dialogue:'): new_lines.append(shift_ass_line(line, offset_seconds))
        return "\n".join(new_lines)
    for line in lines:
        new_lines.append(shift_ass_line(line, offset_seconds) if line.startswith('Dialogue:') else line)
    return "\n".join(new_lines)

def shift_ass_line(line, offset_seconds):
    if offset_seconds == 0: return line
    try:
        parts = line.split(',', 9)
        if len(parts) < 10: return line
        parts[1] = shift_ass_time(parts[1], offset_seconds)
        parts[2] = shift_ass_time(parts[2], offset_seconds)
        return ",".join(parts)
    except: return line

def shift_ass_time(time_str, offset_seconds):
    try:
        h, m, s_cs = time_str.split(':')
        s, cs = s_cs.split('.')
        new_total = int(h)*3600 + int(m)*60 + int(s) + int(cs)/100.0 + offset_seconds
        sh, rem = divmod(new_total, 3600)
        sm, ss = divmod(rem, 60)
        scs = (ss - int(ss)) * 100
        return f"{int(sh)}:{int(sm):02}:{int(ss):02}.{int(round(scs)):02}"
    except: return time_str

async def extract_subtitle(video_path, stream_index, output_format='srt'):
    output_path = video_path.rsplit('.', 1)[0] + f"_internal.{output_format}"
    process = await asyncio.create_subprocess_exec('ffmpeg', '-y', '-i', video_path, '-map', f'0:{stream_index}', output_path, stdout=async_subprocess.PIPE, stderr=async_subprocess.PIPE)
    await process.communicate()
    return output_path if os.path.exists(output_path) else None
