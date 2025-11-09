"""
Natural Text-to-Speech for Kabu using Coqui TTS
High-quality, human-like voices - Works OFFLINE!
For Python 3.12
"""

# Install: py -m pip install TTS

import sys
import os

def check_dependencies():
    """Check if TTS is installed"""
    try:
        import TTS
        print("✅ Coqui TTS is installed!")
        return True
    except ImportError:
        print("❌ Coqui TTS not found!")
        print("\n📦 To install, run:")
        print("   py -m pip install TTS")
        return False

if not check_dependencies():
    sys.exit(1)

from TTS.api import TTS
import time

def initialize_tts():
    """Initialize Coqui TTS with best model for natural speech"""
    print("\n" + "="*60)
    print("📦 Loading Coqui TTS Model...")
    print("="*60)
    print("\nℹ️  First run will download the model (~100MB)")
    print("   This may take a few minutes...")
    
    try:
        # Using the best English model for natural speech
        # This is a fast, high-quality model
        model_name = "tts_models/en/ljspeech/tacotron2-DDC"
        
        print(f"\n🔄 Initializing model: {model_name}")
        tts = TTS(model_name=model_name, progress_bar=True)
        
        print("\n✅ Model loaded successfully!")
        print("🎤 Voice: Female, clear, natural tone (great for children)")
        
        return tts
        
    except Exception as e:
        print(f"\n❌ Error loading model: {e}")
        print("\n💡 Trying alternative model...")
        
        try:
            # Fallback to a simpler model
            model_name = "tts_models/en/ljspeech/fast_pitch"
            print(f"🔄 Loading: {model_name}")
            tts = TTS(model_name=model_name, progress_bar=True)
            print("\n✅ Alternative model loaded!")
            return tts
        except Exception as e2:
            print(f"\n❌ Failed to load alternative model: {e2}")
            return None

def speak(text, tts):
    """Generate and play speech using Coqui TTS"""
    print(f"\n🔊 Kabu says: '{text}'")
    
    try:
        # Generate speech to file
        output_file = "kabu_coqui_speech.wav"
        
        print("⏳ Generating audio...")
        tts.tts_to_file(text=text, file_path=output_file)
        
        print("🎵 Playing audio...")
        play_audio(output_file)
        
        # Cleanup
        try:
            os.remove(output_file)
        except:
            pass
        
        print("✅ Done!")
        
    except Exception as e:
        print(f"❌ Error generating speech: {e}")

def play_audio(file_path):
    """Play audio file using available system player"""
    import platform
    import subprocess
    
    system = platform.system()
    
    try:
        if system == "Darwin":  # macOS
            subprocess.run(["afplay", file_path], check=True)
        elif system == "Windows":
            # Try multiple methods for Windows
            try:
                # Method 1: Use pygame if available
                import pygame
                pygame.mixer.init()
                pygame.mixer.music.load(file_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                pygame.mixer.quit()
            except:
                # Method 2: Use Windows Media Player
                import winsound
                winsound.PlaySound(file_path, winsound.SND_FILENAME)
        else:  # Linux
            players = ["paplay", "aplay", "ffplay"]
            for player in players:
                try:
                    subprocess.run([player, file_path], check=True, stderr=subprocess.DEVNULL)
                    break
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue
    except Exception as e:
        print(f"⚠️  Audio playback issue: {e}")
        print(f"   Audio saved as: {file_path}")
        print("   Please play it manually to hear the result")

def list_available_models():
    """List some good Coqui TTS models for children's apps"""
    print("\n📚 Recommended Coqui TTS Models:")
    print("\n1. tts_models/en/ljspeech/tacotron2-DDC")
    print("   • High quality, natural female voice")
    print("   • Best for children's applications")
    print("   • Medium speed")
    
    print("\n2. tts_models/en/ljspeech/fast_pitch")
    print("   • Fast generation")
    print("   • Good quality")
    print("   • Lower resource usage")
    
    print("\n3. tts_models/en/vctk/vits")
    print("   • Multiple speakers available")
    print("   • Very natural sounding")
    print("   • Slower generation")

def interactive_mode(tts):
    """Interactive testing mode"""
    print("\n" + "="*60)
    print("🎮 INTERACTIVE COQUI TTS TESTING MODE")
    print("="*60)
    
    # Sample phrases for Kabu
    sample_phrases = [
        "Hello! I'm Kabu. What did you eat today?",
        "That sounds delicious! Tell me more about it.",
        "What's your favorite thing about that meal?",
        "Great job finishing your vegetables!",
        "I didn't quite catch that. Could you say it again?",
        "Wow! That must have been really tasty!",
        "Do you like eating with your family?",
        "What other foods do you like?",
        "Tell me about the colors on your plate!",
        "Did you help cook the meal?"
    ]
    
    print("\n📋 Sample phrases Kabu might say:")
    for i, phrase in enumerate(sample_phrases, 1):
        print(f"   {i}. {phrase}")
    
    print("\n" + "="*60)
    print("Commands:")
    print("  • Type any text for Kabu to say")
    print("  • Type 'sample' for a random phrase")
    print("  • Type 'all' to hear all samples")
    print("  • Type 'models' to see available models")
    print("  • Type 'quit' to exit")
    print("="*60)
    
    while True:
        text = input("\n📝 Text: ").strip()
        
        if text.lower() in ['quit', 'exit', 'q']:
            print("\n👋 Goodbye! Thanks for testing Kabu's Coqui voice!")
            break
        
        if not text:
            continue
        
        if text.lower() == 'models':
            list_available_models()
            continue
        
        if text.lower() == 'sample':
            import random
            text = random.choice(sample_phrases)
            print(f"   🎲 Random phrase: {text}")
        
        elif text.lower() == 'all':
            print("\n🎵 Playing all sample phrases...\n")
            for i, phrase in enumerate(sample_phrases, 1):
                print(f"\n[{i}/{len(sample_phrases)}]")
                speak(phrase, tts)
                time.sleep(0.5)  # Small pause between phrases
            print("\n✅ All samples played!")
            continue
        
        speak(text, tts)

def main():
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║                                                            ║
    ║         🎙️  KABU'S COQUI TTS TESTING TOOL  🎙️            ║
    ║                                                            ║
    ║            High-Quality Offline Voice Synthesis           ║
    ║              Perfect for Children's Application            ║
    ║                                                            ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    print(f"\n🐍 Python Version: {sys.version.split()[0]}")
    print(f"📍 Python Path: {sys.executable}")
    
    print("\n✨ Coqui TTS Features:")
    print("   • Works OFFLINE (no internet needed)")
    print("   • Very natural, human-like voice")
    print("   • High quality audio")
    print("   • Free and open source")
    
    print("\n📦 Installation:")
    print("   py -m pip install TTS")
    
    print("\n⚠️  Note: First run downloads model (~100MB)")
    
    input("\nPress Enter to start loading model...")
    
    # Initialize TTS
    tts = initialize_tts()
    
    if tts is None:
        print("\n❌ Failed to initialize TTS. Exiting...")
        sys.exit(1)
    
    # Start interactive mode
    interactive_mode(tts)

if __name__ == "__main__":
    main()