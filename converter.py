import os
import ffmpeg

import typing as T
import sys

def extract_audio(input_file: str, burned_subtitles : T.Optional[str] = None, remove_old: bool = False) -> T.Optional[str]:
    return convert_common(input_file, ".mp3", True, remove_old)

def convert_video(input_file: str, burned_subtitles : T.Optional[str] = None, remove_old: bool = False) -> T.Optional[str]:
    return convert_common(input_file, ".mp4", False, burned_subtitles, remove_old)

def convert_common(input_file: str, desired_ending: str, audio_only: bool, burned_subtitles: T.Optional[str], remove_old: bool = False) -> T.Optional[str]:
    if burned_subtitles is not None:
        burned_subtitles = os.path.abspath(burned_subtitles)
        if not os.path.isfile(burned_subtitles):
            # No subtitles!
            print(f"WARNING: Subtitles {burned_subtitles} not found. Skipping.", file=sys.stderr)
            burned_subtitles = None    

    input_file = os.path.abspath(input_file)
    if not os.path.isfile(input_file):
        return None
    output_dir, input_fn = os.path.split(input_file)
    name_only, input_ext = os.path.splitext(input_fn)
    output_fn = f"{name_only}{desired_ending}"
    output_path = os.path.join(output_dir, output_fn)

    if input_ext.lower() == desired_ending.lower() and (burned_subtitles is None):
        # We don't need to copy it
        return output_path

    # There's something we need to do with it!
    # We'll use FFMPEG for all conversion

    # Can't do an in-place conversion
    if os.path.basename(input_file).lower() == os.path.basename(output_path).lower():
        name_only = f"{name_only}_ORIG"
        input_fn = f"{name_only}{input_ext}"
        new_input_file = os.path.join(output_dir, input_fn)
        os.rename(input_file, new_input_file)
        input_file = new_input_file

    # Paths are good now

    # Catch any exceptions made during conversion
    try:        
        # Get the input stream
        strm_input = ffmpeg.input(input_file)

        if audio_only:
            # We just want the audio
            strm_final = strm_input.audio
        else:
            # We want both audio and video!
            if burned_subtitles is None:
                # No subtitles. Just take it as is
                strm_final = strm_input
            else:
                # We want to pass the video through a burning-stage
                subtitle_relpath = os.path.relpath(burned_subtitles)

                # Extract video/ audio
                strm_video = strm_input.video
                strm_audio = strm_input.audio

                # Burn subtitles into the video
                strm_subbed = strm_video.filter("subtitles", subtitle_relpath)

                # Combined the burned video back with the audio
                strm_final = ffmpeg.concat(strm_subbed, strm_audio, v=1, a=1)
        
        # Make the output pin
        strm_output = strm_final.output(output_path)

        # Now we have the output pin  / compute graph
        # Add program-level args
        ffmpeg_globals = [
            # Overwrite files as needed
            "-y",
            # Print only warnings and errors
            "-loglevel",
            "warning"
        ]


        # Apply globals
        strm_output = strm_output.global_args(*ffmpeg_globals)

        # Now, run FFMPEG conversion!
        strm_output.run()
    except Exception as err:
        print(f"Conversion Error: {err}", file=sys.stderr)
        if os.path.exists(output_path):
            os.remove(output_path)
        return None
    else:
        # Conversion success!
        if remove_old and input_fn.lower() != output_fn.lower():
            os.remove(input_file)
        return output_path

        
      
