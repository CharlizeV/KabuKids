from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.checkbox import CheckBox
from mainsession.config import CAMERA_INDEX
from services.models import CURRENT_MEAL, init_current_meal, clear_current_meal, SAMPLE_REPORTS
from db import meals_col
from kivy.app import App
from kivy.metrics import dp
from datetime import datetime
import uuid

import json
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'mainsession'))
from mainsession import stt, llm, tts, mongodb, fer, utils, Kabu_V1, config

import time
import threading
import cv2
import numpy as np
import sounddevice as sd
from kokoro import KPipeline
from PIL import Image
from transformers import pipeline
from openai import OpenAI
from typing import Dict, List, Any
from datetime import datetime, timezone
from kivy.logger import Logger

class PortionSizeBeforePage(Screen):
    pass

class PortionSizeAfterPage(Screen):
    pass

class InputIngredientsBMPage(Screen):
    def on_enter(self):
        """Always start a fresh meal and clear the visible tags when opening the Before-Meal screen."""
        app = App.get_running_app()
        user = getattr(app, "current_user", None)
        user_id = None
        try:
            if isinstance(user, dict):
                user_id = user.get("_id")
            else:
                user_id = getattr(user, "_id", None)
        except Exception:
            user_id = None

        # Force-init a new CURRENT_MEAL for this session so previous tags/data are cleared
        init_current_meal(user_id=user_id)
        CURRENT_MEAL["food_before_meal"] = []

        # Rebuild the ingredients container UI so no tags from previous meal remain
        try:
            cont = self.ids.ingredients_container
            cont.clear_widgets()
            plus = Button(
                text="+",
                size_hint_y=None,
                height=30,
                font_size='20sp',
                background_normal='',
                background_color=(0.85, 0.85, 0.85, 1),
                color=(0, 0, 0, 1)
            )
            plus.bind(on_release=lambda btn: self.add_tag_prompt("ingredients"))
            cont.add_widget(plus)
            cont.height = cont.minimum_height if cont.children else 40
        except Exception as e:
            print("❌ InputIngredientsBMPage.on_enter UI rebuild error:", e)

    def remove_tag(self, tag_layout):
        parent = tag_layout.parent
        parent.remove_widget(tag_layout)
        parent.height = parent.minimum_height if parent.children else 40
        # update global buffer to match UI
        try:
            if CURRENT_MEAL is not None:
                CURRENT_MEAL["food_before_meal"] = self._collect_ingredients()
        except Exception:
            pass

    def add_tag_prompt(self, section):
        # Create input popup
        content = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))
        text_input = TextInput(
            hint_text="Enter tag...",
            font_size='16sp',
            multiline=False,
            size_hint_y=None,
            height=dp(40)
        )
        btn_layout = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(40))
        btn_submit = Button(text="Add")
        btn_cancel = Button(text="Cancel")
        btn_layout.add_widget(btn_submit)
        btn_layout.add_widget(btn_cancel)
        content.add_widget(text_input)
        content.add_widget(btn_layout)

        popup = Popup(title="Add Tag", content=content, size_hint=(0.7, 0.3))

        def add_tag(instance):
            tag_text = text_input.text.strip()
            if tag_text:
                self.add_tag_to_section(section, tag_text)
            popup.dismiss()

        def cancel(instance):
            popup.dismiss()

        btn_submit.bind(on_press=add_tag)
        btn_cancel.bind(on_press=cancel)
        popup.open()

    def add_tag_to_section(self, section, tag_text):
        # Create tag widget
        tag_box = BoxLayout(
            size_hint_y=None,
            height=30,
            spacing=5
        )
        tag_box.canvas.before.clear()
        from kivy.graphics import Color, Rectangle
        with tag_box.canvas.before:
            Color(0.8, 0.8, 0.8, 1)
            Rectangle(pos=tag_box.pos, size=tag_box.size)
        tag_box.bind(pos=lambda obj, pos: setattr(obj.canvas.before.children[-1], 'pos', pos),
                     size=lambda obj, size: setattr(obj.canvas.before.children[-1], 'size', size))

        label = Label(
            text=tag_text,
            font_size='14sp',
            color=[0, 0, 0, 1],
            halign='left',
            valign='center'
        )
        label.bind(size=label.setter('text_size'))

        close_btn = Button(
            text="×",
            size_hint_x=None,
            width=25,
            background_normal='',
            background_color=[1, 0.4, 0.4, 1],
            color=[1, 1, 1, 1],
            font_size='16sp'
        )
        close_btn.bind(on_press=lambda x: self.remove_tag(tag_box))

        tag_box.add_widget(label)
        tag_box.add_widget(close_btn)

        # Add to correct section
        if section == "ingredients":
            container = self.ids.ingredients_container
        else:
            return

        # Insert before the "+" button (which is the last child)
        container.add_widget(tag_box, len(container.children) - 1)
        container.height = container.minimum_height

        # --- NEW: update global buffer to reflect current ingredients ---
        try:
            if CURRENT_MEAL is None:
                init_current_meal()
            CURRENT_MEAL["food_before_meal"] = self._collect_ingredients()
            # also ensure user_id is set
            app = App.get_running_app()
            user = getattr(app, "current_user", None)
            if user:
                CURRENT_MEAL["user_id"] = user.get("_id") if isinstance(user, dict) else getattr(user, "_id", CURRENT_MEAL.get("user_id"))
        except Exception as e:
            print("❌ failed to update CURRENT_MEAL on add_tag:", e)

    def _collect_ingredients(self):
        """Return the visible ingredients from the ingredients_container in first-added order."""
        try:
            cont = self.ids.ingredients_container
        except Exception:
            return []
        tags = []
        for child in cont.children:
            if not isinstance(child, BoxLayout):
                continue
            found = None
            for w in child.children:
                if hasattr(w, 'text') and w.text and w.text != "×":
                    found = w
                    break
            if found:
                tags.append(found.text)
        tags.reverse()
        return tags

class InputIngredientsAMPage(Screen):  # AM = After Meal
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Placeholder food list (replace later with actual data from before-meal input)
        self.placeholder_foods = ["chicken", "rice", "carrots", "apple", "bread"]

    def on_enter(self):
        # Populate checkboxes from CURRENT_MEAL if available, otherwise fallback placeholder
        container = self.ids.food_checkboxes
        container.clear_widgets()

        ingredients = CURRENT_MEAL.get("food_before_meal", []) if CURRENT_MEAL else []
        if not ingredients:
            ingredients = self.placeholder_foods

        for food in ingredients:
            row = BoxLayout(size_hint_y=None, height=40, padding=[10, 5])
            cb = CheckBox(size_hint_x=None, width=30, group=None)
            label = Label(text=food.capitalize(), color=[0, 0, 0, 1], halign='left', valign='middle')
            label.bind(size=label.setter('text_size'))
            row.add_widget(cb)
            row.add_widget(label)
            container.add_widget(row)

        container.height = container.minimum_height

    def finish_meal(self):
        """Collect after-meal inputs, assemble the meal doc, save to MongoDB, update in-memory reports,
           and navigate to the report page showing the newly inserted meal.
           This uses dummy portion/session data (portions/session pages should set real values into CURRENT_MEAL).
        """
        try:
            # ensure we have a buffer
            if not CURRENT_MEAL:
                init_current_meal()
            # collect finished vs not finished from UI
            container = self.ids.food_checkboxes
            finished = []
            not_finished = []
            for row in container.children:
                # find checkbox and label inside row
                cb = None
                lbl = None
                for w in row.children:
                    if isinstance(w, CheckBox):
                        cb = w
                    elif hasattr(w, "text"):
                        lbl = w
                name = lbl.text if lbl else ""
                if cb and cb.active:
                    finished.append(name)
                else:
                    not_finished.append(name)

            # normalize names (remove bullet/case)
            finished = [s.strip() for s in finished]
            not_finished = [s.strip() for s in not_finished]

            # update CURRENT_MEAL fields (use dummy start/end times/summary/portions if not set)
            now = datetime.now()
            if not CURRENT_MEAL.get("date"):
                CURRENT_MEAL["date"] = now.strftime("%B %d, %Y")
            if not CURRENT_MEAL.get("start_time"):
                CURRENT_MEAL["start_time"] = now.strftime("%I:%M %p").lstrip("0")
            if not CURRENT_MEAL.get("end_time"):
                CURRENT_MEAL["end_time"] = now.strftime("%I:%M %p").lstrip("0")
            CURRENT_MEAL["food_before_meal"] = CURRENT_MEAL.get("food_before_meal", []) or []
            CURRENT_MEAL["food_not_finished"] = not_finished
            # dummy portions (portions pages should set these)
            if not CURRENT_MEAL.get("portion_before_image"):
                CURRENT_MEAL["portion_before_image"] = "assets/portion_before_dummy.jpg"
            if not CURRENT_MEAL.get("portion_after_image"):
                CURRENT_MEAL["portion_after_image"] = "assets/portion_after_dummy.jpg"
            # dummy summary & suggestions (session page should set these)
            if not CURRENT_MEAL.get("summary"):
                CURRENT_MEAL["summary"] = "Auto-generated summary (dummy)."
            if not CURRENT_MEAL.get("conversation_suggestions"):
                CURRENT_MEAL["conversation_suggestions"] = ["Try asking about colors.", "Praise effort."]
            if not CURRENT_MEAL.get("ingredient_suggestions"):
                CURRENT_MEAL["ingredient_suggestions"] = ["Carrots - good source of beta-carotene."]

            # ensure required keys exist and set _id if missing
            if not CURRENT_MEAL.get("_id"):
                CURRENT_MEAL["_id"] = str(uuid.uuid4())

            # Insert into MongoDB
            try:
                result = meals_col.insert_one(CURRENT_MEAL)
                print("✅ Inserted meal:", result.inserted_id)
                meal_doc = CURRENT_MEAL.copy()
            except Exception as e:
                # Fallback: still use CURRENT_MEAL as the inserted doc (but inform)
                print("❌ failed to insert meal to MongoDB:", e)
                meal_doc = CURRENT_MEAL.copy()

            # Update in-memory SAMPLE_REPORTS so report page can immediately show it
            SAMPLE_REPORTS[meal_doc["_id"]] = meal_doc

            # Select the new meal and navigate to report
            app = App.get_running_app()
            app.selected_meal_id = meal_doc["_id"]
            # clear buffer for next meal
            clear_current_meal()

            # navigate to report screen
            self.manager.current = "report"

        except Exception as e:
            print("❌ finish_meal error:", e)
            Popup(title="", content=Label(text="Failed to finish meal."), size_hint=(0.6,0.3)).open()

transcription = [None]
emotions = [None]
camera = None
start = None

class SessionPage(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._session_thread = None
        self._stop_event = threading.Event()
        self.camera = None
        self.pipeline = None
        self.full_transcript = []

    def on_pre_enter(self, *args):
        self.start_session()

    def on_leave(self, *args):
        self.stop_session()

    def start_session(self):
        Logger.info("Kabu: start_session called")
        if self._session_thread and self._session_thread.is_alive():
            Logger.info("Kabu: session already running; skipping start")
            return
        self._stop_event.clear()
        self._session_thread = threading.Thread(target=self._run_session_loop, daemon=True)
        self._session_thread.start()
        Logger.info("Kabu: session thread started -> %s", str(self._session_thread))

    def stop_session(self):
        Logger.info("Kabu: stop_session called")
        self._stop_event.set()
        # try to join the session thread (short timeout) so we can observe shutdown
        try:
            if self._session_thread:
                self._session_thread.join(timeout=1.0)
                if self._session_thread.is_alive():
                    Logger.info("Kabu: session thread still alive after join timeout")
        except Exception as e:
            Logger.info("Kabu: error joining session thread: %s", e)
        try:
            if self.camera and hasattr(self.camera, "isOpened") and self.camera.isOpened():
                self.camera.release()
                Logger.info("Kabu: camera released in stop_session")
        except Exception as e:
            Logger.info("Kabu: camera release error: %s", e)

    def _run_session_loop(self):
        Logger.info("Kabu: _run_session_loop starting")
        start = datetime.now(timezone.utc)
        try:
            # keep original initialization (unchanged) but log key steps
            Logger.info("Kabu: loading child_data")
            child_data = mongodb.get_child_by_id(CURRENT_MEAL.get("user_id"))
            Logger.info("Kabu: child_data loaded: %s", str(child_data.get("name")))
            
            USER_CONTEXT = f"""
                WHO YOU ARE WITH:
                You are talking to a {child_data.get('gender')} child who is eating a meal as you speak.
                Their name is {child_data.get('name')}, they are {utils.compute_age_from(child_data.get('birthday'))} years old.
                
                THE LIST OF THINGS THE CHILD LIKES TO TALK ABOUT:
                {child_data.get('likes')}

                THE LIST OF THINGS THE CHILD DISLIKES TO TALK ABOUT (AVOID THESE TOPICS, PHRASES, OR SENTENCES WHEN TALKING TO THE CHILD):
                {child_data.get('dislikes')}

                THE LIST OF INGREDIENTS THE CHILD IS EATING IN THIS MEAL ARE THE FOLLOWING:
                {CURRENT_MEAL.get('food_before_meal')}

                CHILD'S GOAL:
                {child_data.get('goals')}
                """

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
            Kabu_emotion: [Excited, Happy, Neutral, Sad] (Note: EMOTIONS SHOULD ONLY BE FROM THIS LIST: Excited, Happy, Neutral, Sad. Do not create new emotions outside of this list.)

            FOLLOW THIS EXACT FORMAT IN EVERY RESPONSE. DO NOT DEVIATE FROM IT.
            Example: 
            Kabu: I'm having a great time chatting with you while you eat your meal! What is your favorite food to eat?
            Kabu_emotion: [Happy]
            """ 

            ANALYSIS_PROMPT = """
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

            Logger.info("Kabu: initializing pipeline")
            try:
                pipeline = KPipeline(lang_code='a')
                self.pipeline = pipeline
                Logger.info("Kabu: pipeline initialized")
            except Exception as e:
                Logger.info("Kabu: pipeline init failed: %s", e)
                pipeline = None
                self.pipeline = None

            Logger.info("Kabu: opening camera index %s", config.CAMERA_INDEX)
            try:
                camera = cv2.VideoCapture(config.CAMERA_INDEX)
                self.camera = camera
                if not camera.isOpened():
                    Logger.info("Kabu: camera not opened")
                else:
                    Logger.info("Kabu: camera opened")
            except Exception as e:
                Logger.info("Kabu: camera init exception: %s", e)
                camera = None
                self.camera = None

            utils.reset_history(system_message={
                "role": "system",
                "content": USER_CONTEXT + CONTEXT,
            })
            Logger.info("Kabu: utils history reset")

            start_time = datetime.now(timezone.utc)
            Logger.info("Kabu: entering main loop")

            # MAIN LOOP (preserve original logic) with safer joins and debug logging
            while not self._stop_event.is_set():
                Logger.info("Kabu: loop iteration start")
                transcription = [None]
                emotions = [None]

                def audio_task():
                    try:
                        Logger.info("Kabu: audio_task started")
                        audio = stt.get_audio(wait_time=30.0)
                        if isinstance(audio, str) and audio == "NO_SPEECH":
                            transcription[0] = "NO_SPEECH"
                            return
                        if audio is None:
                            transcription[0] = ""
                            return
                        transcription[0] = stt.get_transcribed_audio(audio) or ""
                        Logger.info("Kabu: audio_task finished -> %s", str(transcription[0])[:80])
                    except Exception as e:
                        Logger.info("Kabu: audio_task exception: %s", e)
                        transcription[0] = ""

                def fer_task():
                    try:
                        Logger.info("Kabu: fer_task started")
                        if camera:
                            result = fer.get_facial_expression(camera, duration=5.0)
                            emotions[0] = result if result is not None else []
                        else:
                            emotions[0] = []
                        Logger.info("Kabu: fer_task finished -> %s", str(emotions[0]))
                    except Exception as e:
                        Logger.info("Kabu: fer_task exception: %s", e)
                        emotions[0] = []

                audio_thread = threading.Thread(target=audio_task, daemon=True)
                fer_thread = threading.Thread(target=fer_task, daemon=True)

                audio_thread.start()
                fer_thread.start()

                # join with timeouts so we remain responsive to stop_event
                audio_thread.join(timeout=35.0)
                fer_thread.join(timeout=12.0)

                # log if threads didn't finish
                if audio_thread.is_alive():
                    Logger.info("Kabu: audio_thread still alive after join timeout")
                if fer_thread.is_alive():
                    Logger.info("Kabu: fer_thread still alive after join timeout")

                user_text = (transcription[0] or "").strip()
                emotion_list = emotions[0] or []
                emotion_str = ", ".join(emotion_list) if emotion_list else "unknown"

                self.full_transcript.append({"speaker": "child", 
                                             "text": user_text, 
                                             "emotions": emotion_list, 
                                             "timestamp": datetime.now(timezone.utc).isoformat()})

                Logger.info("Kabu: got user_text='%s' emotions=%s", str(user_text)[:80], str(emotion_list))

                if user_text == "NO_SPEECH":
                    Logger.info("Kabu: NO_SPEECH detected, continuing")
                    if self._stop_event.wait(0.1):
                        break
                    continue
                if not user_text:
                    if self._stop_event.wait(0.1):
                        break
                    continue

                # rest of original processing (LLM / TTS / append transcript)
                try:
                    Logger.info("Kabu: requesting LLM response")
                    reply = llm.get_kabu_response(f"The child said: \"{user_text}\". Observed emotion(s): {emotion_str}.")
                    parsed = utils.parse_kabu_reply(reply)
                    Logger.info("Kabu: LLM returned")
                    
                    self.full_transcript.append({"speaker": "kabu", 
                                                 "text": parsed['text'],
                                                 "timestamp": datetime.now(timezone.utc).isoformat(),
                                                 "emotion": parsed['emotions']})
                    #If you to know what emotion the bot is giving you have to input parsed['emotions']

                    try:
                        if pipeline:
                            tts.tts_kokoro(pipeline, parsed['text'])
                    except Exception as e:
                        Logger.info("Kabu: tts error: %s", e)
                except Exception as e:
                    Logger.info("Kabu: LLM/processing error: %s", e)

                # short sleep but remain responsive
                if self._stop_event.wait(0.1):
                    break

        except Exception as e:
            Logger.info("Kabu: _run_session_loop top-level exception: %s", e)
        finally:
            Logger.info("Kabu: _run_session_loop finishing, cleaning up")
            
            try:
                analysis_reply = llm.get_kabu_response(ANALYSIS_PROMPT)
                Logger.inf("\n--- Conversation Analysis ---")
                Logger.inf(analysis_reply)
                parsed = utils.parse_kabu_reply_final(analysis_reply)
                Logger.info(parsed["recommendations"])
                Logger.info(parsed["disliked_foods"])
                # persist analysis into history
            except Exception as e:
                Logger.inf("Analysis request failed:", e)

            end = datetime.now(timezone.utc)

            meal_hash ={
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "date": start.date().isoformat(),
            "transcript": self.full_transcript,
            "conversation_suggestions": parsed["recommendations"],
            "ingredient_suggestions": parsed["disliked_foods"]
            }

            meal_id = mongodb.insert_meal(meal_hash)
            Logger.info(f"Meal data saved with meal_id: {meal_id}")

            try:
                if self.camera and hasattr(self.camera, "isOpened") and self.camera.isOpened():
                    self.camera.release()
                    Logger.info("Kabu: camera released in finally")
            except Exception as e:
                Logger.info("Kabu: camera release finally error: %s", e)
            # ensure session thread will exit
            Logger.info("Kabu: _run_session_loop exited")