#!/usr/bin/env python3
"""Pull the San Üni post artwork out of a screen recording.

Finds the post's bounds in a frame, then crops and conditions each element
the way the Figma rebuild consumes it. Run with the recording path as argv[1].

Needs: pillow, numpy, and an ffmpeg binary (imageio-ffmpeg supplies one).
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

GREEN = np.array([155, 255, 129])   # #9BFF81, the colour-state ground
OUT = Path(__file__).parent / "assets"


def frame_at(video, seconds, dest):
    import imageio_ffmpeg
    subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-ss", str(seconds), "-i", str(video),
         "-frames:v", "1", "-y", str(dest)],
        check=True, capture_output=True,
    )
    return Image.open(dest).convert("RGB")


def post_bounds(frame):
    """The post is the only full-width green band in the frame."""
    px = np.asarray(frame).astype(int)
    green_rows = [
        y for y in range(px.shape[0])
        if px[y, 5, 1] > 200 and px[y, 5, 0] > 100 and px[y, 5, 2] < 200
    ]
    return green_rows[0], green_rows[-1] + 1


def main(video):
    OUT.mkdir(exist_ok=True)
    ref = Path(__file__).parent / "reference"
    ref.mkdir(exist_ok=True)

    tmp_colour = ref / "_frame_colour.png"
    tmp_dither = ref / "_frame_dither.png"
    colour = frame_at(video, 2.9, tmp_colour)
    dither = frame_at(video, 0.2, tmp_dither)
    top, bottom = post_bounds(colour)
    w = colour.width
    colour = colour.crop((0, top, w, bottom))
    dither = dither.crop((0, top, w, bottom))
    colour.save(ref / "source-colour-state.png")
    dither.save(ref / "source-dither-state.png")
    tmp_colour.unlink()
    tmp_dither.unlink()

    scale = 1080 / w  # recording -> 1080-wide canvas

    # Ornaments and portrait keep their green ground; the Figma layer adds an
    # additive fill to lift the JPEG quantisation back to #9BFF81.
    for name, box, size, quality in [
        ("orn_tl",   (0, 0, 410, 845),        (235, 485), 70),
        ("orn_tr",   (910, 0, 1320, 845),     (235, 485), 70),
        ("portrait", (228, 238, 1102, 1052),  (520, 484), 74),
    ]:
        (colour.crop(box).resize(size, Image.LANCZOS)
               .save(OUT / f"{name}.jpg", quality=quality,
                     optimize=True, subsampling=2))
        print(f"{name}: canvas x={box[0]*scale:.0f} y={box[1]*scale:.0f} "
              f"w={(box[2]-box[0])*scale:.0f} h={(box[3]-box[1])*scale:.0f}")

    # The dither layer is genuinely 1-bit; threshold it and let Figma multiply.
    d = np.asarray(dither.crop((0, 0, w, 1080))).astype(float).mean(axis=2)
    bw = d < 128
    bw[25:205, 395:915] = False          # cut out the title, kept as live text
    img = Image.fromarray(np.where(bw, 0, 255).astype(np.uint8), "L")
    img = img.resize((1080, 884), Image.LANCZOS).point(
        lambda v: 0 if v < 140 else 255).convert("1")
    img.save(OUT / "dither.png", optimize=True, bits=1)
    print("dither: canvas x=0 y=0 w=1080 h=884 (multiply over the mint ground)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: extract.py <recording.mov>")
    main(Path(sys.argv[1]))
