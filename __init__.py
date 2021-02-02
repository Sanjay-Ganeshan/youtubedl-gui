from .api_key import YOUTUBE_API_KEY
import pafy
pafy.set_api_key(YOUTUBE_API_KEY)
print("Set API key!")

import os
mydir = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DOWNLOAD_DIR = os.path.join(mydir, "Downloads")
