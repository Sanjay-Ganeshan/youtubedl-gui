import os
import typing as T

from .dlconfig import DLConfig

from api_key import YOUTUBE_API_KEY

def download(youtube_url:str, cfg: DLConfig, fpath: str, overwrite = False):
    if os.path.exists(fpath):
        if os.path.isfile(fpath):
            if not overwrite:
                raise FileExistsError("Provided file already exists")
        else:
            raise FileExistsError("Provided download path is a folder")
    
    # Make a pafy instance
    pafy.new(youtube_url)



