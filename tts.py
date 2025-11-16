import sounddevice as sd
import numpy as np
from kokoro import KPipeline
from typing import Dict, List, Any

def tts_kokoro(pipeline, text):
    try:
        generator = pipeline(text, voice='af_sky')
        for i, (gs, ps, audio) in enumerate(generator):
            audio_np = np.asarray(audio, dtype='float32')
            sd.play(audio_np, samplerate=24000)
            sd.wait()
    except Exception as e:
        print("TTS error:", e)