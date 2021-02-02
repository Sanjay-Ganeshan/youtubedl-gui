from mutagen.easyid3 import EasyID3 as id3

def tag_file(mp3_path, title = None, artist = None):
    mp3_file = id3(mp3_path)
    if title is not None:
        mp3_file["title"] = title
    if artist is not None:
        mp3_file["artist"] = artist
    mp3_file.save()
