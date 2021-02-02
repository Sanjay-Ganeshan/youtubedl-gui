import os
import ffmpeg

import typing as T

def extract_audio(input_file: str, remove_old: bool = False) -> T.Optional[str]:
    return convert_common(input_file, ".mp3", True, remove_old)

def convert_video(input_file: str, remove_old: bool = False) -> T.Optional[str]:
    return convert_common(input_file, ".mp4", False, remove_old)

def convert_common(input_file: str, desired_ending: str, audio_only: bool, remove_old: bool = False) -> T.Optional[str]:
    input_file = os.path.abspath(input_file)
    if input_file.endswith(desired_ending):
        return input_file
    if not os.path.isfile(input_file):
        return None
    output_dir, input_fn = os.path.split(input_file)
    name_only = os.path.splitext(input_fn)[0]
    output_fn = f"{name_only}{desired_ending}"
    output_path = os.path.join(output_dir, output_fn)
    if os.path.isfile(output_path):
        return output_path
    try:
        inp = ffmpeg.input(input_file)
        if audio_only:
            inp = inp.audio
        inp.output(output_path).run()
    except Exception as err:
        print("Conversion Error", err)
        if os.path.exists(output_path):
            os.remove(output_path)
    else:
        if remove_old and input_fn != output_fn:
            os.remove(input_file)
    return output_path

        
      
