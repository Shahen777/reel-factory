"""Beat grid detection with librosa, cached next to the audio file."""
import json
import os


def beats_for(music, cache=True):
    """Return {'tempo', 'beats': [seconds...], 'duration'} for an audio file."""
    cpath = music + ".beats.json"
    if cache and os.path.exists(cpath) and os.path.getmtime(cpath) >= os.path.getmtime(music):
        return json.load(open(cpath))
    import warnings
    warnings.filterwarnings("ignore")
    import librosa
    import numpy as np
    y, sr = librosa.load(music, sr=22050, mono=True)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
    d = {"tempo": float(np.atleast_1d(tempo)[0]),
         "beats": [round(float(b), 4) for b in beats],
         "duration": float(len(y) / sr)}
    if cache:
        try:
            json.dump(d, open(cpath, "w"))
        except OSError:
            pass
    return d


def grid(music, offset=0.0, min_len=400, beat_source=None):
    """Beats shifted by offset and extended with the average step if the track runs out."""
    bd = beats_for(beat_source or music)
    beats = [b - offset for b in bd["beats"] if b - offset >= -0.01]
    if len(beats) < 2:
        step = 60.0 / max(bd.get("tempo") or 120.0, 1.0)
        beats = [i * step for i in range(min_len)]
    else:
        step = (beats[-1] - beats[0]) / (len(beats) - 1)
        while len(beats) < min_len:
            beats.append(beats[-1] + step)
    return bd["tempo"], beats
