# -*- coding: utf-8 -*-
# BIMBO URL Bot
# Powered by BIMBO
# Support: @Bimbo69

import os
import json
import html
import asyncio
import logging
import re
import aiohttp
from urllib.parse import urlparse

from config import Config
from pyrogram import filters, enums
from database.adduser import AddUser
from pyrogram import Client as BimboBot
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from helper_funcs.display_progress import humanbytes
from utils import check_verification, get_token
from plugins.xhamster_engine import is_xhamster as _xh_is, extract as xh_extract

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

DIRECT_FILE_EXTENSIONS = [
    '.mp4', '.mkv', '.mov', '.avi', '.webm', '.flv', '.m4v', '.3gp',
    '.mp3', '.m4a', '.wav', '.flac', '.aac', '.ogg', '.wma',
    '.pdf', '.zip', '.rar', '.7z', '.tar', '.gz', '.apk',
    '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg',
    '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt',
    '.exe', '.dmg', '.iso', '.torrent'
]

PREFERRED_VIDEO_EXTS = ["mp4", "mkv", "webm"]
HLS_PROTOCOLS = {"m3u8", "m3u8_native"}


# ============================================================
#  xHamster special handling
#  Reason: xHamster ke "progressive mp4" (h264-480p etc.) URLs ab DEAD hain
#  (CDN "Wrong key" 403 deta hai) aur av1 HLS variants resolve nahi hote.
#  SIRF h264 (avc1) + audio (mp4a) wale HLS variants actually download hote
#  hain. Isliye xHamster ke liye hum:
#    - clean height-based buttons dikhate hain (144p..1080p)
#    - format_id "xh-<height>" rakhte hain -> download time pe ek HEIGHT-BASED
#      format-string use hota hai (specific format_id nahi), taaki yt-dlp
#      khud sahi (avc1+mp4a) HLS variant chun le.
# ============================================================
def is_xhamster(url: str) -> bool:
    # asli detection xhamster_engine me hai (saare domains/mirrors)
    return _xh_is(url)


def build_xhamster_keyboard_from_engine(xh):
    """Engine ke nikaale qualities se clean buttons banao."""
    inline_keyboard = []
    for q in sorted(xh.get("qualities", []), key=lambda x: -int(x["height"])):
        h = int(q["height"])
        label = "🎬 " + q.get("label", f"{h}p")
        cb_video = f"video|xh-{h}|mp4"
        cb_file = f"file|xh-{h}|mp4"
        inline_keyboard.append([
            InlineKeyboardButton(label, callback_data=cb_video.encode("UTF-8")),
            InlineKeyboardButton("📁 File", callback_data=cb_file.encode("UTF-8")),
        ])
    if xh.get("duration") is not None:
        inline_keyboard.append([
            InlineKeyboardButton("🎵 MP3 128K", callback_data="audio|128k|mp3".encode("UTF-8")),
            InlineKeyboardButton("🎧 MP3 320K", callback_data="audio|320k|mp3".encode("UTF-8")),
        ])
    if not inline_keyboard:
        inline_keyboard.append([
            InlineKeyboardButton("🎬 Send Video", callback_data="video|xh-720|mp4".encode("UTF-8")),
            InlineKeyboardButton("📁 Send File", callback_data="file|xh-720|mp4".encode("UTF-8")),
        ])
    return InlineKeyboardMarkup(inline_keyboard)


def build_xhamster_keyboard(response_json):
    """xHamster ke liye clean height-based quality buttons."""
    heights = set()
    for fmt in (response_json.get("formats") or []):
        proto = (fmt.get("protocol") or "")
        h = fmt.get("height")
        vc = (fmt.get("vcodec") or "")
        # SIRF h264 (avc1) HLS variants count karo (yahi download hote hain)
        if h and proto.startswith("m3u8") and vc.lower().startswith(("avc1", "h264")):
            heights.add(int(h))
    if not heights:
        # fallback: kisi bhi HLS height
        for fmt in (response_json.get("formats") or []):
            if fmt.get("height") and (fmt.get("protocol") or "").startswith("m3u8"):
                heights.add(int(fmt["height"]))

    QLABEL = {144: "144p", 240: "240p", 360: "360p", 480: "480p (SD)",
              720: "720p (HD)", 1080: "1080p (FHD)", 1440: "1440p", 2160: "4K"}
    inline_keyboard = []
    for h in sorted(heights, reverse=True):
        label = "🎬 " + QLABEL.get(h, f"{h}p")
        # format_id "xh-<height>" -> download step ise pehchaan kar height-based
        # format-string use karega. ext hamesha mp4.
        cb_video = f"video|xh-{h}|mp4"
        cb_file = f"file|xh-{h}|mp4"
        inline_keyboard.append([
            InlineKeyboardButton(label, callback_data=cb_video.encode("UTF-8")),
            InlineKeyboardButton("📁 File", callback_data=cb_file.encode("UTF-8")),
        ])
    if response_json.get("duration") is not None:
        inline_keyboard.append([
            InlineKeyboardButton("🎵 MP3 128K", callback_data="audio|128k|mp3".encode("UTF-8")),
            InlineKeyboardButton("🎧 MP3 320K", callback_data="audio|320k|mp3".encode("UTF-8")),
        ])
    if not inline_keyboard:
        inline_keyboard.append([
            InlineKeyboardButton("🎬 Send Video", callback_data="video|xh-720|mp4".encode("UTF-8")),
            InlineKeyboardButton("📁 Send File", callback_data="file|xh-720|mp4".encode("UTF-8")),
        ])
    return InlineKeyboardMarkup(inline_keyboard)


def escape_html(text):
    return html.escape(str(text or ""), quote=False)


def trim_text(text: str, limit: int = 60) -> str:
    text = str(text or "").strip()
    return text if len(text) <= limit else text[:limit - 3] + "..."


def build_verify_markup(verify_url: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧑‍💻 Verify Now", url=verify_url)],
        [InlineKeyboardButton("📘 How to Verify", url=f"{Config.BIMBO_TUTORIAL}")]
    ])


def build_direct_markup():
    cb_string_file = "{}={}={}".format("file", "DIRECT", "AUTO")
    cb_string_video = "{}={}={}".format("video", "DIRECT", "AUTO")
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📁 File", callback_data=cb_string_file.encode("UTF-8")),
        InlineKeyboardButton("🎬 Video", callback_data=cb_string_video.encode("UTF-8"))
    ]])


def safe_filesize(fmt):
    if fmt.get("filesize"):
        return humanbytes(fmt["filesize"])
    if fmt.get("filesize_approx"):
        return f"~{humanbytes(fmt['filesize_approx'])}"
    return "?"


def clean_quality_label(fmt):
    height = fmt.get("height")
    width = fmt.get("width")
    note = fmt.get("format_note") or fmt.get("format") or "Unknown"

    if height:
        return f"{height}p"
    if width and fmt.get("height"):
        return f"{width}x{fmt.get('height')}"

    note = str(note)
    note = note.replace("video only", "").replace("audio only", "").strip()
    return note[:20] if note else "Auto"


def score_format(fmt):
    score = 0
    ext = (fmt.get("ext") or "").lower()
    protocol = (fmt.get("protocol") or "").lower()
    vcodec = (fmt.get("vcodec") or "").lower()
    acodec = (fmt.get("acodec") or "").lower()
    height = int(fmt.get("height") or 0)
    tbr = float(fmt.get("tbr") or 0)

    if vcodec and vcodec != "none":
        score += 1000
    if acodec and acodec != "none":
        score += 120
    if ext in PREFERRED_VIDEO_EXTS:
        score += 200 - (PREFERRED_VIDEO_EXTS.index(ext) * 20)
    if protocol not in HLS_PROTOCOLS:
        score += 180
    score += height
    score += int(tbr)
    return score


def select_best_video_formats(formats_list):
    grouped = {}

    for fmt in formats_list:
        format_id = fmt.get("format_id")
        ext = fmt.get("ext")
        vcodec = fmt.get("vcodec")
        if not format_id or not ext or not vcodec or vcodec == "none":
            continue

        label = clean_quality_label(fmt)
        old = grouped.get(label)
        if old is None or score_format(fmt) > score_format(old):
            grouped[label] = fmt

    selected = list(grouped.values())
    selected.sort(key=lambda x: (int(x.get("height") or 0), score_format(x)), reverse=True)
    return selected[:10]


def build_format_keyboard(response_json):
    inline_keyboard = []
    selected_formats = select_best_video_formats(response_json.get("formats") or [])

    for fmt in selected_formats:
        format_id = fmt.get("format_id")
        format_ext = (fmt.get("ext") or "mp4").upper()
        quality_label = clean_quality_label(fmt)
        size_label = safe_filesize(fmt)

        video_label = trim_text(f"🎬 {quality_label} • {format_ext} • {size_label}", 28)
        file_label = trim_text(f"📁 {format_ext}", 12)

        cb_string_video = f"video|{format_id}|{fmt.get('ext')}"
        cb_string_file = f"file|{format_id}|{fmt.get('ext')}"

        inline_keyboard.append([
            InlineKeyboardButton(video_label, callback_data=cb_string_video.encode("UTF-8")),
            InlineKeyboardButton(file_label, callback_data=cb_string_file.encode("UTF-8")),
        ])

    if response_json.get("duration") is not None:
        inline_keyboard.append([
            InlineKeyboardButton("🎵 MP3 64K", callback_data="audio|64k|mp3".encode("UTF-8")),
            InlineKeyboardButton("🎵 MP3 128K", callback_data="audio|128k|mp3".encode("UTF-8")),
        ])
        inline_keyboard.append([
            InlineKeyboardButton("🎧 MP3 320K", callback_data="audio|320k|mp3".encode("UTF-8"))
        ])

    if not inline_keyboard:
        format_id = response_json.get("format_id", "best")
        format_ext = response_json.get("ext", "mp4")
        inline_keyboard.append([
            InlineKeyboardButton("🎬 Send Video", callback_data=f"video|{format_id}|{format_ext}".encode("UTF-8")),
            InlineKeyboardButton("📁 Send File", callback_data=f"file|{format_id}|{format_ext}".encode("UTF-8")),
        ])

    return InlineKeyboardMarkup(inline_keyboard)


async def send_log(bot, action, user, link, extra=""):
    if not Config.BIMBO_LOG_CHANNEL or Config.BIMBO_LOG_CHANNEL == 0:
        return

    username = f"@{user.username}" if getattr(user, "username", None) else "N/A"
    first_name = escape_html(getattr(user, "first_name", None) or "User")
    user_mention = f'<a href="tg://user?id={user.id}">{first_name}</a>'

    html_text = (
        "<b>📊 New Bot Activity</b>\n\n"
        f"<b>👤 User:</b> {user_mention} (<code>{user.id}</code>)\n"
        f"<b>🔖 Username:</b> {escape_html(username)}\n"
        f"<b>⚡ Action:</b> {escape_html(action)}\n"
        f"<b>🔗 Link:</b> <code>{escape_html(link)[:1500]}</code>\n"
        f"{extra}"
    )

    try:
        await bot.send_message(
            chat_id=Config.BIMBO_LOG_CHANNEL,
            text=html_text,
            parse_mode=enums.ParseMode.HTML,
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error(f"Log channel HTML error: {e}")
        try:
            plain_text = (
                f"New Bot Activity\n\n"
                f"User: {getattr(user, 'first_name', 'User')} ({user.id})\n"
                f"Username: {username}\n"
                f"Action: {action}\n"
                f"Link: {link}\n"
            )
            await bot.send_message(chat_id=Config.BIMBO_LOG_CHANNEL, text=plain_text, disable_web_page_preview=True)
        except Exception as e2:
            logger.error(f"Log channel fallback error: {e2}")


async def is_direct_download_url(url):
    parsed_url = urlparse(url)
    path = parsed_url.path.lower()

    if any(path.endswith(ext) for ext in DIRECT_FILE_EXTENSIONS):
        return True

    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.head(url, allow_redirects=True) as response:
                    content_type = response.headers.get('Content-Type', '').lower()
                    content_length = response.headers.get('Content-Length')
                    if any(ct in content_type for ct in [
                        'video/', 'audio/', 'application/octet-stream',
                        'application/zip', 'application/pdf', 'application/x-rar',
                        'image/', 'application/vnd.android.package-archive'
                    ]):
                        return True
                    if content_length and content_length.isdigit() and int(content_length) > 1024 * 1024:
                        return True
            except Exception:
                pass

            try:
                async with session.get(url, allow_redirects=True) as response:
                    content_type = response.headers.get('Content-Type', '').lower()
                    content_length = response.headers.get('Content-Length')
                    if any(ct in content_type for ct in [
                        'video/', 'audio/', 'application/octet-stream',
                        'application/zip', 'application/pdf', 'application/x-rar',
                        'image/', 'application/vnd.android.package-archive'
                    ]):
                        return True
                    if content_length and content_length.isdigit() and int(content_length) > 1024 * 1024:
                        return True
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Direct download check failed: {e}")

    return False


def _clean_extracted_url(url: str) -> str:
    """Telegram/Markdown text se asli URL nikaalo. Logs me utm ka tukda aa raha tha."""
    url = str(url or "").strip()
    # Markdown preview/copy kabhi [text](url) bana deta hai
    m = re.search(r"\((https?://[^\s)]+)\)", url)
    if m:
        url = m.group(1)
    # Normal http URL extract
    m = re.search(r"https?://[^\s<>]+", url)
    if m:
        url = m.group(0)
    url = url.strip().strip("`\'\"<>[]()")
    url = url.replace("&amp;", "&")
    return url


def extract_url_parts(text, entities):
    youtube_dl_username = None
    youtube_dl_password = None
    file_name = None
    raw_text = text or ""
    url = raw_text

    # Sabse pehle Telegram entity se exact URL lo. Ye sabse reliable hai.
    for entity in (entities or []):
        entity_type = str(getattr(entity, "type", "")).lower()
        if "text_link" in entity_type and getattr(entity, "url", None):
            url = entity.url
            break
        elif entity_type.endswith("url") or entity_type == "url":
            o = entity.offset
            l = entity.length
            url = raw_text[o:o + l]
            break

    # Agar custom format use kiya: URL | filename | username | password
    # Sirf tab split karo jab left part me actual http ho.
    if "|" in raw_text and raw_text.strip().lower().startswith(("http://", "https://")):
        url_parts = raw_text.split("|")
        if len(url_parts) == 2:
            url = url_parts[0]
            file_name = url_parts[1]
        elif len(url_parts) == 4:
            url = url_parts[0]
            file_name = url_parts[1]
            youtube_dl_username = url_parts[2]
            youtube_dl_password = url_parts[3]

    url = _clean_extracted_url(url)
    file_name = file_name.strip() if file_name is not None else file_name
    youtube_dl_username = youtube_dl_username.strip() if youtube_dl_username is not None else youtube_dl_username
    youtube_dl_password = youtube_dl_password.strip() if youtube_dl_password is not None else youtube_dl_password

    return url, file_name, youtube_dl_username, youtube_dl_password


@BimboBot.on_message(filters.private & ~filters.via_bot & filters.regex(pattern=".*http.*"))
async def echo(bot, update):
    if not await check_verification(bot, update.from_user.id) and Config.BIMBO is True:
        verify_url = await get_token(bot, update.from_user.id, f"https://telegram.me/{Config.BIMBO_BOT_USERNAME}?start=")
        await update.reply_text(
            text=(
                "<b>🔐 Verification Required</b>\n\n"
                "Please verify first, then send your link again."
            ),
            protect_content=True,
            parse_mode=enums.ParseMode.HTML,
            reply_markup=build_verify_markup(verify_url),
        )
        return

    await AddUser(bot, update)
    imog = await update.reply_text(
        "<b>⚡ Processing your request...</b>",
        parse_mode=enums.ParseMode.HTML,
        reply_to_message_id=update.id,
    )

    url, file_name, youtube_dl_username, youtube_dl_password = extract_url_parts(update.text, update.entities)
    original_name = file_name if file_name else "Not Set"

    await send_log(
        bot,
        "Link Received",
        update.from_user,
        url,
        f"<b>📁 Custom Name:</b> <code>{escape_html(original_name)}</code>",
    )

    # ============================================================
    #  xHamster -> apna ALAG engine pehle (yt-dlp se azaad).
    #  Sahi chale to seedha quality buttons dikha do.
    #  Fail ho to neeche normal yt-dlp flow chal jaayega (fallback).
    # ============================================================
    if is_xhamster(url):
        try:
            cookies_path = "cookies.txt" if os.path.exists("cookies.txt") else None
            loop = asyncio.get_event_loop()
            xh = await loop.run_in_executor(None, xh_extract, url, cookies_path)
        except Exception as e:
            logger.warning(f"xhamster engine error: {e}")
            xh = None

        if xh and xh.get("qualities"):
            logger.info("xhamster custom engine OK: %s qualities=%s", url, [q.get("height") for q in xh.get("qualities", [])])
            # button handler ke liye JSON usi jagah save karo (xh marker ke saath)
            xh_json = {
                "title": xh.get("title") or "xHamster video",
                "fulltitle": xh.get("title") or "xHamster video",
                "duration": xh.get("duration"),
                "_xhamster": True,
                "xh_qualities": {str(q["height"]): q["m3u8"] for q in xh["qualities"]},
                "xh_headers": xh.get("headers") or {},
            }
            os.makedirs(Config.BIMBO_DOWNLOAD_LOCATION, exist_ok=True)
            save_ytdl_json_path = os.path.join(
                Config.BIMBO_DOWNLOAD_LOCATION, f"{update.from_user.id}.json")
            with open(save_ytdl_json_path, "w", encoding="utf8") as outfile:
                json.dump(xh_json, outfile, ensure_ascii=False)

            reply_markup = build_xhamster_keyboard_from_engine(xh)
            await imog.delete(True)
            await bot.send_message(
                chat_id=update.chat.id,
                text=(
                    "<b>🎯 Choose quality</b>\n"
                    "<b>✅ xHamster custom engine active</b>\n\n"
                    "Send a photo now to set a custom thumbnail.\n"
                    "Use /delthumbnail to remove a saved thumbnail."
                ),
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML,
                reply_to_message_id=update.id,
            )
            return

        # IMPORTANT: xHamster ke liye yt-dlp -j bilkul mat chalao.
        # Agar apna engine fail hua, user ko clear message do, warna yt-dlp ka
        # purana KeyError('videoModel') confusing error aa jaata hai.
        logger.error("xhamster custom engine FAILED, not using yt-dlp info fallback: %s", url)
        await imog.edit(
            "<b>❌ xHamster custom engine link parse nahi kar paya.</b>\n\n"
            "Bot ko yt-dlp wale old error se bachane ke liye maine yahan stop kar diya hai.\n"
            "Please Koyeb logs me <code>xhamster:</code> wali 5-10 lines bhejo, main exact patch kar dunga.\n\n"
            "Tip: same link ko browser me open karke copy fresh link bhejo.",
            parse_mode=enums.ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return False

    command_to_exec = [
        "yt-dlp",
        "--no-warnings",
        "--geo-bypass",
        "--add-header", "User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "-j",
        url,
    ]

    if Config.BIMBO_HTTP_PROXY != "":
        command_to_exec.extend(["--proxy", Config.BIMBO_HTTP_PROXY])
    if os.path.exists("cookies.txt"):
        command_to_exec.extend(["--cookies", "cookies.txt"])
    if youtube_dl_username is not None:
        command_to_exec.extend(["--username", youtube_dl_username])
    if youtube_dl_password is not None:
        command_to_exec.extend(["--password", youtube_dl_password])

    try:
        process = await asyncio.create_subprocess_exec(
            *command_to_exec,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        await imog.edit("**ERROR:** `yt-dlp` install nahi hai. Requirements install/deploy dobara karo.")
        return False

    stdout, stderr = await process.communicate()
    e_response = stderr.decode(errors="ignore").strip()
    t_response = stdout.decode(errors="ignore").strip()

    if process.returncode != 0:
        await imog.edit("<b>⚠️ yt-dlp failed, checking direct link...</b>", parse_mode=enums.ParseMode.HTML)
        try:
            if await is_direct_download_url(url):
                await imog.delete(True)
                await bot.send_message(
                    chat_id=update.chat.id,
                    text="<b>✅ Direct link detected</b>\nChoose output type:",
                    reply_markup=build_direct_markup(),
                    parse_mode=enums.ParseMode.HTML,
                    reply_to_message_id=update.id,
                )
                return
        except Exception as e:
            logger.error(f"Direct download check error: {e}")

        if "This video is only available for registered users." in e_response or "Sign in" in e_response:
            error_message = (
                "<b>🔐 Login required for this link</b>\n\n"
                "Use this format:\n"
                "<code>URL | filename | username | password</code>\n\n"
                "Or add <code>cookies.txt</code> to the bot files."
            )
        else:
            actual_error = escape_html(e_response.split('\n')[0][:250] or "Invalid or unsupported URL")
            error_message = (
                "<b>❌ Invalid or unsupported URL</b>\n\n"
                f"<b>Reason:</b> <code>{actual_error}</code>"
            )

        await bot.send_message(
            chat_id=update.chat.id,
            text=error_message,
            disable_web_page_preview=True,
            parse_mode=enums.ParseMode.HTML,
            reply_to_message_id=update.id,
        )
        await imog.delete(True)
        return False

    if t_response:
        first_json_line = next((line for line in t_response.splitlines() if line.strip()), "")
        response_json = json.loads(first_json_line)

        os.makedirs(Config.BIMBO_DOWNLOAD_LOCATION, exist_ok=True)
        save_ytdl_json_path = os.path.join(Config.BIMBO_DOWNLOAD_LOCATION, f"{update.from_user.id}.json")
        with open(save_ytdl_json_path, "w", encoding="utf8") as outfile:
            json.dump(response_json, outfile, ensure_ascii=False)

        if is_xhamster(url):
            reply_markup = build_xhamster_keyboard(response_json)
        else:
            reply_markup = build_format_keyboard(response_json)
        await imog.delete(True)
        await bot.send_message(
            chat_id=update.chat.id,
            text=(
                "<b>🎯 Choose format</b>\n\n"
                "Send photo now for custom thumbnail.\n"
                "Use /delthumbnail to remove saved thumbnail.\n\n"
                "<b>🔐 Login format:</b>\n"
                "<code>URL | filename | username | password</code>"
            ),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML,
            reply_to_message_id=update.id,
        )
    else:
        await imog.edit("<b>⚠️ No format found, checking direct link...</b>", parse_mode=enums.ParseMode.HTML)
        try:
            if await is_direct_download_url(url):
                await imog.delete(True)
                await bot.send_message(
                    chat_id=update.chat.id,
                    text="<b>✅ Direct link detected</b>\nChoose output type:",
                    reply_markup=build_direct_markup(),
                    parse_mode=enums.ParseMode.HTML,
                    reply_to_message_id=update.id,
                )
                return
        except Exception as e:
            logger.error(f"Direct download check error: {e}")

        fallback_markup = InlineKeyboardMarkup([[
            InlineKeyboardButton("🎬 Video", callback_data="video=OFL=ENON".encode("UTF-8")),
            InlineKeyboardButton("📁 File", callback_data="file=LFO=NONE".encode("UTF-8")),
        ]])
        await imog.delete(True)
        await bot.send_message(
            chat_id=update.chat.id,
            text="<b>📦 Format selection ready</b>",
            reply_markup=fallback_markup,
            parse_mode=enums.ParseMode.HTML,
            reply_to_message_id=update.id,
        )
