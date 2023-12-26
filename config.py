import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Discord bot token https://www.writebots.com/discord-bot-token/
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
# MODEL_PATH = os.getenv('MODEL')
FFMPEG_PATH = os.getenv('FFMPEG')
# ytdl_logger = logging.getLogger("ytdl-ignore")
# ytdl_logger.disabled = True

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'geo_bypass': True,
    'ignoreerrors': True,
    'skip_download': True,
    'lazy_playlist': True,
    'include_ads': False,
    'default_search': 'auto',
    'quiet': True,
    # 'logger': ytdl_logger,
    'extract_flat': 'in_playlist',
    'flat_playlist': True,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }]
}

FFMPEG_OPTIONS = {
    'executable': FFMPEG_PATH,
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -loglevel panic',
    'options': '-vn',
}
