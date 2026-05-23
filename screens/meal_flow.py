from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.checkbox import CheckBox
from kivy.uix.video import Video
from mainsession.config import CAMERA_INDEX
from services.models import CURRENT_MEAL, init_current_meal, clear_current_meal, SAMPLE_REPORTS
from db import meals_col
from kivy.app import App
from kivy.metrics import dp
from datetime import datetime
from kivy.clock import Clock
import uuid

import json
import sys
import os
from kivy.clock import Clock

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

hash_meal_final = {

}

loading_screen = False

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
            # if colored checkbox do not work use this one and delete the lower code
            # cb = CheckBox(size_hint_x=None, width=30, group=None)
            cb = ColoredCheckBox(size_hint_x=None, width=30, group=None)
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
            # ensure buffer exists
            if not CURRENT_MEAL:
                init_current_meal()

            # collect finished vs not finished from UI
            container = self.ids.food_checkboxes
            finished = []
            not_finished = []
            for row in container.children:
                cb = None
                lbl = None
                for w in row.children:
                    if isinstance(w, CheckBox):
                        cb = w
                    elif hasattr(w, "text"):
                        lbl = w
                name = (lbl.text.strip() if lbl and lbl.text else "").strip()
                if not name:
                    continue
                if cb and cb.active:
                    finished.append(name)
                else:
                    not_finished.append(name)

            # normalize names
            finished = [s.strip() for s in finished]
            not_finished = [s.strip() for s in not_finished]

            # update CURRENT_MEAL fields
            # now = datetime.now()
            # if not CURRENT_MEAL.get("date"):
            #     CURRENT_MEAL["date"] = now.strftime("%B %d, %Y")
            # if not CURRENT_MEAL.get("start_time"):
            #     CURRENT_MEAL["start_time"] = now.strftime("%I:%M %p").lstrip("0")
            # if not CURRENT_MEAL.get("end_time"):
            #     CURRENT_MEAL["end_time"] = now.strftime("%I:%M %p").lstrip("0")

            # # food arrays: before / after / not finished
            CURRENT_MEAL["food_before_meal"] = CURRENT_MEAL.get("food_before_meal", []) or []
            # food_after_meal should be the items NOT checked (leftover / after-meal)
            CURRENT_MEAL["food_after_meal"] = not_finished or []
            # keep explicit not_finished and finished buckets
            CURRENT_MEAL["food_not_finished"] = not_finished or []
            CURRENT_MEAL["food_finished"] = finished or []

            # # dummy portions (if not set)
            # if not CURRENT_MEAL.get("portion_before_image"):
            #     CURRENT_MEAL["portion_before_image"] = "assets/portion_before_dummy.jpg"
            # if not CURRENT_MEAL.get("portion_after_image"):
            #     CURRENT_MEAL["portion_after_image"] = "assets/portion_after_dummy.jpg"

            # # keep existing LLM-generated summary/suggestions if present, otherwise fallback
            # if not CURRENT_MEAL.get("summary"):
            #     CURRENT_MEAL["summary"] = "Auto-generated summary (dummy)."
            # if not CURRENT_MEAL.get("conversation_suggestions"):
            #     CURRENT_MEAL["conversation_suggestions"] = ["Try asking about colors.", "Praise effort."]
            # if not CURRENT_MEAL.get("ingredient_suggestions"):
            #     CURRENT_MEAL["ingredient_suggestions"] = ["Carrots - good source of beta-carotene."]
            global hash_meal_final

            CURRENT_MEAL["start_time"] = hash_meal_final['start_time']
            CURRENT_MEAL["end_time"] = hash_meal_final['end_time']
            CURRENT_MEAL["date"] = hash_meal_final['date']
            CURRENT_MEAL["transcript"] = hash_meal_final['transcript']
            CURRENT_MEAL["conversation_suggestions"] = hash_meal_final['conversation_suggestions']
            CURRENT_MEAL["summary"] = hash_meal_final['summary']
            CURRENT_MEAL["ingredient_suggestions"] = hash_meal_final['ingredient_suggestions']
            CURRENT_MEAL["portion_before_image"] = hash_meal_final['portion_before_image']
            CURRENT_MEAL["portion_after_image"] = hash_meal_final['portion_after_image']

            # ensure _id exists before insert
            if not CURRENT_MEAL.get("_id"):
                CURRENT_MEAL["_id"] = str(uuid.uuid4())

            # attach currently logged-in user's id (if available)
            try:
                app = App.get_running_app()
                current_user = getattr(app, "current_user", None)
                if current_user:
                    if isinstance(current_user, dict):
                        uid = current_user.get("user_id") or current_user.get("id") or current_user.get("_id") or current_user.get("userId")
                    else:
                        uid = getattr(current_user, "user_id", None) or getattr(current_user, "id", None)
                    if uid is not None:
                        CURRENT_MEAL["user_id"] = str(uid)
            except Exception:
                pass

            # Insert into MongoDB and ensure inserted id is a string key used in SAMPLE_REPORTS
            meal_doc = None
            try:
                result = meals_col.insert_one(CURRENT_MEAL)
                inserted_id = str(result.inserted_id)
                Logger.info(f"Inserted meal: {inserted_id}")
                meal_doc = CURRENT_MEAL.copy()
                meal_doc["_id"] = inserted_id
                # ensure inserted doc contains user_id (string)
                if meal_doc.get("user_id") is not None:
                    meal_doc["user_id"] = str(meal_doc["user_id"])
                else:
                    meal_doc["user_id"] = CURRENT_MEAL.get("user_id")
            except Exception as e:
                Logger.info("failed to insert meal to MongoDB: %s", e)
                if not CURRENT_MEAL.get("_id"):
                    CURRENT_MEAL["_id"] = str(uuid.uuid4())
                meal_doc = CURRENT_MEAL.copy()

            # Ensure food_after_meal exists in the stored doc (defensive)
            meal_doc["food_after_meal"] = meal_doc.get("food_after_meal", []) or []
            meal_doc["food_finished"] = meal_doc.get("food_finished", []) or []
            meal_doc["food_not_finished"] = meal_doc.get("food_not_finished", []) or []

            # Update in-memory SAMPLE_REPORTS and select the new meal
            try:
                SAMPLE_REPORTS[str(meal_doc["_id"])] = meal_doc
                app = App.get_running_app()
                app.selected_meal_id = str(meal_doc["_id"])
            except Exception:
                pass

            # Clear current buffer and navigate to dashboard
            clear_current_meal()
            self.manager.current = "dashboard"

        except Exception as e:
            print("❌ finish_meal error:", e)
            Popup(title="", content=Label(text="Failed to finish meal."), size_hint=(0.6,0.3)).open()

transcription = [None]
emotions = [None]
camera = None
start = None

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

SUMMARY_PROMPT = """
            Using all of the context above create a 5 sentence summary of what happened during the meal. DO NOT COPY OTHER FORMATTING MENTIONED ABOVE. (DO NOT MAKE UP STORIES)"""

class SessionPage(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._session_thread = None
        self._stop_event = threading.Event()
        self.camera = None
        self.pipeline = None
        self.full_transcript = []
        self.loading_popup = None
        self.session_finished = False

    def on_pre_enter(self, *args):
        # set default neutral image immediately
        try:
            Clock.schedule_once(lambda dt: self.update_emotion_image(["Neutral"]), 0)
        except Exception:
            pass
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

    def update_emotion_image(self, emotions: list):
        """Pick a video from KabuEmotions based on emotions and show it in the center Video widget."""
        try:
            # choose priority: first known emotion, fallback to neutral
            fname_map = {
                "neutral": "neutral.mp4",
                "happy": "happy.mp4",
                "excited": "excited.mp4",
                "sad": "sad.mp4"
            }
            picked = "neutral.mp4"
            if emotions:
                for e in emotions:
                    if not e:
                        continue
                    key = str(e).strip().lower()
                    if key in fname_map:
                        picked = fname_map[key]
                        break
            video_path = os.path.join(os.path.dirname(__file__), "KabuEmotions", picked)
            if not os.path.exists(video_path):
                # fallback: try just picked name in project root
                video_path = picked
            # set source on main thread
            if 'emos_img' in self.ids:
                video_widget = self.ids.emos_img
                # Stop current video if playing
                if video_widget.state == 'play':
                    video_widget.state = 'stop'
                # Set the video source
                video_widget.source = video_path
                # Set looping option
                video_widget.options = {'eos': 'loop'}
                # Start playing the video
                video_widget.state = 'play'
            Logger.info("Kabu: emotion video set -> %s", video_path)
        except Exception as e:
            Logger.info("Kabu: update_emotion_image error: %s", e)

    def end_session(self, *args):
        try:
            Logger.info("Kabu: end_session pressed - stopping session")
            self.stop_session()
        except Exception as e:
            Logger.info("Kabu: end_session stop error: %s", e)

        # Show non-dismissable loading popup
        if not self.loading_popup:
            content = Label(
                text="Analyzing your meal and saving the report...\nPlease wait.",
                halign="center",
                valign="middle"
            )
            content.bind(size=lambda inst, size: setattr(inst, "text_size", size))

            self.loading_popup = Popup(
                title="Finishing up",
                content=content,
                size_hint=(0.7, 0.3),
                auto_dismiss=False,
            )
        self.loading_popup.open()

        # Start polling for background completion
        self.session_finished = False  # reset before we wait
        Clock.schedule_interval(self._check_session_finished, 0.3)

    def _check_session_finished(self, dt):
        """Poll from main thread until _run_session_loop has finished its cleanup."""
        if not self.session_finished:
            return  # keep waiting

        # Done: stop polling
        Clock.unschedule(self._check_session_finished)

        # Close popup
        if self.loading_popup:
            try:
                self.loading_popup.dismiss()
            except Exception:
                pass
            self.loading_popup = None
        try:
            App.get_running_app().root.current = "inputIngredientsAM"
        except Exception as e:
            Logger.info("Kabu: navigation error after loading: %s", e)
    
    def fmt_time(self,dt):
                    try:
                        return dt.strftime("%I:%M %p").lstrip("0")
                    except Exception:
                        return datetime.now(timezone.utc).strftime("%I:%M %p").lstrip("0")

    def fmt_date(self, dt):
        try:
            s = dt.strftime("%B %d, %Y")
            return s.replace(" 0", " ")
        except Exception:
            return datetime.now(timezone.utc).strftime("%B %d, %Y").replace(" 0", " ")

    def _run_session_loop(self):
        Logger.info("Kabu: _run_session_loop starting")
        start = self.fmt_time(datetime.now())
        try:
 
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
            Kabu_emotion: [Excited, Happy, Neutral, Sad] (Note: EMOTIONS SHOULD ONLY BE FROM THIS LIST: Excited, Happy, Neutral, Sad. Do not create new emotions outside of this list. As much as possible try to switch emotions. If you're concerned then display sad)
            Topic Mentioned: <One word to descibe the topic.>

            FOLLOW THIS EXACT FORMAT IN EVERY RESPONSE. DO NOT DEVIATE FROM IT.
            Example: 
            Kabu: I love talking about animals! They are so much fun. Owls are such interesting creatures, don't you think?
            Kabu_emotion: [Happy]
            Topic Mentioned: Owls
            """ 

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

            topics_mentioned = set()
            first_reply = True

            while not self._stop_event.is_set():
                Logger.info("Kabu: loop iteration start")
                transcription = [None]
                emotions = [None]

                if (first_reply):
                    tts.tts_kokoro(f""" Hi {child_data.get('name')}! I'm so excited to chat with you while you eat your meal!""")
                    first_reply = False

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

                audio_thread.join(timeout=35.0)
                fer_thread.join(timeout=12.0)

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

                try:
                    Logger.info("Kabu: requesting LLM response")
                    reply = llm.get_kabu_response(f"The child said: \"{user_text}\". Observed emotion(s): {emotion_str}.")
                    parsed = utils.parse_kabu_reply(reply)
                    Logger.info("Kabu: LLM returned")
                    
                    self.full_transcript.append({"speaker": "kabu", 
                                                 "text": parsed['text'],
                                                 "timestamp": self.fmt_time(datetime.now(timezone.utc).isoformat()),
                                                 "emotion": parsed['emotions']})

                    try:
                        kabu_emotions = parsed.get('emotions') or []
                        if isinstance(kabu_emotions, str):
                            kabu_emotions = [kabu_emotions]
                        Clock.schedule_once(lambda dt, el=kabu_emotions: self.update_emotion_image(el), 0)
                    except Exception as e:
                        Logger.info("Kabu: failed to schedule Kabu emotion image update: %s", e)

                    try:
                        if pipeline:
                            tts.tts_kokoro( parsed['text'])
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
                Logger.info("\n--- Conversation Analysis ---")
                Logger.info(str(analysis_reply)[:2000])
                parsed = utils.parse_kabu_reply_final(analysis_reply) or {}
                Logger.info("Kabu: analysis parsed keys -> %s", list(parsed.keys()))
            except Exception as e:
                Logger.info("Analysis request failed: %s", e)
                parsed = {"recommendations": [], "disliked_foods": []}

            try:
                end = self.fmt_time(datetime.now())
                Logger.info("Kabu: requesting summary")
                summary = llm.get_kabu_response(SUMMARY_PROMPT) or ""
            except Exception as e:
                Logger.info("Kabu: summary request failed: %s", e)
                summary = ""

            try:
                global loading_screen
                global hash_meal_final
                meal_hash = {
                    "start_time": str(start),
                    "end_time": str(end),
                    "date": datetime.now(timezone.utc).strftime("%B %d, %Y").replace(" 0", " "),
                    "transcript": list(self.full_transcript) if getattr(self, "full_transcript", None) else [],
                    "conversation_suggestions": parsed.get("recommendations", []) if isinstance(parsed, dict) else [],
                    "ingredient_suggestions": parsed.get("disliked_foods", []) if isinstance(parsed, dict) else [],
                    "food_after_meal": ["Placeholder food"],
                    "summary": summary,
                    "portion_before_image": "assets/portion_before_dummy.jpg",
                    "portion_after_image": "assets/portion_after_dummy.jpg",
                }
                loading_screen = True
                hash_meal_final = meal_hash
                # log a concise preview (avoid passing extra args to Logger.info)
                Logger.info(f"Kabu: built hash_meal_final preview -> summary: {summary}")
            except Exception as e:
                Logger.info("Kabu: meal_hash build error: %s", e)
                meal_hash = {}
            try:
                if self.camera and hasattr(self.camera, "isOpened") and self.camera.isOpened():
                    self.camera.release()
                    Logger.info("Kabu: camera released in finally")
            except Exception as e:
                Logger.info("Kabu: camera release finally error: %s", e)

            Logger.info("Kabu: _run_session_loop exited")
            self.session_finished = True

from kivy.graphics import Color, Rectangle
from colors import ACCENT_COLOR, LIGHT_COLOR

class ColoredCheckBox(CheckBox):
    """CheckBox with a colored square background that stays square and reacts to `active`."""
    def __init__(self, **kwargs):
        # ensure explicit sizing so width/height are available during init
        if 'size_hint' not in kwargs and 'size' not in kwargs:
            kwargs.setdefault('size_hint', (None, None))
            kwargs.setdefault('size', (dp(24), dp(24)))
        elif 'size' in kwargs and ('size_hint' not in kwargs):
            kwargs.setdefault('size_hint', (None, None))
 
        super().__init__(**kwargs)
 
        # safe initial bg (use fallback dp size if width/height not set yet)
        init_w = self.width if (self.width and self.width > 0) else dp(24)
        init_h = self.height if (self.height and self.height > 0) else dp(24)
 
        with self.canvas.before:
            self._bg_color = Color(*(ACCENT_COLOR if self.active else LIGHT_COLOR))
            # draw rectangle; we'll resize/center it in _update_graphics
            self._bg = Rectangle(pos=self.pos, size=(init_w, init_h))
 
        # bind updates
        self.bind(pos=self._update_graphics, size=self._update_graphics, active=self._on_active_changed)
 
        # ensure initial geometry is correct
        Clock.schedule_once(lambda dt: self._update_graphics(), 0)
 
    def _update_graphics(self, *a):
        try:
            w = self.width if self.width and self.width > 0 else dp(24)
            h = self.height if self.height and self.height > 0 else dp(24)
            box_size = min(w, h)
            x = self.x + (w - box_size) / 2
            y = self.y + (h - box_size) / 2
            self._bg.pos = (x, y)
            self._bg.size = (box_size, box_size)
        except Exception:
            pass
 
    def _on_active_changed(self, inst, value):
        try:
            self._bg_color.rgba = ACCENT_COLOR if value else LIGHT_COLOR
        except Exception:
            pass

