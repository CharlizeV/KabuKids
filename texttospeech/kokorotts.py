import soundfile as sf
import torch
from kokoro import KPipeline
import os

# Configuration
input_dir = "text_files"      # Folder to read .txt files from
output_dir = "kokoro_result"  # Folder to save .wav files to
lang_code = 'a'
voice_style = 'af_heart'
sample_rate = 24000  # kokoro models output at 24kHz

# Setup Directories
# Create input and output directories if they don't exist
os.makedirs(input_dir, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)
print(f"Reading texts from: {os.path.abspath(input_dir)}")
print(f"Saving audio to:    {os.path.abspath(output_dir)}")


# Load Pipeline
print("\nLoading pipeline... This might take a moment.")
try:
    pipeline = KPipeline(lang_code=lang_code)
    print("Pipeline loaded successfully.")
except Exception as e:
    print(f"Fatal Error: Could not load the pipeline: {e}")
    print("Please check your 'kokoro' installation and dependencies.")
    exit() # Exit if can't load the model


# Find and Process .txt Files
try:
    # Get a list of all files in the input directory ending with .txt
    txt_files = [f for f in os.listdir(input_dir) if f.endswith('.txt')]
except FileNotFoundError:
    print(f"Error: Input directory not found at '{os.path.abspath(input_dir)}'")
    txt_files = []

if not txt_files:
    print(f"\nNo .txt files found in '{input_dir}'.")
    print(f"Please add one or more .txt files to {os.path.abspath(input_dir)} and run again.")
else:
    print(f"\nFound {len(txt_files)} file(s) to process: {', '.join(txt_files)}")


# Main Processing Loop
# Loop through each text file found
for txt_filename in txt_files:
    # Construct the full path for reading the text file
    input_filepath = os.path.join(input_dir, txt_filename)
    
    # Determine base name
    base_name = os.path.splitext(txt_filename)[0]
    
    # Construct the full path for saving the audio file
    output_filename = os.path.join(output_dir, f"{base_name}.wav")

    print(f"\n--- Processing: {txt_filename} ---")

    # 1. Read the text from the file
    try:
        with open(input_filepath, 'r', encoding='utf-8') as f:
            text_to_speak = f.read()
        
        # Skip if the file is empty
        if not text_to_speak.strip():
            print(f"Warning: '{txt_filename}' is empty. Skipping.")
            continue  # Move to the next file

    except Exception as e:
        print(f"Error reading file '{input_filepath}': {e}. Skipping.")
        continue  # Move to the next file

    text_snippet = text_to_speak[:70].replace('\n', ' ')
    print(f"Generating audio for: '{text_snippet}...'")
    
    # 2. Generate the audio
    try:
        generator = pipeline(text_to_speak, voice=voice_style)
        
        all_audio = []
        # The generator yields chunks; collect them
        for i, (gs, ps, audio) in enumerate(generator):
            all_audio.append(audio)

        # 3. Combine and Save the audio
        if all_audio:
            # Combine all audio chunks into one array
            final_audio = torch.cat(all_audio).numpy()
            
            # Save the final combined audio to its unique file
            sf.write(output_filename, final_audio, sample_rate)
            print(f"Success! Audio saved to: {os.path.abspath(output_filename)}")
        else:
            print(f"No audio was generated for {txt_filename}.")

    except Exception as e:
        # Catch any errors during the generation/saving process
        print(f"Error during audio generation for '{txt_filename}': {e}")

print("\n--- All processing complete. ---")