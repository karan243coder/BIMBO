# BIMBO URL Bot
# Powered by BIMBO
# Support: @Bimbo69

import logging
from config import Config
from pyrogram import filters
from pyrogram.errors import UserNotParticipant
from pyrogram import Client as BimboBot
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from plugins.youtube_dl_button import youtube_dl_call_back
from plugins.dl_button import ddl_call_back
from translation import Translation
from plugins.forcesub import get_invite_link

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

@BimboBot.on_callback_query(filters.regex('^X0$'))
async def delt(bot, update):
    await update.message.delete(True)

@BimboBot.on_callback_query()
async def button(bot, update):
    try:
        if "|" in update.data:
            await youtube_dl_call_back(bot, update)
        elif "=" in update.data:
            await ddl_call_back(bot, update)
        elif update.data == "home":
            await update.message.edit(
                text=Translation.BIMBO_START_TEXT.format(update.from_user.mention),
                reply_markup=Translation.BIMBO_START_BUTTONS,
            )
        elif update.data == "help":
            await update.message.edit(
                text=Translation.BIMBO_HELP_TEXT,
                reply_markup=Translation.BIMBO_HELP_BUTTONS,
            )
        elif update.data == "about":
            await update.message.edit(
                text=Translation.BIMBO_ABOUT_TEXT,
                reply_markup=Translation.BIMBO_ABOUT_BUTTONS,
            )
        elif "close" in update.data:
            await update.message.delete(True)
        elif "refreshForceSub" in update.data:
            if Config.BIMBO_UPDATES_CHANNEL:
                if str(Config.BIMBO_UPDATES_CHANNEL).startswith("-100"):
                    channel_chat_id = int(Config.BIMBO_UPDATES_CHANNEL)
                else:
                    channel_chat_id = Config.BIMBO_UPDATES_CHANNEL
                try:
                    user = await bot.get_chat_member(channel_chat_id, update.message.chat.id)
                    if user.status == "kicked":
                        await update.message.edit(
                            text="Sorry Sir, You are Banned to use me. Contact my [owner](https://t.me/bimbobot69).",
                            disable_web_page_preview=True
                        )
                        return
                except UserNotParticipant:
                    chat_id = channel_chat_id
                    invite_link = await get_invite_link(bot, chat_id)
                    await update.message.edit(
                        text="**I like Your Smartness But Don't Be Oversmart! 😑**\n\n",
                        reply_markup=InlineKeyboardMarkup(
                            [
                                [
                                    InlineKeyboardButton("🤖 Join Updates Channel", url=invite_link.invite_link)
                                ],
                                [
                                    InlineKeyboardButton("🔄 Refresh 🔄", callback_data="refreshForceSub")
                                ]
                            ]
                        )
                    )
                    return
                except Exception:
                    await update.message.edit(
                        text="Something went Wrong. Contact my [owner](https://t.me/bimbobot69).",
                        disable_web_page_preview=True
                    )
                    return
            await update.message.edit(
                text=Translation.BIMBO_START_TEXT.format(update.from_user.mention),
                reply_markup=Translation.BIMBO_START_BUTTONS,
            )
    except Exception as e:
        logger.error(f"Callback error: {e}")
        try:
            await update.message.edit(text=f"**Error:** {str(e)}")
        except:
            pass
