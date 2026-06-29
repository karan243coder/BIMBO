# BIMBO URL Bot
# Powered by BIMBO
# Support: @Bimbo69

from config import Config
from database.database import Database

bimbo = Database(Config.BIMBO_DATABASE_URL, Config.BIMBO_SESSION_NAME)
