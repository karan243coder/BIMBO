# -*- coding: utf-8 -*-
# BIMBO URL Bot
# Powered by BIMBO
# Support: @Bimbo69

import os
import random
import logging
from PIL import Image, ImageOps
from config import Config
from pyrogram import filters
from translation import Translation
from database.access import bimbo
from database.adduser import AddUser
from pyrogram import Client as BimboBot
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
from helper_funcs.help_Nekmo_ffmpeg import take_screen_shot

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

THUMB_MAX_EDGE = 320
THUMB_DEFAULT_VIDEO_SIZE = (320, 180)
THUMB_DEFAULT_IMAGE_SIZE = (320, 320)
THUMB_QUALITY = 88


def ensure_thumb_dir():
    os.makedirs(Config.BIMBO_DOWNLOAD_LOCATION, exist_ok=True)


def get_thumb_path(user_id: int) -> str:
    ensure_thumb_dir()
    return os.path.join(Config.BIMBO_DOWNLOAD_LOCATION, f"{user_id}.jpg")


def get_target_thumbnail_size(video_width: int = 0, video_height: int = 0):
    if video_width and video_height:
        ratio = float(video_width) / float(video_height)
        if ratio >= 1:
            target_width = THUMB_MAX_EDGE
            target_height = max(90, int(target_width / ratio))
        else:
            target_height = THUMB_MAX_EDGE
            target_width = max(90, int(target_height * ratio))
        return target_width, target_height
    return THUMB_DEFAULT_VIDEO_SIZE


def normalize_thumbnail(input_path: str, output_path: str = None, target_size=None, crop_to_fit: bool = False) -> str | None:
    """Convert image to Telegram-friendly JPEG thumbnail."""
    try:
        if not input_path or not os.path.exists(input_path):
            return None

        output_path = output_path or input_path
        target_size = target_size or THUMB_DEFAULT_IMAGE_SIZE

        with Image.open(input_path) as img:
            img = img.convert("RGB")
            if crop_to_fit:
                final_img = ImageOps.fit(
                    img,
                    target_size,
                    method=Image.Resampling.LANCZOS,
                    centering=(0.5, 0.5)
                )
            else:
                final_img = ImageOps.contain(img, target_size, method=Image.Resampling.LANCZOS)
            final_img.save(output_path, "JPEG", quality=THUMB_QUALITY, optimize=True)
        return output_path
    except Exception as e:
        logger.error(f"Thumbnail normalize error: {e}")
        return None


async def download_user_thumbnail(bot, user_id: int, target_size=None, crop_to_fit: bool = False):
    db_thumbnail = await bimbo.get_thumbnail(user_id)
    if db_thumbnail is None:
        return None

    thumb_image_path = get_thumb_path(user_id)
    try:
        downloaded_path = await bot.download_media(message=db_thumbnail, file_name=thumb_image_path)
        return normalize_thumbnail(downloaded_path, thumb_image_path, target_size=target_size, crop_to_fit=crop_to_fit)
    except Exception as e:
        logger.error(f"Custom thumbnail download error: {e}")
        return None


def pick_screenshot_second(duration: int) -> int:
    duration = int(duration or 0)
    if duration <= 1:
        return 0
    if duration <= 10:
        return max(1, duration // 2)

    candidate_points = [
        max(1, int(duration * 0.15)),
        max(1, int(duration * 0.30)),
        max(1, int(duration * 0.45)),
        max(1, int(duration * 0.60)),
        max(1, int(duration * 0.75)),
    ]
    return random.choice(candidate_points)


async def generate_video_screenshot(download_directory: str, duration: int, user_id: int, target_size=None):
    try:
        output_dir = os.path.dirname(download_directory)
        shot_second = pick_screenshot_second(duration)
        screenshot = await take_screen_shot(download_directory, output_dir, shot_second)
        if screenshot and os.path.exists(screenshot):
            return normalize_thumbnail(
                screenshot,
                get_thumb_path(user_id),
                target_size=target_size,
                crop_to_fit=True,
            )
    except Exception as e:
        logger.error(f"Video screenshot error: {e}")
    return None


def extract_media_metadata(download_directory):
    width = 0
    height = 0
    duration = 0

    try:
        parser = createParser(download_directory)
        if not parser:
            return width, height, duration

        with parser:
            metadata = extractMetadata(parser)

        if metadata is not None:
            if metadata.has("duration"):
                duration = metadata.get("duration").seconds
            if metadata.has("width"):
                width = metadata.get("width")
            if metadata.has("height"):
                height = metadata.get("height")
    except Exception as e:
        logger.error(f"Metadata read error for {download_directory}: {e}")

    return width or 0, height or 0, duration or 0


@BimboBot.on_message(filters.private & filters.photo)
async def save_photo(bot, update):
    await AddUser(bot, update)
    await bimbo.set_thumbnail(update.from_user.id, thumbnail=update.photo.file_id)
    await bot.send_message(
        chat_id=update.chat.id,
        text=Translation.BIMBO_SAVED_CUSTOM_THUMB_NAIL,
        reply_to_message_id=update.id
    )


@BimboBot.on_message(filters.private & filters.command("delthumbnail"))
async def delthumbnail(bot, update):
    await AddUser(bot, update)
    await bimbo.set_thumbnail(update.from_user.id, thumbnail=None)
    await bot.send_message(
        chat_id=update.chat.id,
        text=Translation.BIMBO_DEL_ETED_CUSTOM_THUMB_NAIL,
        reply_to_message_id=update.id
    )


@BimboBot.on_message(filters.private & filters.command("viewthumbnail"))
async def viewthumbnail(bot, update):
    await AddUser(bot, update)
    thumbnail = await bimbo.get_thumbnail(update.from_user.id)
    if thumbnail is not None:
        await bot.send_photo(
            chat_id=update.chat.id,
            photo=thumbnail,
            caption="**Your current saved thumbnail ✅**",
            reply_to_message_id=update.id
        )
    else:
        await update.reply_text(text="**No thumbnail found 🙁**")


async def Gthumb01(bot, update):
    """Get custom thumbnail for audio/document uploads."""
    return await download_user_thumbnail(
        bot,
        update.from_user.id,
        target_size=THUMB_DEFAULT_IMAGE_SIZE,
        crop_to_fit=False,
    )


async def Gthumb02(bot, update, duration, download_directory):
    """Get video-aligned thumbnail so it looks naturally fitted inside the video frame."""
    video_width, video_height, _ = extract_media_metadata(download_directory)
    target_size = get_target_thumbnail_size(video_width, video_height)

    custom_thumb = await download_user_thumbnail(
        bot,
        update.from_user.id,
        target_size=target_size,
        crop_to_fit=True,
    )
    if custom_thumb is not None:
        return custom_thumb

    auto_thumb = await generate_video_screenshot(download_directory, duration, update.from_user.id, target_size=target_size)
    return auto_thumb


async def Mdata01(download_directory):
    width, height, duration = extract_media_metadata(download_directory)
    return width, height, duration


async def Mdata02(download_directory):
    width, _, duration = extract_media_metadata(download_directory)
    return width, duration


async def Mdata03(download_directory):
    _, _, duration = extract_media_metadata(download_directory)
    return duration


async def get_flocation(download_directory, extension):
    candidates = [
        download_directory,
        download_directory + ".mkv",
        download_directory + "." + extension,
        os.path.splitext(download_directory)[0] + ".mkv",
        os.path.splitext(download_directory)[0] + "." + extension,
    ]

    for file_directory in candidates:
        try:
            file_size = os.stat(file_directory).st_size
            return file_size, file_directory
        except Exception:
            continue

    return 0, download_directory
