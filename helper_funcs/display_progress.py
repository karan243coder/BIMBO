# -*- coding: utf-8 -*-
# BIMBO URL Bot
# Powered by BIMBO
# Support: @Bimbo69

import logging
import math
import re
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Smooth speed tracking
speed_history = {}
last_edit_time = {}
last_progress_text = {}

PROGRESS_UPDATE_INTERVAL = 5
PROGRESS_BAR_BLOCKS = 20
SPEED_HISTORY_LIMIT = 12


def trim_text(text: str, limit: int = 32) -> str:
    text = str(text or "Unknown File").strip()
    text = re.sub(r'\s+', ' ', text)
    if len(text) <= limit:
        return text
    return text[:limit - 3] + "..."


def humanbytes(size):
    if size is None:
        return "0 B"

    size = float(size)
    if size <= 0:
        return "0 B"

    power = 1024
    n = 0
    power_labels = {0: 'B', 1: 'KiB', 2: 'MiB', 3: 'GiB', 4: 'TiB', 5: 'PiB'}

    while size >= power and n < 5:
        size /= power
        n += 1

    if n == 0:
        return f"{int(size)} {power_labels[n]}"
    return f"{round(size, 2)} {power_labels[n]}"


def TimeFormatter(milliseconds: int) -> str:
    milliseconds = int(milliseconds or 0)
    seconds, milliseconds = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds:
        parts.append(f"{seconds}s")
    if milliseconds and not parts:
        parts.append(f"{milliseconds}ms")

    return ', '.join(parts) if parts else "0 s"


def get_status_emoji(percentage: float) -> str:
    if percentage < 25:
        return "🟡"
    if percentage < 50:
        return "🟠"
    if percentage < 75:
        return "🔵"
    if percentage < 100:
        return "🟢"
    return "✅"


def get_action_meta(is_download: bool):
    if is_download:
        return "⬇️", "DOWNLOAD", "Downloading"
    return "⬆️", "UPLOAD", "Uploading"


def build_progress_bar(percentage: float, total_blocks: int = PROGRESS_BAR_BLOCKS) -> str:
    percentage = max(0.0, min(100.0, percentage))
    completed_blocks = min(total_blocks, math.floor((percentage / 100) * total_blocks))
    remaining_blocks = total_blocks - completed_blocks
    return "█" * completed_blocks + "░" * remaining_blocks


def format_speed(speed_bytes_per_sec: float) -> str:
    if not speed_bytes_per_sec or speed_bytes_per_sec <= 0:
        return "Calculating..."
    return f"{humanbytes(speed_bytes_per_sec)}/s"


def cleanup_progress_state(msg_id: int):
    speed_history.pop(msg_id, None)
    last_edit_time.pop(msg_id, None)
    last_progress_text.pop(msg_id, None)


async def progress_for_pyrogram(
    current,
    total,
    ud_type,
    message,
    start,
    file_name="",
    is_download=False
):
    if not message or total == 0:
        return

    now = time.time()
    diff = max(now - start, 0.001)
    msg_id = getattr(message, "id", 0) or 0
    last_time = last_edit_time.get(msg_id, 0)

    if (now - last_time < PROGRESS_UPDATE_INTERVAL) and current not in (0, total):
        return

    percentage = (current * 100) / total
    percentage = min(max(percentage, 0), 100)
    instant_speed = current / diff if diff > 0 else 0

    history = speed_history.setdefault(msg_id, [])
    history.append(instant_speed)
    if len(history) > SPEED_HISTORY_LIMIT:
        history.pop(0)
    avg_speed = sum(history) / len(history) if history else instant_speed

    elapsed_ms = int(diff * 1000)
    remaining_bytes = max(total - current, 0)
    eta_ms = int((remaining_bytes / avg_speed) * 1000) if avg_speed > 0 else 0

    elapsed_text = TimeFormatter(elapsed_ms)
    eta_text = TimeFormatter(eta_ms) if eta_ms > 0 else "0 s"
    transferred_text = humanbytes(current)
    total_text = humanbytes(total)
    speed_text = format_speed(avg_speed)
    progress_bar = build_progress_bar(percentage)

    action_emoji, action_title, stage_text = get_action_meta(is_download)
    status_emoji = get_status_emoji(percentage)
    display_name = trim_text(file_name or "Unknown File", 34)

    progress_text = (
        f"╭━━━〔 {status_emoji} {action_title} STATUS 〕━━━╮\n"
        f"┃ {action_emoji} Status    : {stage_text}\n"
        f"┃ 📁 File      : {display_name}\n"
        f"┃ {progress_bar} {percentage:.2f}%\n"
        f"┃ ⚡ Speed     : {speed_text}\n"
        f"┃ 📦 Done      : {transferred_text} / {total_text}\n"
        f"┃ ⏳ ETA       : {eta_text}\n"
        f"┃ 🕒 Elapsed   : {elapsed_text}\n"
        f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
    )

    if last_progress_text.get(msg_id) == progress_text and current != total:
        return

    try:
        await message.edit(text=progress_text)
        last_edit_time[msg_id] = now
        last_progress_text[msg_id] = progress_text

        if current == total:
            cleanup_progress_state(msg_id)

    except Exception as e:
        error_text = str(e).upper()
        if "MESSAGE_NOT_MODIFIED" not in error_text:
            logger.error(f"Progress edit error: {e}")

        if current == total:
            cleanup_progress_state(msg_id)
