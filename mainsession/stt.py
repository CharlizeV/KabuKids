import time
import numpy as np
import sounddevice as sd
from transformers import pipeline
from .config import SAMPLE_RATE, PROCESS_TIMEOUT


# Initialize ASR pipeline on import (may take time)
try:
    asr_pipeline = pipeline(
        "automatic-speech-recognition",
        model="openai/whisper-tiny",
        tokenizer="openai/whisper-tiny",
        device=-1,
    )
except Exception:
    asr_pipeline = None


def get_audio(wait_time: float = 30.0, silence_threshold=0.005):

    chunk_se = 0.2
    chunk_frames = max(1, int(chunk_se * SAMPLE_RATE))

    start_time = time.time()
    recorded_chunks = []
    recording = False
    silence_start = None

    try: 
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", blocksize=chunk_frames) as stream:
            while True:
                frames, overflowed = stream.read(chunk_frames)
                chunk = np.asarray(frames, dtype="float32").flatten()
                rms = float(np.sqrt(np.mean(chunk.astype("float64") ** 2))) if chunk.size else 0.0
                now = time.time()

                # not recording yet: wait for speech start
                if not recording:
                    if rms >= silence_threshold:
                        recording = True
                        recorded_chunks.append(chunk)
                        silence_start = None
                    else:
                        # timeout waiting for initial speech
                        if now - start_time >= wait_time:
                            return "NO_SPEECH"
                        # keep listening
                        continue

                else:
                    # already recording: accumulate
                    recorded_chunks.append(chunk)
                    if rms < silence_threshold:
                        if silence_start is None:
                            silence_start = now
                        elif now - silence_start >= 2.0:
                            # 2 seconds of silence -> stop and return audio
                            audio = np.concatenate(recorded_chunks) if recorded_chunks else np.array([], dtype="float32")
                            return audio
                    else:
                        # reset silence timer when speech resumes
                        silence_start = None
    except Exception:
        return "NO_SPEECH"
     
    # frames = int(wait_time * SAMPLE_RATE)
    # audio_buf = sd.rec(frames, samplerate=SAMPLE_RATE, channels=1, dtype='float32')
    # sd.wait()
    # audio = audio_buf.flatten()

    # # simple energy check (RMS) to decide if speech present
    # if audio.size == 0:
    #     return "NO_SPEECH"
    # rms = float(np.sqrt(np.mean(audio.astype('float64') ** 2)))
    # if rms < silence_threshold:
    #     return "NO_SPEECH"
    # return audio


def transcribe_with_timeout(audio, timeout: float = PROCESS_TIMEOUT):
    if asr_pipeline is None:
        return None
    start = time.time()
    try:
        output = asr_pipeline(audio)
        elapsed = time.time() - start
        if elapsed <= timeout:
            return output.get("text", "").strip() or None
        return None
    except Exception:
        return None


def get_transcribed_audio(audio, timeout: float = PROCESS_TIMEOUT):
    return transcribe_with_timeout(audio, timeout=timeout)
