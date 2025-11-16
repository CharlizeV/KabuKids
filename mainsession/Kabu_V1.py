import os
import json
import time
import threading
import collections
import cv2
import numpy as np
import sounddevice as sd
import torch
import ollama
import random
import tts
import mongodb
from kokoro import KPipeline
from PIL import Image
from transformers import pipeline
from openai import OpenAI
from typing import Dict, List, Any
from datetime import datetime, timezone

from config import CAMERA_INDEX
import utils
import stt
import fer
import llm

#Possible Additional Changes:
# -- Add more interaction elements such as waiting for a response in 30 seconds before moving on.
# -- Add sound effects or music during meal times to make it more engaging.



# --------------------------------------------------------------------------------------------------------------
#CONFIG
SAMPLE_RATE = 16000
DURATION = 10   
PROCESS_TIMEOUT = 3.0  

HISTORY_FILE = "conversation_history.json"

CONTEXT = """
WHO YOU ARE:
You are Kabu, a personal eating chatbot companion for kids.
You are Joyful and empathic. Ready to bring fun to children as much as possible.

YOUR GOAL:
Keeping the child engaged so that they enjoy and most importantly finish their meal.

ENCOURAGE:
Keep the sentences to a minimum of 4.
The conversation to be child-friendly. 
If the child wants to talk about his topic focus on that topic instead.
Ask the child about what food they are currently eating or have eaten recently.
Before replying to the child, consider their facial expressions to make your response more empathetic.
TRY YOUR VERY BEST TO ASK WHAT THEY ARE EATING IF THEY HAVE NOT MENTIONED IT YET. After they mentioned what they ate remember that and do not ask them again in later conversations.

AVOID:
Asking too much questions.
Making the same replies like your other prompts from before.
Asking to join your for meals, because you are a chatbot you cannot eat physically. 
ANY USE OF PROFANITY. 
SUGGESTING TO CHILD TO EAT FOOD. Unless the child asks for suggestions, do not suggest food items.
Do not assume that you know what's on the plate of the child. You do not have that information.

ADDITONAL CONTEXTS:
Rememeber what the child hated or liked about the meal, but do not bring it up unless the child does first. You may ask follow up questions about it.

FORMAT YOUR REPONSE AS BELOW (EVERY REPLY SHOULD HAVE THIS FORMAT THIS IS A NON NEGOTIABLE):
Kabu: <your response here>
Kabu_emotion: [Excited, Happy, Neutral, Sad]

FOLLOW THIS EXACT FORMAT IN EVERY RESPONSE. DO NOT DEVIATE FROM IT.
Example: 
Kabu: I'm having a great time chatting with you while you eat your meal! What is your favorite food to eat?
Kabu_emotion: [Happy]
"""

ANALYSIS_PROMPT = ("""
    Using the conversation history above as the ONLY source of facts, analyze and provide:
    1) Three concise, actionable conversation recommendations to better engage the child.
    2) A list of foods the child expressed they do NOT like (if any). If you are going to suggest anything make sure it's a healthy alternative option of an ingredient. Example: If you are suggesting an alternative for broccoli then suggest something like cauliflower.
    3) For each disliked food, suggest 1-2 child-friendly alternatives or ways to present it.
    Format your response clearly and keep it short. Do not invent facts; base everything on the conversation_history.

    Format your response as below:
    Conversation Recommendations:
    Recommendation 1:
    Recommendation 2:
    Recommendation 3:
    Disliked Foods:
    Food 1: Alternatives
    Food 2: Alternatives
    (Add more if applicable)

    Example:
    Conversation Recommendations:
    Recommendation 1: Try asking the child about their favorite color of food to make the conversation more engaging.
    Recommendation 2: Use more playful language to keep the child interested.
    Recommendation 3: Ask the child about their favorite snacks to learn more about their preferences.
    Disliked Foods:
    Food 1: Broccoli: Cauliflower - (vitamins C, K, B6, and folate, and also contains fiber, choline, and various minerals like potassium and magnesium)
    Food 2: Spinach: Lettuce - (Lettuce contains a variety of nutrients, including vitamins A and K, folate, and vitamin C.)
"""
)

transcript = {
    "role": "",                                 
    "current_time": "",  
    "transcript": "",
    "emotion_displayed": []
}

def main():
    child_data = mongodb.get_child_by_id("charlizeyv")

    USER_CONTEXT = f"""
    WHO YOU ARE WITH:
    You are talking to a {child_data.get('gender')} child who is eating a meal as you speak.
    Their name is {child_data.get('name')}, they are {utils.compute_age_from(child_data.get('birthday'))} years old.
    
    THE LIST OF THINGS THE CHILD LIKES TO TALK ABOUT:
    {child_data.get('likes')}

    THE LIST OF THINGS THE CHILD DISLIKES TO TALK ABOUT (AVOID THESE TOPICS, PHRASES, OR SENTENCES WHEN TALKING TO THE CHILD):
    {child_data.get('dislikes')}

    CHILD'S GOAL:
    {child_data.get('goals')}
    """

    print(USER_CONTEXT)

    full_transcript = []

    pipeline = KPipeline(lang_code='a')

    utils.reset_history(system_message={
        "role": "system",
        "content": USER_CONTEXT + CONTEXT,
    })

    camera = cv2.VideoCapture(CAMERA_INDEX)
    if not camera.isOpened():
        print("Could not open camera")
        return
    
    utils.clear_screen()

    start = datetime.now(timezone.utc)

    try:
        print("Starting Kabu MEALTIME... Press Ctrl+C to stop.")

        while True:
            transcription = [None]
            emotions = [None]

            def audio_task():
                audio = stt.get_audio(wait_time=30.0)
                if isinstance(audio, str) and audio == "NO_SPEECH":
                    transcription[0] = "NO_SPEECH"
                    return
                if audio is None:
                    transcription[0] = ""
                    return
                text = stt.get_transcribed_audio(audio)
                transcription[0] = text if text else ""

            def fer_task():
                result = fer.get_facial_expression(camera, duration=5.0)
                emotions[0] = result if result is not None else []

            audio_thread = threading.Thread(target=audio_task)
            fer_thread = threading.Thread(target=fer_task)

            print("Listening and observing face ... Please speak and stay in view.")
            audio_thread.start()
            fer_thread.start()

            audio_thread.join()
            fer_thread.join()

            user_text = transcription[0].strip() if transcription[0] else None
            emotion_list = emotions[0]
            emotion_str = ", ".join(emotion_list) if emotion_list else "unknown"

            if user_text == "NO_SPEECH":
                print("The child did not say anything.")
                prompt = f"No speech detected. Observed emotion(s): {emotion_str}."
            else:
                print(f"Transcribed: {user_text}")
                print(f"Emotion(s): {emotion_str}")
                prompt = f"The child said: \"{user_text}\". Observed emotion(s): {emotion_str}."
            try:
                full_transcript.append({
                    "role": "User(Temp)",
                    "current_time": utils.time_format(start),
                    "transcript": user_text,
                    "emotion_displayed": emotion_list
                })

                reply = llm.get_kabu_response(prompt)
                parsed = utils.parse_kabu_reply(reply)
                #print("\nKabu:", reply) --- IGNORE ---

                full_transcript.append({
                    "role": "Kabu(Temp)",
                    "current_time": utils.time_format(start),
                    "transcript": parsed['text'],
                    "emotion_displayed": parsed['emotions']
                })

                print(f"\nKabu: {parsed['text']} (Emotions: {', '.join(parsed['emotions'])})")
                tts.tts_kokoro(pipeline, parsed['text'])
            except Exception as e:
                print("Failed to get Kabu's response:", e)

            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        try:
            analysis_reply = llm.get_kabu_response(ANALYSIS_PROMPT)
            print("\n--- Conversation Analysis ---")
            print(analysis_reply)
            parsed = utils.parse_kabu_reply_final(analysis_reply)
            print(parsed["recommendations"])
            print(parsed["disliked_foods"])
            # persist analysis into history
        except Exception as e:
            print("Analysis request failed:", e)
        

        end = datetime.now(timezone.utc)
        
        meal_hash ={
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "date": start.date().isoformat(),
            "transcript": full_transcript,
            "conversation_suggestions": parsed["recommendations"],
            "ingredient_suggestions": parsed["disliked_foods"],
            "ingredients_not_finished": ["Rice"],
            "portion_after_meal": "1/3 cup",
        }

        meal_id = mongodb.insert_meal(meal_hash)
        print(f"Meal data saved with meal_id: {meal_id}")

        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()