import io
import wave
import numpy as np
import sounddevice as sd
from groq import Groq

GROQ_API_KEY = ""
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

def tts_kokoro( text, voice="autumn"):
    if client is None or not text or not text.strip():
        return
    
    try:
        response = client.audio.speech.create(
            model="canopylabs/orpheus-v1-english",
            input=text.strip(),
            voice=voice,
            response_format="wav"
        )
        
        wav_buffer = io.BytesIO(response.read())
        with wave.open(wav_buffer, 'rb') as wav_file:
            sample_rate = wav_file.getframerate()
            n_channels = wav_file.getnchannels()
            audio_bytes = wav_file.readframes(wav_file.getnframes())
            
            audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
            audio_np = audio_np.astype(np.float32) / 32768.0
            
            if n_channels == 2:
                audio_np = audio_np.reshape(-1, 2)
            
            sd.play(audio_np, samplerate=sample_rate)
            sd.wait() 
            
    except Exception as e:
        print(f"TTS Error: {e}")
