import typing as T
import youtube_dl
import os

def download_subtitles(link: str, fname: str):
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
        'subtitleslangs': ['en'],
        'skip_download': True,
        'postprocessors': postprocessors,
        'outtmpl': fname + '.%(ext)s'
    }
    with youtube_dl.YoutubeDL(params=yt_params) as downloader:
        downloader.download([link])
    
    return fname + ".en.vtt"

if __name__ == '__main__':
    test_download()