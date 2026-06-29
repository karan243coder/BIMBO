import os
import logging
from config import Config
from pyrogram import Client as BimboBot

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("pymongo").setLevel(logging.WARNING)
logging.getLogger("pymongo.topology").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # create download directory, if not exist
    if not os.path.isdir(Config.BIMBO_DOWNLOAD_LOCATION):
        os.makedirs(Config.BIMBO_DOWNLOAD_LOCATION)
    
    plugins = dict(root="plugins")
    
    BIMBO_CLIENT = BimboBot(
        name="BIMBO_BOT",
        bot_token=Config.BIMBO_BOT_TOKEN,
        api_id=Config.BIMBO_API_ID,
        api_hash=Config.BIMBO_API_HASH,
        plugins=plugins
    )
    
    BIMBO_CLIENT.run()
