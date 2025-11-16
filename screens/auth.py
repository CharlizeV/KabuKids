from kivy.uix.screenmanager import Screen
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.app import App
from db import db, children_col
import uuid
from datetime import datetime
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.graphics import Color, Rectangle

class SplashScreen(Screen):
    pass

class LoginPage(Screen):
    def show_message(self, message):
        Popup(title="", content=Label(text=message), size_hint=(0.6,0.3)).open()

    def login(self):
        username = self.ids.username_input.text.strip() if 'username_input' in self.ids else ""
        password = self.ids.password_input.text.strip() if 'password_input' in self.ids else ""
        if not username or not password:
            self.show_message("Please enter both username and password.")
            return
        user = children_col.find_one({"username": username, "password": password})
        if user:
            app = App.get_running_app()
            app.current_user = user
            self.manager.current = "dashboard"
        else:
            self.show_message("Invalid username or password.")

    def on_pre_enter(self):
        # Clear login fields every time the page is shown
        if 'username_input' in self.ids:
            self.ids.username_input.text = ""
        if 'password_input' in self.ids:
            self.ids.password_input.text = ""

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

    def on_pre_enter(self):
        # Clear form text inputs
        for fid in ("name_input", "birthday_input", "gender_input", "username_input", "password_input"):
            if fid in self.ids:
                self.ids[fid].text = ""

        # Remove tag BoxLayout widgets but keep non-Box children (e.g. the "+" button)
        for cid in ("likes_container", "dislikes_container", "goals_container"):
            if cid in self.ids:
                cont = self.ids[cid]
                for child in list(cont.children):
                    if isinstance(child, BoxLayout):
                        cont.remove_widget(child)
                cont.height = cont.minimum_height if cont.children else 40

        # Optionally reset selected profile image path on the app
        try:
            app = App.get_running_app()
            app.profile_image_path = ""
        except Exception:
            pass