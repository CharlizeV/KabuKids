import kivy
kivy.require('2.0.0')
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle, Ellipse, Rectangle
from kivy.properties import StringProperty, ListProperty
from kivy.uix.popup import Popup
from kivy.uix.checkbox import CheckBox
from kivy.uix.textinput import TextInput
from colors import SECONDARY_COLOR, DARK_COLOR
from kivy.clock import Clock
import threading
import os
import certifi
from pymongo import MongoClient
from pymongo.server_api import ServerApi

from kivy.core.window import Window
from kivy.utils import platform
from kivy.uix.stencilview import StencilView

import uuid
from datetime import datetime

from kivy.core.window import Window
from kivy.uix.image import Image

import uuid
from datetime import datetime

try:
    from tkinter import Tk
    from tkinter.filedialog import askopenfilename
except ImportError:
    pass

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'mainsession'))
from mainsession import stt, llm, tts, mongodb, fer, utils, Kabu_V1

# ====== MongoDB Setup ======
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb+srv://kabu_db_user:pass101pass101@cluster0.kxhmgjt.mongodb.net/")
client = MongoClient(
    MONGODB_URI,
    server_api=ServerApi("1"),
    tls=True,
    tlsCAFile=certifi.where(),
    serverSelectionTimeoutMS=5000,
)
db = client["kabu_db_user"]
meals_col = db["Meals"]

# Global variable to hold fetched reports (will be filled after async load)
SAMPLE_REPORTS = {}

# In-memory buffer for the current meal being recorded across screens
CURRENT_MEAL = {}

def init_current_meal(user_id=None):
    """Initialize CURRENT_MEAL with defaults and attach user_id if provided."""
    global CURRENT_MEAL
    CURRENT_MEAL = {
        "_id": str(uuid.uuid4()),
        "user_id": str(user_id) if user_id else "",
        "date": "",
        "start_time": "",
        "end_time": "",
        "transcript": [],
        "summary": "",
        "conversation_suggestions": [],
        "ingredient_suggestions": [],
        "food_before_meal": [],
        "food_not_finished": [],
        "portion_before_image": "",
        "portion_after_image": "",
    }

def clear_current_meal():
    global CURRENT_MEAL
    CURRENT_MEAL = {}

def fetch_reports_from_db(callback):
    """Fetch all meal reports from MongoDB (run in background thread)."""
    try:
        cursor = meals_col.find({})
        reports = {doc["_id"]: doc for doc in cursor}
        callback(reports)
    except Exception as e:
        print("❌ Error fetching from MongoDB:", e)
        callback({})

# --- new: fetch only reports for a specific user_id ---
def fetch_reports_for_user(user_id, callback):
    """Fetch meal reports for a single user (by user_id)."""
    try:
        if not user_id:
            callback({})
            return
        cursor = meals_col.find({"user_id": str(user_id)})
        reports = {doc["_id"]: doc for doc in cursor}
        callback(reports)
    except Exception as e:
        print("❌ Error fetching user reports:", e)
        callback({})

# Helper to create rounded background (unchanged)
def add_rounded_background(widget, radius=8):
    with widget.canvas.before:
        Color(0.95, 0.95, 0.95, 1)
        widget.rect = RoundedRectangle(
            pos=widget.pos,
            size=widget.size,
            radius=[dp(radius)]
        )
    widget.bind(pos=lambda obj, pos: setattr(widget.rect, 'pos', pos))
    widget.bind(size=lambda obj, size: setattr(widget.rect, 'size', size))


# Helper function to create a rounded rectangle background
def add_rounded_background(widget, radius=8):
    with widget.canvas.before:
        Color(0.95, 0.95, 0.95, 1)
        widget.rect = RoundedRectangle(
            pos=widget.pos,
            size=widget.size,
            radius=[dp(radius)]
        )
    widget.bind(pos=lambda obj, pos: setattr(widget.rect, 'pos', pos))
    widget.bind(size=lambda obj, size: setattr(widget.rect, 'size', size))

class MealItem(BoxLayout):
    def __init__(self, meal_id, date, start_time, end_time, **kwargs):
        self.meal_id = meal_id  # ← Store report ID
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(60)
        self.spacing = dp(10)
        
        # Add rounded background
        with self.canvas.before:
            Color(0.95, 0.95, 0.95, 1)
            self.rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(8)]
            )
        self.bind(pos=self._update_rect, size=self._update_rect)

        # Info layout
        info_layout = BoxLayout(orientation='vertical', padding=[dp(10), dp(5)])
        
        # Date label
        info_layout.add_widget(Label(
            text=date,
            font_size='14sp',
            size_hint_y=None,
            height=dp(20)
        ))
        
        # Time label
        info_layout.add_widget(Label(
            text=f"Start: {start_time} | End: {end_time}",
            font_size='12sp',
            color=(0.4, 0.4, 0.4, 1),
            size_hint_y=None,
            height=dp(16)
        ))
        
        self.add_widget(info_layout)

        # More button
        more_btn = Button(
            text="More",
            size_hint_x=None,
            width=dp(70)
        )
        more_btn.bind(on_press=self.go_to_report)
        self.add_widget(more_btn)

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def go_to_report(self, instance):
        app = App.get_running_app()
        app.selected_meal_id = self.meal_id  # ← Save which report was clicked
        app.root.current = "report"

# Define all screen classes
class SplashScreen(Screen):
    pass

class LoginPage(Screen):
    def show_message(self, message):
        popup = Popup(
            title="",
            content=Label(text=message, halign='center', text_size=(300, None)),
            size_hint=(0.6, 0.3)
        )
        popup.open()

    def login(self):
        try:
            username = self.ids.username_input.text.strip() if 'username_input' in self.ids else ""
            password = self.ids.password_input.text.strip() if 'password_input' in self.ids else ""

            if not username or not password:
                self.show_message("Please enter both username and password.")
                return

            # Query the Children collection for matching credentials
            user = db["Children"].find_one({"username": username, "password": password})
            if user:
                app = App.get_running_app()
                app.current_user = user  # store the user document on the app instance
                # Navigate to dashboard
                self.manager.current = "dashboard"
            else:
                self.show_message("Invalid username or password.")

        except Exception as e:
            print("❌ Login error:", e)
            self.show_message("Login failed. Check your connection and try again.")

class MakeAccountPage(Screen):
    def remove_tag(self, tag_layout):
        parent = tag_layout.parent
        parent.remove_widget(tag_layout)
        parent.height = parent.minimum_height if parent.children else 40

    def add_tag_prompt(self, section):
        content = BoxLayout(orientation='vertical', padding=15, spacing=10)
        text_input = TextInput(
            hint_text="Enter tag...",
            font_size='16sp',
            multiline=False,
            size_hint_y=None,
            height=40
        )
        btn_layout = BoxLayout(spacing=10, size_hint_y=None, height=40)
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
        tag_box = BoxLayout(size_hint_y=None, height=30, spacing=5)

        # Background for tag box
        with tag_box.canvas.before:
            Color(0.8, 0.8, 0.8, 1)
            tag_box.rect = Rectangle(pos=tag_box.pos, size=tag_box.size)

        tag_box.bind(
            pos=lambda obj, pos: setattr(obj.rect, 'pos', pos),
            size=lambda obj, size: setattr(obj.rect, 'size', size)
        )

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

        if section == "likes":
            container = self.ids.likes_container
        elif section == "dislikes":
            container = self.ids.dislikes_container
        elif section == "goals":
            container = self.ids.goals_container
        else:
            return

        # Insert before the "+" button (last child)
        container.add_widget(tag_box, len(container.children) - 1)
        container.height = container.minimum_height

    def get_tags_from_container(self, container_id):
        container = self.ids[container_id]
        tags = []
        # container.children is LIFO (last added first). Each tag is a BoxLayout containing a Label and a Button.
        for child in container.children:
            if not isinstance(child, BoxLayout):
                continue
            found = None
            for w in child.children:
                if hasattr(w, 'text') and w.text and w.text != "×":
                    found = w
                    break
            if found:
                tags.append(found.text)
            else:
                # debug help if something unexpected appears
                print("Warning: no text widget found in tag child:", [type(w) for w in child.children])
        tags.reverse()  # return in visual (first-added) order
        return tags

    def show_message(self, message):
        popup = Popup(
            title="",
            content=Label(text=message, halign='center', text_size=(300, None)),
            size_hint=(0.6, 0.3)
        )
        popup.open()

    def save_profile(self):
        try:
            name = self.ids.name_input.text.strip()
            birthday = self.ids.birthday_input.text.strip()
            gender = self.ids.gender_input.text.strip()
            username = self.ids.username_input.text.strip()
            password = self.ids.password_input.text.strip()

            if not name:
                self.show_message("Please enter a name.")
                return

            likes = self.get_tags_from_container("likes_container")
            dislikes = self.get_tags_from_container("dislikes_container")
            goals = self.get_tags_from_container("goals_container")

            # Get image path from app
            app = App.get_running_app()
            image_path = app.profile_image_path

            child_doc = {
                "_id": str(uuid.uuid4()),
                "name": name,
                "username": username,
                "password": password,
                "birthday": birthday,
                "gender": gender,
                "likes": likes,
                "dislikes": dislikes,
                "goals": goals,
                "profile_picture": image_path,
                "created_at": datetime.utcnow(),
            }

            # Save to MongoDB
            result = db["Children"].insert_one(child_doc)
            print(f"✅ Child profile saved with ID: {result.inserted_id}")

            self.show_message("Profile saved successfully!")
            self.manager.current = "login"

        except Exception as e:
            print("❌ Error saving profile:", e)
            self.show_message("Failed to save. Check your internet connection.")

class DashboardPage(Screen):
    _reports_loaded = False
    user_name = StringProperty("User Name")   # <-- new property

    def on_enter(self, *args):
        # update displayed user name from the logged-in user
        app = App.get_running_app()
        current_user = getattr(app, "current_user", None)
        if current_user:
            try:
                if isinstance(current_user, dict):
                    name = current_user.get("name") or current_user.get("username") or "User"
                else:
                    name = getattr(current_user, "name", None) or getattr(current_user, "username", "User")
            except Exception:
                name = "User"
            self.user_name = name
        else:
            self.user_name = "User"

        if not self._reports_loaded:
            self.ids.meals_list.clear_widgets()
            self.load_reports_from_db()
        else:
            self._populate_list()

    def load_reports_from_db(self):
        # Get current user id from the running app
        app = App.get_running_app()
        current_user = getattr(app, "current_user", None)
        if not current_user:
            # no user logged in -> show empty list/placeholder
            Clock.schedule_once(lambda dt: self._populate_list(), 0)
            return

        # extract user_id (works for dict returned by pymongo)
        user_id = None
        try:
            if isinstance(current_user, dict):
                user_id = str(current_user.get("_id"))
            else:
                user_id = str(getattr(current_user, "_id", None))
        except Exception:
            user_id = None

        def on_reports_fetched(reports):
            global SAMPLE_REPORTS
            SAMPLE_REPORTS = reports
            self._reports_loaded = True
            Clock.schedule_once(lambda dt: self._populate_list(), 0)

        thread = threading.Thread(target=fetch_reports_for_user, args=(user_id, on_reports_fetched))
        thread.daemon = True
        thread.start()

    def _populate_list(self):
        self.ids.meals_list.clear_widgets()
        # self.ids.loading_label.text = ""  # ← REMOVED

        if not SAMPLE_REPORTS:
            self.ids.meals_list.add_widget(Label(text="No reports found.", size_hint_y=None, height=dp(40)))
            return

        # Build a list and sort by timestamp (newest first).
        def _extract_timestamp(report):
            # Prefer explicit datetime fields
            for key in ("created_at", "createdAt", "created"):
                v = report.get(key)
                if isinstance(v, datetime):
                    return v
                if isinstance(v, str):
                    # try iso format first
                    try:
                        return datetime.fromisoformat(v)
                    except Exception:
                        pass
                    # try common formats
                    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S", "%B %d, %Y"):
                        try:
                            return datetime.strptime(v, fmt)
                        except Exception:
                            continue
            # fallback: try combining "date" and "start_time"
            date_str = report.get("date", "") or ""
            time_str = report.get("start_time", "") or ""
            if date_str:
                try:
                    dt = datetime.strptime(date_str, "%B %d, %Y")
                    if time_str:
                        try:
                            tt = datetime.strptime(time_str, "%I:%M %p")
                            dt = dt.replace(hour=tt.hour, minute=tt.minute)
                        except Exception:
                            pass
                    return dt
                except Exception:
                    pass
            return datetime.min

        reports = list(SAMPLE_REPORTS.values())
        reports.sort(key=_extract_timestamp, reverse=True)

        for report in reports:
            item = MealItem(
                meal_id=report.get("_id", ""),
                date=report.get("date", ""),
                start_time=report.get("start_time", ""),
                end_time=report.get("end_time", "")
            )
            self.ids.meals_list.add_widget(item)

class ProfilePage(Screen):
    # values bound to KV
    display_name = StringProperty("")
    username_text = StringProperty("")
    birthday_text = StringProperty("")
    gender_text = StringProperty("")
    profile_image_source = StringProperty("")
    likes = ListProperty([])
    dislikes = ListProperty([])
    goals = ListProperty([])

    def on_pre_enter(self, *args):
        """Populate profile UI from the logged-in user (App.current_user)."""
        app = App.get_running_app()
        user = getattr(app, "current_user", None)

        if user:
            if isinstance(user, dict):
                self.display_name = user.get("name") or ""
                self.username_text = user.get("username") or ""
                self.birthday_text = user.get("birthday") or ""
                self.gender_text = user.get("gender") or ""
                src = user.get("profile_picture") or ""
                self.likes = user.get("likes", []) or []
                self.dislikes = user.get("dislikes", []) or []
                self.goals = user.get("goals", []) or []
            else:
                # fallback for object-like user
                self.display_name = getattr(user, "name", "") or ""
                self.username_text = getattr(user, "username", "") or ""
                self.birthday_text = getattr(user, "birthday", "") or ""
                self.gender_text = getattr(user, "gender", "") or ""
                src = getattr(user, "profile_picture", "") or ""
                self.likes = getattr(user, "likes", []) or []
                self.dislikes = getattr(user, "dislikes", []) or []
                self.goals = getattr(user, "goals", []) or []

            if src:
                try:
                    if not os.path.isabs(src):
                        src = os.path.abspath(src)
                except Exception:
                    pass
                self.profile_image_source = src
            else:
                # optional fallback to global app path
                self.profile_image_source = getattr(app, "profile_image_path", "") or ""
        else:
            # no user — clear everything
            self.display_name = ""
            self.username_text = ""
            self.birthday_text = ""
            self.gender_text = ""
            self.profile_image_source = ""
            self.likes = []
            self.dislikes = []
            self.goals = []

        # populate the likes/dislikes/goals containers in KV
        Clock.schedule_once(lambda dt: self._populate_containers(), 0)

    def _populate_containers(self):
        def make_label(text):
            lbl = Label(text=text, halign="left", valign="top", size_hint_y=None)
            lbl.bind(width=lambda inst, w: setattr(inst, "text_size", (w, None)))
            lbl.bind(texture_size=lambda inst, ts: setattr(inst, "height", inst.texture_size[1]))
            return lbl

        # likes
        if "likes_container" in self.ids:
            c = self.ids.likes_container
            c.clear_widgets()
            if not self.likes:
                c.add_widget(make_label("• None"))
            else:
                for item in self.likes:
                    c.add_widget(make_label(f"• {item}"))

        # dislikes
        if "dislikes_container" in self.ids:
            c = self.ids.dislikes_container
            c.clear_widgets()
            if not self.dislikes:
                c.add_widget(make_label("• None"))
            else:
                for item in self.dislikes:
                    c.add_widget(make_label(f"• {item}"))

        # goals
        if "goals_container" in self.ids:
            c = self.ids.goals_container
            c.clear_widgets()
            if not self.goals:
                c.add_widget(make_label("• None"))
            else:
                for item in self.goals:
                    c.add_widget(make_label(f"• {item}"))

class ReportPage(Screen):
    date = StringProperty("")
    time_range = StringProperty("")
    summary_text = StringProperty("")
    food_before_text = StringProperty("")
    food_not_finished_text = StringProperty("")
    portion_before_source = StringProperty("")
    portion_after_source = StringProperty("")
    formatted_ingredient_suggestions = StringProperty("")
    formatted_conversation_suggestions = StringProperty("")

    def on_pre_enter(self, *args):
        app = App.get_running_app()
        meal_id = app.selected_meal_id

        if not meal_id or meal_id not in SAMPLE_REPORTS:
            # Fallback or error handling
            self.date = "N/A"
            self.summary_text = "Report not found."
            return

        data = SAMPLE_REPORTS[meal_id]

        # Date & time
        self.date = data["date"]
        self.time_range = f"{data['start_time']} – {data['end_time']}"

        # Summary
        self.summary_text = data.get("summary", "No summary available.")

        # Food lists (with real newlines)
        self.food_before_text = "\n".join([f"• {food}" for food in data["food_before_meal"]])
        self.food_not_finished_text = "\n".join([f"• {food}" for food in data["food_not_finished"]]) if data["food_not_finished"] else "• None"

        # Images
        self.portion_before_source = data["portion_before_image"]
        self.portion_after_source = data["portion_after_image"]

        # Suggestions (with real newlines)
        self.formatted_ingredient_suggestions = "\n".join([f"• {s}" for s in data["ingredient_suggestions"]])
        self.formatted_conversation_suggestions = "\n".join([f'• "{s}"' for s in data["conversation_suggestions"]])

class TranscriptPage(Screen):
    def on_pre_enter(self, *args):
        content = self.ids.transcript_content
        content.clear_widgets()

        app = App.get_running_app()
        meal_id = getattr(app, 'selected_meal_id', None)

        if not meal_id or meal_id not in SAMPLE_REPORTS:
            error = Label(
                text="Transcript not found.",
                color=DARK_COLOR,
                font_size='16sp',
                halign='left',
                valign='top',
                size_hint_x=1,
                size_hint_y=None,
                height=dp(40)
            )
            error.bind(
                width=lambda inst, w: setattr(inst, 'text_size', (w - dp(20), None)),
                texture_size=lambda inst, size: setattr(inst, 'height', size[1])
            )
            content.add_widget(error)
            return

        report = SAMPLE_REPORTS[meal_id]
        for msg in report["transcript"]:
            role = msg["role"]
            text = msg["text"]
            emotion = msg.get("emotion", "neutral")

            # Message container
            msg_box = BoxLayout(
                orientation='vertical',
                size_hint_y=None,
                size_hint_x=1,
                height=dp(10),
                padding=[0, 0, 0, dp(10)]
            )

            # Speaker label
            # Build header row: "Speaker (11:00 AM):" + optional dislike button on the right
            # try to find a time field in the message (supports several keys)
            time_val = None
            for time_key in ("time", "timestamp", "time_str", "created_at"):
                if time_key in msg and msg[time_key]:
                    time_val = msg[time_key]
                    break
            # simple formatting for datetime objects; otherwise use string as-is
            if isinstance(time_val, datetime):
                time_str = time_val.strftime("%I:%M %p").lstrip("0")
            else:
                time_str = str(time_val) if time_val else ""

            speaker_text = ("Kabu" if role == "Kabu" else "Name")
            if time_str:
                speaker_text = f"{speaker_text} ({time_str}):"
            else:
                speaker_text = f"{speaker_text}:"

            # Make label size to its content so the dislike button can sit right after it
            header_row = BoxLayout(size_hint_y=None, height=dp(20), spacing=dp(6))
            speaker_label = Label(
                text=speaker_text,
                font_size='16sp',
                bold=True,
                color=SECONDARY_COLOR,
                halign='left',
                valign='middle',
                size_hint_x=None,
                size_hint_y=None,
                height=dp(20)
            )
            # size label to its texture width so it doesn't expand and push the button away
            speaker_label.bind(texture_size=lambda inst, ts: setattr(inst, 'width', inst.texture_size[0] + dp(4)))
            speaker_label.bind(texture_size=lambda inst, ts: setattr(inst, 'height', max(dp(20), inst.texture_size[1])))
            header_row.add_widget(speaker_label)
 
             # Emotion label
            emotion_label = Label(
                text=f"[{emotion}]",
                font_size='12sp',
                color=(0.4, 0.4, 0.4, 1),
                halign='left',
                valign='top',
                size_hint_x=1,
                size_hint_y=None,
                height=dp(16)
            )
            emotion_label.bind(
                width=lambda inst, w: setattr(inst, 'text_size', (w - dp(20), None)),
                texture_size=lambda inst, size: setattr(inst, 'height', size[1])
            )
 
            # Message text
            msg_label = Label(
                text=text,
                font_size='16sp',
                color=DARK_COLOR,
                halign='left',
                valign='top',
                size_hint_x=1,
                size_hint_y=None,
                height=dp(30)
            )
            msg_label.bind(
                width=lambda inst, w: setattr(inst, 'text_size', (w - dp(20), None)),
                texture_size=lambda inst, size: setattr(inst, 'height', size[1])
            )
 
            # add header (speaker + optional dislike button), emotion, message
            # place dislike button into header_row so it aligns with speaker/time
            if role == "Kabu":
                # pass the exact message text into the popup handler so it can be saved with the reason
                dislike_btn = Button(
                    size_hint_x=None,
                    width=dp(24),
                    height=dp(18),
                    background_normal='',
                    background_color=(1, 0, 0, 1)
                )
                dislike_btn.bind(on_press=lambda inst, m=text: self.open_dislike_popup(m))
                # add button immediately after label (left side)
                header_row.add_widget(dislike_btn)
            # spacer to push nothing to the right (keeps left alignment)
            header_row.add_widget(BoxLayout())
            msg_box.add_widget(header_row)
            msg_box.add_widget(emotion_label)
            msg_box.add_widget(msg_label)
 
            # Auto height
            msg_box.bind(minimum_height=msg_box.setter('height'))
            content.add_widget(msg_box)

    def open_dislike_popup(self, message_text):
        """Open popup asking why user dislikes this specific response.
        When submitted, append formatted entry to user's 'dislikes' in DB:
            (reason(s)) - "message_text"
        """
        content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(12))

        title = Label(
            text="What do you dislike about this response?",
            font_size='16sp',
            halign='left',
            size_hint_y=None,
            height=dp(40)
        )
        title.bind(width=lambda w, width: setattr(title, 'text_size', (width - dp(40), None)))
        content.add_widget(title)

        options = ["Ineffective", "Distracting", "Doesn't relate to interest", "Other"]
        check_items = []
        for opt in options:
            row = BoxLayout(size_hint_y=None, height=dp(32), spacing=dp(8))
            cb = CheckBox(size_hint_x=None, width=dp(30), height=dp(30))
            lbl = Label(text=opt, font_size='14sp', halign='left', size_hint_x=1, height=dp(30))
            lbl.bind(width=lambda w, width: setattr(lbl, 'text_size', (width - dp(40), None)))
            row.add_widget(cb)
            row.add_widget(lbl)
            content.add_widget(row)
            check_items.append((cb, opt))

        other = TextInput(hint_text="Specify other...", size_hint_y=None, height=dp(40))
        content.add_widget(other)

        def on_submit(btn, popup):
            selected = [opt for cb, opt in check_items if cb.active]
            other_text = other.text.strip()
            if other_text:
                selected.append(other_text)
            if not selected:
                # require at least one reason
                Popup(title="", content=Label(text="Please select or enter a reason.", halign='center'), size_hint=(0.6,0.3)).open()
                return
            reason_str = "; ".join(selected)
            entry = f"{reason_str} - \"{message_text}\""

            # Save into user's dislikes array in DB
            try:
                app = App.get_running_app()
                user = getattr(app, "current_user", None)
                if user:
                    user_id = user.get("_id") if isinstance(user, dict) else getattr(user, "_id", None)
                    if user_id:
                        db["Children"].update_one({"_id": user_id}, {"$push": {"dislikes": entry}})
                        # refresh in-memory user doc
                        try:
                            updated = db["Children"].find_one({"_id": user_id})
                            app.current_user = updated
                        except Exception:
                            pass
                        # update profile UI if present
                        try:
                            prof = self.manager.get_screen("profile")
                            Clock.schedule_once(lambda dt: prof.on_pre_enter(), 0)
                        except Exception:
                            pass
            except Exception as e:
                print("❌ dislike submit error:", e)

            popup.dismiss()
            Popup(title="", content=Label(text="Thanks for the feedback."), size_hint=(0.6,0.3)).open()

        submit = Button(text="Submit", size_hint_y=None, height=dp(44))
        popup = Popup(title='', content=content, size_hint=(0.86, 0.62))
        submit.bind(on_press=lambda btn: on_submit(btn, popup))
        content.add_widget(submit)
        popup.open()
        self.popup = popup

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

class EditProfilePage(Screen):
    profile_data = StringProperty("")   # << add this

    def remove_tag(self, tag_layout):
        parent = tag_layout.parent
        parent.remove_widget(tag_layout)
        # Optional: update container height
        parent.height = parent.minimum_height if parent.children else 40

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
        if section == "likes":
            container = self.ids.likes_container
        elif section == "dislikes":
            container = self.ids.dislikes_container
        elif section == "goals":
            container = self.ids.goals_container
        else:
            return

        # Insert before the "+" button (which is the last child)
        container.add_widget(tag_box, len(container.children) - 1)
        container.height = container.minimum_height

    def on_pre_enter(self, *args):
        app = App.get_running_app()
        user = getattr(app, "current_user", None)
        if not user:
            return

        # fill simple fields
        try:
            if isinstance(user, dict):
                self.ids.name_input.text = user.get("name", "")
                self.ids.username_input.text = user.get("username", "")
                # do not prefill password for security
                self.ids.password_input.text = ""
                self.ids.birthday_input.text = user.get("birthday", "")
                self.ids.gender_input.text = user.get("gender", "")
                likes = user.get("likes", []) or []
                dislikes = user.get("dislikes", []) or []
                goals = user.get("goals", []) or []
                existing_pic = user.get("profile_picture", "") or ""
            else:
                self.ids.name_input.text = getattr(user, "name", "") or ""
                self.ids.username_input.text = getattr(user, "username", "") or ""
                self.ids.password_input.text = ""
                self.ids.birthday_input.text = getattr(user, "birthday", "") or ""
                self.ids.gender_input.text = getattr(user, "gender", "") or ""
                likes = getattr(user, "likes", []) or []
                dislikes = getattr(user, "dislikes", []) or []
                goals = getattr(user, "goals", []) or []
                existing_pic = getattr(user, "profile_picture", "") or ""
        except Exception as e:
            print("❌ EditProfilePage.on_pre_enter:", e)
            likes = dislikes = goals = []
            existing_pic = ""

        # determine which picture to show on the edit screen:
        # prefer a recently selected image (app.profile_image_path), otherwise use the stored user picture
        app_pic = getattr(App.get_running_app(), "profile_image_path", "") or ""
        pic_to_show = app_pic if app_pic else existing_pic
        if pic_to_show:
            try:
                if not os.path.isabs(pic_to_show):
                    pic_to_show = os.path.abspath(pic_to_show)
            except Exception:
                pass
            try:
                if 'profile_image' in self.ids:
                    self.ids.profile_image.source = pic_to_show
                    self.ids.profile_image.reload()
            except Exception as e:
                print("EditProfilePage: failed to set profile image:", e)

        # rebuild containers: ensure '+' button is first, then tags
        def rebuild(section_id, tags):
            cont = self.ids[section_id]
            cont.clear_widgets()
            # add '+' button
            plus = Button(text="+", size_hint_y=None, height=30,
                          font_size='20sp', background_normal='',
                          background_color=(0.85, 0.85, 0.85, 1), color=(0,0,0,1))
            # section name: likes/dislikes/goals
            sec_name = section_id.replace("_container", "")
            plus.bind(on_release=lambda btn, s=sec_name: self.add_tag_prompt(s))
            cont.add_widget(plus)
            # add tags
            for t in tags:
                self.add_tag_to_section(sec_name, t)

        rebuild("likes_container", likes)
        rebuild("dislikes_container", dislikes)
        rebuild("goals_container", goals)


    def add_tag_to_section(self, section, text):
        """Add one visual tag box to <section>_container."""
        try:
            cont = self.ids[f"{section}_container"]
        except Exception:
            return
        if not text:
            return
        tag_box = BoxLayout(size_hint_y=None, height=30, spacing=5)
        # background rectangle
        with tag_box.canvas.before:
            Color(0.8, 0.8, 0.8, 1)
            Rectangle(pos=tag_box.pos, size=tag_box.size)
        # keep background geometry updated
        def _update_rect(inst, *l):
            for instr in tag_box.canvas.before.children:
                # Rectangle is last in canvas.before children; update it
                if isinstance(instr, Rectangle):
                    instr.pos = tag_box.pos
                    instr.size = tag_box.size
        tag_box.bind(pos=_update_rect, size=_update_rect)

        lbl = Label(text=str(text), font_size='14sp', color=(0,0,0,1),
                    halign='left', valign='center', text_size=(None, None))
        # ensure wrapping/height
        lbl.bind(width=lambda inst, w: setattr(inst, "text_size", (w, None)))
        lbl.bind(texture_size=lambda inst, ts: setattr(inst, "height", inst.texture_size[1]))

        btn = Button(text="×", size_hint_x=None, width=25, background_normal='',
                     background_color=(1, 0.4, 0.4, 1), color=(1,1,1,1), font_size='16sp')
        btn.bind(on_release=lambda b: self.remove_tag(tag_box))

        tag_box.add_widget(lbl)
        tag_box.add_widget(btn)
        cont.add_widget(tag_box)


    def add_tag_prompt(self, section):
        """Open a small popup to add a tag to section."""
        ti = TextInput(hint_text="Tag", multiline=False, size_hint_y=None, height=40)
        def on_ok(instance):
            val = ti.text.strip()
            if val:
                self.add_tag_to_section(section, val)
            popup.dismiss()
        ok = Button(text="Add", size_hint_y=None, height=40, on_release=on_ok)
        box = BoxLayout(orientation='vertical', spacing=8, padding=8)
        box.add_widget(ti)
        box.add_widget(ok)
        popup = Popup(title=f"Add to {section}", content=box, size_hint=(0.8, 0.3))
        popup.open()


    def remove_tag(self, widget):
        parent = widget.parent
        if parent:
            parent.remove_widget(widget)


    def _collect_tags(self, container_id):
        container = self.ids[container_id]
        tags = []
        # container.children is LIFO (last added first). Each tag is a BoxLayout containing a Label and a Button.
        for child in container.children:
            if not isinstance(child, BoxLayout):
                continue
            found = None
            for w in child.children:
                if hasattr(w, 'text') and w.text and w.text != "×":
                    found = w
                    break
            if found:
                tags.append(found.text)
            else:
                # debug help if something unexpected appears
                print("Warning: no text widget found in tag child:", [type(w) for w in child.children])
        tags.reverse()  # return in visual (first-added) order
        return tags


    def save_profile(self):
        try:
            app = App.get_running_app()
            user = getattr(app, "current_user", None)
            if not user:
                Popup(title="", content=Label(text="No user logged in."), size_hint=(0.6,0.3)).open()
                return
            user_id = user.get("_id") if isinstance(user, dict) else getattr(user, "_id", None)
            if not user_id:
                Popup(title="", content=Label(text="Missing user id."), size_hint=(0.6,0.3)).open()
                return

            name = self.ids.name_input.text.strip()
            username = self.ids.username_input.text.strip()
            password = self.ids.password_input.text.strip()
            birthday = self.ids.birthday_input.text.strip()
            gender = self.ids.gender_input.text.strip()

            # determine profile picture to save:
            app_path = getattr(App.get_running_app(), "profile_image_path", "") or ""
            existing_pic = user.get("profile_picture") if isinstance(user, dict) else getattr(user, "profile_picture", "")
            pic_to_save = app_path if app_path else (existing_pic or "")

            update = {
                "name": name,
                "username": username,
                "birthday": birthday,
                "gender": gender,
                "profile_picture": pic_to_save,
                "likes": self._collect_tags("likes_container"),
                "dislikes": self._collect_tags("dislikes_container"),
                "goals": self._collect_tags("goals_container"),
            }
            # only set password if provided (you may want to hash it)
            if password:
                update["password"] = password

            result = db["Children"].update_one({"_id": user_id}, {"$set": update})
            if result.matched_count:
                updated = db["Children"].find_one({"_id": user_id})
                app.current_user = updated

                # update UI images immediately in other screens if present
                try:
                    prof = self.manager.get_screen("profile")
                    if 'profile_image' in prof.ids:
                        prof.ids.profile_image.source = pic_to_save
                        prof.ids.profile_image.reload()
                except Exception:
                    pass
                try:
                    make = self.manager.get_screen("make_account")
                    if 'profile_image' in make.ids:
                        make.ids.profile_image.source = pic_to_save
                        make.ids.profile_image.reload()
                except Exception:
                    pass
                try:
                    # also update this edit screen's image (in case it was not updated)
                    if 'profile_image' in self.ids:
                        self.ids.profile_image.source = pic_to_save
                        self.ids.profile_image.reload()
                except Exception:
                    pass

                Popup(title="", content=Label(text="Profile saved."), size_hint=(0.6,0.3)).open()
            else:
                Popup(title="", content=Label(text="Save failed: user not found."), size_hint=(0.6,0.3)).open()

        except Exception as e:
            print("❌ save_profile error:", e)
            Popup(title="", content=Label(text="Failed to save."), size_hint=(0.6,0.3)).open()
class SessionPage(Screen):
    pass

class WindowManager(ScreenManager):
    pass

# Load the kv file
kv = Builder.load_file("KabuKids.kv")

class MultiScreenApp(App):
    profile_image_path = StringProperty("")

    def build(self):
        # Make sure your ScreenManager includes 'make_account'
        from kivy.lang import Builder
        return Builder.load_file('KabuKids.kv')  # or use Builder.load_string below

    def select_profile_picture(self):
        if platform in ('android', 'ios'):
            from plyer import filechooser
            filechooser.open_file(
                on_selection=self._on_image_selected,
                filters=["*jpg", "*jpeg", "*png", "*bmp", "*gif"]
            )
        else:
            # Desktop (Windows/macOS/Linux)
            try:
                Tk().withdraw()
                path = askopenfilename(
                    title="Select Profile Picture",
                    filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.gif")]
                )
                if path:
                    self._on_image_selected([path])
            except Exception as e:
                print("File chooser error:", e)
                self._on_image_selected([])

    def _on_image_selected(self, selection):
        if not selection:
            return
        path = selection[0]
        path = os.path.abspath(path)  # normalize path
        # Ensure UI update happens on the main thread
        def set_image(dt):
            try:
                self.profile_image_path = path
                # update make_account image if exists
                try:
                    make_screen = self.root.get_screen('make_account')
                    if 'profile_image' in make_screen.ids:
                        img_widget = make_screen.ids.profile_image
                        img_widget.source = path
                        img_widget.reload()
                except Exception:
                    pass
                # update edit_profile image if exists
                try:
                    edit_screen = self.root.get_screen('editProfile')
                    if 'profile_image' in edit_screen.ids:
                        img_widget = edit_screen.ids.profile_image
                        img_widget.source = path
                        img_widget.reload()
                except Exception:
                    pass
                # update profile page image if exists
                try:
                    profile_screen = self.root.get_screen('profile')
                    if 'profile_image' in profile_screen.ids:
                        img_widget = profile_screen.ids.profile_image
                        img_widget.source = path
                        img_widget.reload()
                except Exception:
                    pass
            except Exception as e:
                print("Image update error:", e)
        Clock.schedule_once(set_image, 0)
    
if __name__ == '__main__':
    MultiScreenApp().run()