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
from kivy.properties import StringProperty
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


def fetch_reports_from_db(callback):
    """Fetch all meal reports from MongoDB (run in background thread)."""
    try:
        cursor = meals_col.find({})
        reports = {doc["_id"]: doc for doc in cursor}
        callback(reports)
    except Exception as e:
        print("❌ Error fetching from MongoDB:", e)
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
    pass

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

    def on_enter(self, *args):
        if not self._reports_loaded:
            self.ids.meals_list.clear_widgets()
            # self.ids.loading_label.text = "Loading reports..."  # ← REMOVED
            self.load_reports_from_db()
        else:
            self._populate_list()

    def load_reports_from_db(self):
        def on_reports_fetched(reports):
            global SAMPLE_REPORTS
            SAMPLE_REPORTS = reports
            self._reports_loaded = True
            Clock.schedule_once(lambda dt: self._populate_list(), 0)

        thread = threading.Thread(target=fetch_reports_from_db, args=(on_reports_fetched,))
        thread.daemon = True
        thread.start()

    def _populate_list(self):
        self.ids.meals_list.clear_widgets()
        # self.ids.loading_label.text = ""  # ← REMOVED

        if not SAMPLE_REPORTS:
            self.ids.meals_list.add_widget(Label(text="No reports found.", size_hint_y=None, height=dp(40)))
            return

        for meal_id, report in SAMPLE_REPORTS.items():
            item = MealItem(
                meal_id=meal_id,
                date=report["date"],
                start_time=report["start_time"],
                end_time=report["end_time"]
            )
            self.ids.meals_list.add_widget(item)


class ProfilePage(Screen):
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
            speaker_label = Label(
                text="Kabu:" if role == "Kabu" else "Name:",
                font_size='16sp',
                bold=True,
                color=SECONDARY_COLOR,
                halign='left',
                valign='top',
                size_hint_x=1,
                size_hint_y=None,
                height=dp(20)
            )
            speaker_label.bind(
                width=lambda inst, w: setattr(inst, 'text_size', (w - dp(20), None)),
                texture_size=lambda inst, size: setattr(inst, 'height', size[1])
            )

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

            msg_box.add_widget(speaker_label)
            msg_box.add_widget(emotion_label)
            msg_box.add_widget(msg_label)

            # Dislike button for Kabu only
            if role == "Kabu":
                btn_row = BoxLayout(size_hint_y=None, size_hint_x=1, height=dp(30))
                dislike_btn = Button(
                    size_hint_x=None,
                    width=dp(30),
                    background_normal='',
                    background_color=(1, 0, 0, 1),
                    on_press=self.open_dislike_popup
                )
                btn_row.add_widget(dislike_btn)
                btn_row.add_widget(BoxLayout())  # spacer
                msg_box.add_widget(btn_row)

            # Auto height
            msg_box.bind(minimum_height=msg_box.setter('height'))
            content.add_widget(msg_box)

    def open_dislike_popup(self, instance):
        content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))

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
        for opt in options:
            row = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(10))
            cb = CheckBox(size_hint_x=None, width=dp(30), height=dp(30))
            lbl = Label(text=opt, font_size='14sp', halign='left', size_hint_x=1, height=dp(30))
            lbl.bind(width=lambda w, width: setattr(lbl, 'text_size', (width - dp(40), None)))
            row.add_widget(cb)
            row.add_widget(lbl)
            content.add_widget(row)

        other = TextInput(hint_text="Specify other...", size_hint_y=None, height=dp(40))
        content.add_widget(other)

        submit = Button(text="Submit", size_hint_y=None, height=dp(45), on_press=lambda x: self.close_popup(popup))
        content.add_widget(submit)

        popup = Popup(title='', content=content, size_hint=(0.8, 0.6))
        popup.open()
        self.popup = popup

    def close_popup(self, popup):
        popup.dismiss()

class PortionSizeBeforePage(Screen):
    pass

class PortionSizeAfterPage(Screen):
    pass

class InputIngredientsBMPage(Screen):
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
        if section == "ingredients":
            container = self.ids.ingredients_container
        else:
            return

        # Insert before the "+" button (which is the last child)
        container.add_widget(tag_box, len(container.children) - 1)
        container.height = container.minimum_height

class InputIngredientsAMPage(Screen):  # AM = After Meal
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Placeholder food list (replace later with actual data from before-meal input)
        self.placeholder_foods = ["chicken", "rice", "carrots", "apple", "bread"]

    def on_enter(self):
        # Optional: populate checkboxes dynamically when screen is entered
        container = self.ids.food_checkboxes
        container.clear_widgets()

        for food in self.placeholder_foods:
            row = BoxLayout(size_hint_y=None, height=40, padding=[10, 5])
            cb = CheckBox(size_hint_x=None, width=30, group=None)  # Not radio — independent
            label = Label(text=food.capitalize(), color=[0, 0, 0, 1], halign='left', valign='middle')
            label.bind(size=label.setter('text_size'))
            row.add_widget(cb)
            row.add_widget(label)
            container.add_widget(row)

        # Ensure container resizes properly
        container.height = container.minimum_height

class EditProfilePage(Screen):
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
        if selection:
            self.profile_image_path = selection[0]
            make_screen = self.root.get_screen('make_account')
            img_widget = make_screen.ids.profile_image
            img_widget.source = self.profile_image_path
            img_widget.reload()
    
if __name__ == '__main__':
    MultiScreenApp().run()