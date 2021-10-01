import typing as T

from . import DEFAULT_DOWNLOAD_DIR
from .subtitlegetter import download_subtitles
from .dlmutex import downloading_lock

import pafy
import youtube_dl
import uuid
import requests

import os
import threading

from .converter import extract_audio, convert_video
from .api_key import YOUTUBE_API_KEY
from .tagger import tag_file

import urllib.parse as urlparse

PLACEHOLDER_IMG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "placeholder.png")

def extract_url_ids(url: str) -> T.Tuple[T.Optional[str], T.Optional[str]]:
    parsed_url = urlparse.urlparse(url)
    args = urlparse.parse_qs(parsed_url.query)
    video_id = args.get("v", [None])[0]
    list_id = args.get("list", [None])[0]
    return video_id, list_id

def playlist_items(playlist_id_or_url: str) -> T.Optional[T.List[str]]:
    if playlist_id_or_url.startswith("http"):
        _, list_id = extract_url_ids(playlist_id_or_url)
    else:
        list_id = playlist_id_or_url
    
    if list_id is None:
        return None
    else:
        base_url = "https://youtube.googleapis.com/youtube/v3/playlistItems"
        api_url = f"{base_url}?part=id,contentDetails&maxResults=25&playlistId={list_id}&key={YOUTUBE_API_KEY}"
        response = requests.get(api_url)
        has_pages = True
        found_items = None
        while has_pages:
            if response.ok:
                # Valid playlist
                response_body = response.json()

                # Initialize list
                if found_items is None:
                    found_items = []
                
                listed_ids = [each_item.get("contentDetails", {}).get("videoId", None) for each_item in response_body["items"]]
                listed_ids = [i for i in listed_ids if i is not None]
                found_items.extend(listed_ids)
                
                # Get more pages as needed
                if "nextPageToken" in response_body:
                    nextTok = response_body["nextPageToken"]
                    response = requests.get(f"{api_url}&pageToken={nextTok}")
                    has_pages = True
                else:
                    has_pages = False
                
            else:
                # Not a valid playlist
                has_pages = False
        
        # Now we've got everything
        return found_items

def filenamify(s):
    good_chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.-_0123456789'
    return "".join([c for c in s if c in good_chars])

class DownloadEntry(object):
    def __init__(self):
        self.id = str(uuid.uuid4())
        
        # Youtube information
        self.url = None
        self.pafy = None
        self.audio_only = False
        self.subtitles = False
        self.burn_subtitles = False
        self.download_progress = None
        self.download_thread = None

        self.progress_listeners = []
        self.done_listeners = []

        # Local information
        self.output_dir = None
        self.output_file = None
        self.output_extension = None

        # Tag information
        self.title = None
        self.author = None

        self.editable = True
        self.is_done = False
    
    def bind(self, progress: T.Optional[T.Callable[[float], T.NoReturn]] = None, done: T.Optional[T.Callable[[bool], T.NoReturn]] = None):
        if progress is not None:
            self.progress_listeners.append(progress)
        if done is not None:
            self.done_listeners.append(done)    

    def set_url(self, youtube_url: T.Optional[str] = None) -> bool:
        if youtube_url == self.url:
            return True
        self.url = youtube_url

        if youtube_url is None:
            self.pafy = None
            return True

        else:    
            try:
                self.pafy = pafy.new(youtube_url, basic=True)
            except ValueError:
                # Not a valid URL / video ID
                self.set_url(None)
                return False
            except OSError:
                # Not a real video
                self.set_url(None)
                return False
            else:
                return True
    
    def valid(self) -> bool:
        return self.url is not None and self.pafy is not None

    def vtitle(self) -> str:
        if self.pafy is None:
            return ""
        return self.pafy.title
    
    def vauthor(self) -> str:
        if self.pafy is None:
            return ""
        return self.pafy.author
    
    def vthumbnail(self) -> str:
        if self.pafy is None:
            return PLACEHOLDER_IMG
        return self.pafy.getbestthumb()

    def vduration(self) -> int:
        if self.pafy is None:
            return 0
        return self.pafy.length
    
    def vformattedduration(self) -> str:
        total_seconds = self.vduration()
        nseconds = total_seconds % 60
        total_minutes = total_seconds // 60
        nminutes = total_minutes % 60
        total_hours = total_minutes // 60
        nhours = total_hours

        if nhours > 0:
            return "%dhr %02dm" % (nhours, nminutes)
        elif nminutes > 0:
            return "%dm %02ds" % (nminutes, nseconds)
        else:
            return "%ds" % (nseconds,)

    def otitle(self) -> str:
        if self.title is None:
            return self.vtitle()
        else:
            return self.title
    
    def oauthor(self) -> str:
        if self.author is None:
            return self.vauthor()
        else:
            return self.author

    def oextension(self) -> str:
        if self.output_extension is not None:
            return f"{self.output_extension}"
        else:
            if self.audio_only:
                return ".mp3"
            else:
                return ".mp4"

    def odir(self) -> str:
        if self.output_dir is None:
            return DEFAULT_DOWNLOAD_DIR
        else:
            return self.output_dir
    
    def ofilename(self) -> str:
        if self.output_file is None:
            return filenamify(f"{self.otitle()}_{self.oauthor()}{self.oextension()}")
        
        else:
            return filenamify(f"{self.output_file}{self.oextension()}")

    def opath(self) -> str:
        return os.path.join(self.odir(), self.ofilename())
    
    def set_output_dir(self, output_dir: T.Optional[str] = None) -> T.NoReturn:
        self.output_dir = output_dir
    
    def set_output_name(self, output_name: T.Optional[str] = None) -> T.NoReturn:
        self.output_file = output_name
    
    def set_download_type(self, audio_only: bool) -> T.NoReturn:
        self.audio_only = audio_only
    
    def set_download_subtitles(self, download_subtitles: bool) -> T.NoReturn:
        self.subtitles = download_subtitles

    def exists_locally(self) -> bool:
        return os.path.isfile(self.opath())
    
    def download(self, overwrite = False) -> bool:
        if self.download_thread is not None:
            return True

        self.editable = False
        if self.exists_locally() and not overwrite:
            self.download_progress = 1.0
            for each_callback in self.progress_listeners:
                each_callback(1.0)
            for each_callback in self.done_listeners:
                each_callback(True)
            return True
        
        if self.pafy is None:
            # Something's wrong, do nothing
            self.download_progress = 0.0
            for each_callback in self.progress_listeners:
                each_callback(0.0)
            for each_callback in self.done_listeners:
                each_callback(False)
            return False
        
        if self.audio_only:
            target = self._download_audio
        else:
            target = self._download_video
        
        self.download_thread = threading.Thread(target=target, daemon=True)
        self.download_thread.start()
    
    def _download_callback(self, total_bytes, unit_done, percentage, rate, eta):
        self.download_progress = percentage
        for each_callback in self.progress_listeners:
            each_callback(self.download_progress)

    def _download_common(self, stream, postprocess):
        self.download_progress = 0.0

        # Download the video / audio stream
        dl_path = f"{os.path.splitext(self.opath())[0]}.{stream.extension}"
        stream.download(filepath=dl_path, callback=self._download_callback)

        # Now it's done. Download the subtitles if we need them.
        if self.subtitles:
            subtitles_path = self._download_subtitles()
        else:
            subtitles_path = None

        burned_subtitle_path = None if not self.burn_subtitles else subtitles_path

        converted_path = postprocess(dl_path, burned_subtitles = burned_subtitle_path, remove_old=True)

        if converted_path is None:
            # Failure!
            for each_callback in self.done_listeners:
                each_callback(False)
    
        else:
            output_dir, converted_fn = os.path.split(converted_path)
            
            converted_base, converted_ext = os.path.splitext(converted_fn)
            self.output_dir = output_dir
            self.output_file = converted_base
            self.output_extension = converted_ext


            for each_callback in self.done_listeners:
                each_callback(True)

    def _download_audio(self):
        with downloading_lock:
            audiostream = self.pafy.getbestaudio()
            self._download_common(audiostream, extract_audio)
            # Finally, tag it!
            tag_file(self.opath(), self.otitle(), self.oauthor())
            self.is_done = True

    def _download_video(self):
        with downloading_lock:
            videostream = self.pafy.getbest()
            self._download_common(videostream, convert_video)
            self.is_done = True

    def _download_subtitles(self):
        if self.url is not None:
            return download_subtitles(self.url, self.opath())
        else:
            return None

    def reveal_in_explorer(self):
        if self.exists_locally():
            command = f"explorer {self.odir()}"
            os.system(command)
        
    def is_downloadable(self) -> bool:
        return self.pafy is not None and self.download_thread is None and self.editable and not self.exists_locally()

    def is_forgettable(self) -> bool:
        return self.download_thread is None or self.is_done

    def is_revealable(self) -> bool:
        return self.exists_locally()

