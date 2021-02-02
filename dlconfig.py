import typing as T


class DLConfig(object):
    def __init__(self,
        audio_only: bool = True,
        include_subtitles: bool = False
        ):
        self.audio_only = audio_only
        self.include_subtitles = include_subtitles
    
    def validate(self):
        assert not (self.include_subtitles and self.audio_only), "Only video downloads may include subtitles"
        

    