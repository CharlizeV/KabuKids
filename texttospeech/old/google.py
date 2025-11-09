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

def speak(text):
    """Speak using Google TTS - natural, human-like voice"""
    print(f"\n🔊 Kabu says: '{text}'")
    
    try:
        # Generate speech with Google's voice
        tts = gTTS(text=text, lang='en', slow=False)
        
        # Save to temporary file
        filename = "kabu_speech.mp3"
        tts.save(filename)
        
        # Play the audio
        pygame.mixer.init()
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()
        
        # Wait for playback to finish
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        
        # Cleanup
        pygame.mixer.quit()
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
    print("Type 'quit' to exit")
    print("="*60)
    
    while True:
        text = input("\n📝 Text: ").strip()
        
        if text.lower() in ['quit', 'exit', 'q']:
            print("\n👋 Goodbye! Thanks for testing Kabu's voice!")
            break
        
        if not text:
            continue
        
        if text.lower() == 'sample':
            import random
            text = random.choice(sample_phrases)
            print(f"   🎲 Random phrase selected: {text}")
        
        elif text.lower() == 'all':
            print("\n🎵 Playing all sample phrases...\n")
            for i, phrase in enumerate(sample_phrases, 1):
                print(f"\n[{i}/{len(sample_phrases)}] → {phrase}")
                speak(phrase)
            print("\n✅ All samples played!")
            continue
        
        speak(text)

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