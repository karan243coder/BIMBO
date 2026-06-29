# BIMBO URL Bot
# Powered by BIMBO
# Support: @Bimbo69

import os
import re
from os import environ, getenv

id_pattern = re.compile(r'^\d+$')

def is_enabled(value, default):
    if not value:
        return default
    if value.lower() in ["true", "yes", "1", "enable", "y"]:
        return True
    elif value.lower() in ["false", "no", "0", "disable", "n"]:
        return False
    else:
        return default

class Config(object):
    # Bot Information
    BIMBO_BOT_TOKEN = os.environ.get("BIMBO_BOT_TOKEN")
    BIMBO_BOT_USERNAME = os.environ.get("BIMBO_BOT_USERNAME", "")

    # The Telegram API things
    BIMBO_API_ID = int(os.environ.get("BIMBO_API_ID", "0"))
    BIMBO_API_HASH = os.environ.get("BIMBO_API_HASH")

    # the download location, where the HTTP Server runs
    BIMBO_DOWNLOAD_LOCATION = "./DOWNLOADS"

    # Telegram maximum file upload size
    BIMBO_MAX_FILE_SIZE = 50000000
    BIMBO_TG_MAX_FILE_SIZE = 4194304000
    BIMBO_FREE_USER_MAX_FILE_SIZE = 50000000

    # chunk size that should be used with requests/aiohttp direct downloads
    # 128 bytes bahut slow hai; env se override kar sakte ho.
    BIMBO_CHUNK_SIZE = int(os.environ.get("BIMBO_CHUNK_SIZE", str(1024 * 1024)))

    # proxy for accessing youtube-dl in GeoRestricted Areas
    BIMBO_HTTP_PROXY = ""

    # maximum message length in Telegram
    BIMBO_MAX_MESSAGE_LENGTH = 4096

    # set timeout for subprocess
    BIMBO_PROCESS_MAX_TIMEOUT = 3600

    # your telegram account id
    BIMBO_OWNER_ID = int(os.environ.get("BIMBO_OWNER_ID", "0"))
    BIMBO_SESSION_NAME = "BIMBO_SESSION"

    # database uri (mongodb)
    BIMBO_DATABASE_URL = os.environ.get("BIMBO_DATABASE_URL")

    BIMBO_MAX_RESULTS = "50"

    # channel information
    BIMBO_LOG_CHANNEL = int(os.environ.get("BIMBO_LOG_CHANNEL", "0"))

    # if you want force subscribe then give your channel id below else leave blank
    bimbo_update_channel = environ.get('BIMBO_UPDATES_CHANNEL', '')
    BIMBO_UPDATES_CHANNEL = int(bimbo_update_channel) if bimbo_update_channel and id_pattern.search(bimbo_update_channel) else None

    # Url Shortner Information
    BIMBO = is_enabled(environ.get('BIMBO', 'False'), False)
    BIMBO_URL = environ.get('BIMBO_URL', 'modijiurl.com')
    BIMBO_API = environ.get('BIMBO_API', '')
    BIMBO_TUTORIAL = os.environ.get("BIMBO_TUTORIAL", "https://t.me/How_To_Open_Linkl")

# BIMBO URL Bot
# Powered by BIMBO
# Support: @Bimbo69
