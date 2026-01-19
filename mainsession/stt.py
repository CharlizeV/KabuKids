import os
import time
import numpy as np
import io
import wave
from groq import Groq
import sounddevice as sd
from .config import SAMPLE_RATE, PROCESS_TIMEOUT

# Check if API key is set
GROQ_API_KEY = "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"

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

def get_audio(wait_time: float = 30.0, silence_threshold=0.005, debug=False):

    chunk_se = 0.2
    chunk_frames = max(1, int(chunk_se * SAMPLE_RATE))

    start_time = time.time()
    recorded_chunks = []
    recording = False
    silence_start = None
    rms_samples = []  # For debugging

    try: 
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", blocksize=chunk_frames) as stream:
            while True:
                frames, overflowed = stream.read(chunk_frames)
                chunk = np.asarray(frames, dtype="float32").flatten()
                rms = float(np.sqrt(np.mean(chunk.astype("float64") ** 2))) if chunk.size else 0.0
                now = time.time()

                # Collect RMS samples for debugging (keep last 10)
                if debug and len(rms_samples) < 10:
                    rms_samples.append(rms)

                # not recording yet: wait for speech start
                if not recording:
                    if rms >= silence_threshold:
                        recording = True
                        recorded_chunks.append(chunk)
                        silence_start = None
                        if debug:
                            print(f"Speech detected! RMS={rms:.6f}, threshold={silence_threshold:.6f}")
                    else:
                        # timeout waiting for initial speech
                        if now - start_time >= wait_time:
                            if debug:
                                avg_rms = np.mean(rms_samples) if rms_samples else 0.0
                                max_rms = np.max(rms_samples) if rms_samples else 0.0
                                print(f"Timeout: No speech detected. Avg RMS={avg_rms:.6f}, Max RMS={max_rms:.6f}, Threshold={silence_threshold:.6f}")
                                print(f"Tip: If your RMS values are lower than threshold, try lowering silence_threshold (current: {silence_threshold})")
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
                            if debug:
                                print(f"Recording complete. Audio length: {len(audio)/SAMPLE_RATE:.2f} seconds")
                            return audio
                    else:
                        # reset silence timer when speech resumes
                        silence_start = None
    except Exception as e:
        print(f"Error in get_audio: {e}")
        import traceback
        traceback.print_exc()
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


def get_transcribed_audio(audio, timeout: float = None):
    if audio is None or isinstance(audio, str):
        return None
    
    # Use a longer timeout for API calls (default 10 seconds instead of 3)
    if timeout is None:
        timeout = max(PROCESS_TIMEOUT, 10.0)
    
    start = time.time()
    try:
        # Convert float32 audio to int16 PCM
        audio_int16 = (audio * 32767).astype(np.int16)
        
        # Create a WAV file in memory with proper headers
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit = 2 bytes per sample
            wav_file.setframerate(SAMPLE_RATE)
            wav_file.writeframes(audio_int16.tobytes())
        
        wav_buffer.seek(0)  # Reset buffer position to beginning
        
        transcript = client.audio.transcriptions.create(
            file=("audio.wav", wav_buffer.read(), "audio/wav"),
            model="whisper-large-v3-turbo",
        )
        elapsed = time.time() - start
        if elapsed <= timeout:
            result = transcript.text.strip() if transcript.text else None
            print(f"Transcription successful ({elapsed:.2f}s): {result}")
            return result
        else:
            print(f"Transcription timeout: {elapsed:.2f}s > {timeout:.2f}s")
            return None
    except Exception as e:
        print(f"Error during transcription: {e}")
        import traceback
        traceback.print_exc()
        return None
