import soundfile as sf
import torch
from kokoro import KPipeline
import os

# --- Configuration ---
output_dir = "kokoro_result"
output_filename = os.path.join(output_dir, "output_audio.wav")
lang_code = 'a'
voice_style = 'af_heart'
text_to_speak = """
hi
"""

# text_to_speak = """
# Hello! I'm Kabu. What did you eat today? 
# That sounds delicious! Tell me more about it. 
# What's your favorite thing about that meal? 
# Great job finishing your vegetables! 
# I didn't quite catch that. Could you say it again? 
# Wow! That must have been really tasty! 
# Do you like eating with your family? 
# What other foods do you like?
# Tell me about the colors on your plate!
# Did you help cook the meal?
# """
# --- End Configuration ---

# Create the output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)
print(f"Output will be saved to '{output_dir}' directory.")


print("Loading pipeline... This might take a moment.")
# Initialize the TTS pipeline
pipeline = KPipeline(lang_code=lang_code)

print(f"Generating audio for: '{text_to_speak[:50]}...'")
# Generate the audio
generator = pipeline(text_to_speak, voice=voice_style)

all_audio = []
for i, (gs, ps, audio) in enumerate(generator):
    print(f"Generated chunk {i}...")
    all_audio.append(audio)

# Combine all audio chunks into one array
if all_audio:
    final_audio = torch.cat(all_audio).numpy()
    
    # Save the final combined audio to a single file
    sample_rate = 24000  # kokoro models output at 24kHz
    sf.write(output_filename, final_audio, sample_rate)
    print(f"\nSuccess! Audio saved to: {os.path.abspath(output_filename)}")
else:
    print("No audio was generated.")