from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


class Translation(object):

    BIMBO_START_TEXT = """
<b>👋 Hello {}!</b>

<b>I am an advanced URL uploader bot.</b>

Send me any valid link and I can upload it to Telegram as:
• 📁 File
• 🎬 Video
• 🎵 Audio

<b>Features:</b>
• Custom thumbnail support
• Direct link support
• yt-dlp powered downloads
• Clean progress updates

<b>Powered by:</b> <a href="https://t.me/bimbobot69">Bimbo</a>
"""

    BIMBO_HELP_TEXT = """
<b>🛠 Features</b>

• Upload HTTP/HTTPS links to Telegram
• Send as file, video, or audio
• Supports many yt-dlp compatible websites
• Permanent custom thumbnail support
• Broadcast command support

<b>📌 How to use</b>

1. Send a link
2. Select your preferred format
3. Wait for download and upload to complete

<b>💡 Pro tip:</b>
Send a photo before selecting a format to use it as thumbnail.
Use /delthumbnail to remove your saved thumbnail.
"""

    BIMBO_ABOUT_TEXT = """
<b>ℹ️ About This Bot</b>

<b>🤖 Name:</b> URL Uploader Bot
<b>🌀 Channel:</b> <a href="https://t.me/bimbobot69">Join Updates Channel</a>
<b>🐍 Language:</b> <a href="https://www.python.org/">Python 3</a>
<b>⚙️ Framework:</b> <a href="https://docs.pyrogram.org/">Pyrogram</a>
<b>👨‍💻 Developer:</b> <a href="https://t.me/Bimbo69">Bimbo</a>
"""

    BIMBO_START_BUTTONS = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton('📢 Update Channel', url='https://t.me/bimbobot69')
        ], [
            InlineKeyboardButton('❓ Help', callback_data='help'),
            InlineKeyboardButton('ℹ️ About', callback_data='about')
        ]]
    )

    BIMBO_HELP_BUTTONS = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton('📢 Update Channel', url='https://t.me/bimbobot69')
        ], [
            InlineKeyboardButton('🏠 Home', callback_data='home'),
            InlineKeyboardButton('ℹ️ About', callback_data='about')
        ], [
            InlineKeyboardButton('✖️ Close', callback_data='close')
        ]]
    )

    BIMBO_ABOUT_BUTTONS = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton('📢 Update Channel', url='https://t.me/bimbobot69')
        ], [
            InlineKeyboardButton('🏠 Home', callback_data='home'),
            InlineKeyboardButton('❓ Help', callback_data='help')
        ], [
            InlineKeyboardButton('✖️ Close', callback_data='close')
        ]]
    )

    BIMBO_ERROR = "<b>❌ Error:</b> <code>{}</code>"

    BIMBO_FORMAT_SELECTION = """
<b>🎯 Select your preferred format</b>

File size may be approximate.
If you want a custom thumbnail, send a photo before or just after tapping a format button.

Use /delthumbnail to remove your saved thumbnail.
"""

    BIMBO_SET_CUSTOM_USERNAME_PASSWORD = """
<b>🔐 Premium / Login Format</b>

If a website needs login, send your link like this:
<code>URL | filename | username | password</code>
"""

    BIMBO_DOWNLOAD_START = "<b>📥 Downloading...</b>"
    BIMBO_UPLOAD_START = "<b>📤 Uploading...</b>"

    BIMBO_RCHD_TG_API_LIMIT = """
<b>⚠️ Upload limit reached</b>

Downloaded in: {} seconds
Detected file size: {}

Sorry, I cannot upload files bigger than the allowed Telegram limit.
"""

    BIMBO_AFTER_SUCCESSFUL_UPLOAD_MSG = """
<b>✅ Uploaded successfully</b>

Thanks for using me.
<b>Join:</b> https://t.me/bimbobot69
"""

    BIMBO_AFTER_SUCCESSFUL_UPLOAD_MSG_WITH_TS = """
<b>✅ Upload completed</b>

📥 Downloaded in: {} seconds
📤 Uploaded in: {} seconds

<b>Join:</b> https://t.me/bimbobot69
"""

    BIMBO_SAVED_CUSTOM_THUMB_NAIL = "<b>✅ Custom thumbnail saved successfully.</b>\nThis image will be used for your next uploads."
    BIMBO_DEL_ETED_CUSTOM_THUMB_NAIL = "<b>✅ Custom thumbnail deleted successfully.</b>"
    BIMBO_CUSTOM_CAPTION_UL_FILE = "<b>{}</b>"
    BIMBO_NO_VOID_FORMAT_FOUND = "<b>❌ Unable to process this link.</b>\n{}"
    BIMBO_REPLY_TO_MEDIA_ALBUM_TO_GEN_THUMB = "<b>Reply to a media album with /generatecustomthumbnail to create a custom thumbnail.</b>"

    BIMBO_ERR_ONLY_TWO_MEDIA_IN_ALBUM = """
<b>This media album should contain only two photos.</b>

Please send the album again with only two photos and then try again.
"""

    BIMBO_CANCEL_STR = "<b>❌ Process cancelled.</b>"
    BIMBO_ZIP_UPLOADED_STR = "<b>✅ Uploaded {} files in {} seconds.</b>"

    BIMBO_SLOW_URL_DECED = """
<b>⚠️ This URL is too slow.</b>

Please send a faster direct link so I can download and upload it properly.
"""

    BIMBO_ERROR_YTDLP = "<b>Please report this issue to the yt-dlp project and make sure you are using the latest version.</b>"
