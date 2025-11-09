"""
Natural Text-to-Speech for Kabu (Children's Mealtime App)
Using Google TTS (gTTS) - Human-like voice perfect for children!
"""

# Install these packages:
# pip install gTTS pygame

from gtts import gTTS
import pygame
import os
import sys
from datetime import datetime

def speak(text, save_audio=True):
    """Speak using Google TTS - natural, human-like voice"""
    print(f"\n🔊 Kabu says: '{text}'")
    
    try:
        # Create output folder if it doesn't exist
        output_folder = "google_audio_files"
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            print(f"📁 Created folder: {output_folder}")
        
        # Generate speech with Google's voice
        tts = gTTS(text=text, lang='en', slow=False)
        
        # Create filename with timestamp
        if save_audio:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Clean text for filename (remove special characters)
            clean_text = "".join(c for c in text[:30] if c.isalnum() or c.isspace()).strip()
            clean_text = clean_text.replace(" ", "_")
            filename = os.path.join(output_folder, f"{timestamp}_{clean_text}.mp3")
        else:
            filename = "kabu_temp.mp3"
        
        tts.save(filename)
        
        if save_audio:
            print(f"💾 Saved: {filename}")
        
        # Play the audio
        pygame.mixer.init()
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()
        
        # Wait for playback to finish
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        
        # Cleanup
        pygame.mixer.quit()
        
        # Only delete if not saving
        if not save_audio:
            try:
                os.remove(filename)
            except:
                pass
        
        print("✅ Done!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        if "connection" in str(e).lower() or "network" in str(e).lower():
            print("⚠️  Make sure you have an internet connection!")

def interactive_mode():
    """Interactive testing mode"""
    print("\n" + "="*60)
    print("🎮 INTERACTIVE TTS TESTING MODE")
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
    print("Type any text for Kabu to say")
    print("Type 'sample' to hear a random sample phrase")
    print("Type 'all' to hear all sample phrases")
    print("Type 'nosave' to toggle saving audio files")
    print("Type 'quit' to exit")
    print("="*60)
    
    save_mode = True
    print(f"\n💾 Audio saving: {'ON' if save_mode else 'OFF'}")
    print(f"📁 Files saved to: google_audio_files/")
    
    while True:
        text = input("\n📝 Text: ").strip()
        
        if text.lower() in ['quit', 'exit', 'q']:
            # Show summary
            if os.path.exists("google_audio_files"):
                files = [f for f in os.listdir("google_audio_files") if f.endswith('.mp3')]
                print(f"\n📊 Summary: {len(files)} audio files saved")
                print(f"📁 Location: {os.path.abspath('google_audio_files')}")
            print("\n👋 Goodbye! Thanks for testing Kabu's voice!")
            break
        
        if not text:
            continue
        
        if text.lower() == 'nosave':
            save_mode = not save_mode
            print(f"\n💾 Audio saving: {'ON' if save_mode else 'OFF'}")
            continue
        
        if text.lower() == 'sample':
            import random
            text = random.choice(sample_phrases)
            print(f"   🎲 Random phrase selected: {text}")
        
        elif text.lower() == 'all':
            print("\n🎵 Playing all sample phrases...\n")
            for i, phrase in enumerate(sample_phrases, 1):
                print(f"\n[{i}/{len(sample_phrases)}] → {phrase}")
                speak(phrase, save_audio=save_mode)
            print("\n✅ All samples played!")
            if save_mode:
                print(f"📁 All audio files saved to: google_audio_files/")
            continue
        
        speak(text, save_audio=save_mode)

def main():
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║                                                            ║
    ║        🎙️  KABU'S TEXT-TO-SPEECH TESTING TOOL  🎙️         ║
    ║                                                            ║
    ║              Using Google TTS - Natural Voice              ║
    ║              Perfect for Children's Application            ║
    ║                                                            ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    print("\n✨ Features:")
    print("   • Human-like, natural voice")
    print("   • Clear and child-friendly")
    print("   • Powered by Google Text-to-Speech")
    
    print("\n📦 Required packages:")
    print("   pip install gTTS pygame")
    
    print("\n🌐 Note: Requires internet connection")
    
    input("\nPress Enter to start testing...")
    
    interactive_mode()

if __name__ == "__main__":
    main()