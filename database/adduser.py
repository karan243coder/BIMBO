# BIMBO URL Bot
# Powered by BIMBO
# Support: @Bimbo69

from pyrogram import Client
from database.access import bimbo
from pyrogram.types import Message
from config import Config

LOG_TEXT_P = """#NewUser
ID - <code>{}</code>
Nᴀᴍᴇ - {}"""


async def AddUser(bot: Client, update: Message):
    if not await bimbo.is_user_exist(update.from_user.id):
           await bimbo.add_user(update.from_user.id)
           await bot.send_message(Config.BIMBO_LOG_CHANNEL, LOG_TEXT_P.format(update.from_user.id, update.from_user.mention))
