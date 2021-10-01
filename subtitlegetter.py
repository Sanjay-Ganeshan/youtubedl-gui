import typing as T
import youtube_dl
import os
import sys

def download_subtitles(link: str, fname: str, lang: str = "en"):
    fname = os.path.abspath(fname)
    outpath = os.path.splitext(fname)[0]

    postprocessors = []
    postprocessors.append(
        {
            'key': 'FFmpegSubtitlesConvertor',
            'format': 'vtt'
        }
    )
    yt_params = {
        'writesubtitles': True,
        'subtitleslangs': [lang],
        'skip_download': True,
        'postprocessors': postprocessors,
        'outtmpl': outpath + '.%(ext)s'
    }

    try:
        with youtube_dl.YoutubeDL(params=yt_params) as downloader:
            downloader.download([link])
    except Exception as exc:
        print("WARNING: Subtitle download failed.", file=sys.stderr)    
    
    return outpath + ".en.vtt"
    

if __name__ == '__main__':
    test_download()