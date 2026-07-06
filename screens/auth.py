from kivy.uix.screenmanager import Screen
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.app import App
from kivy.properties import StringProperty
from db import children_col
import uuid
from datetime import datetime
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import dp
from colors import DARK_COLOR

class SplashScreen(Screen):
    pass

class LoginPage(Screen):
    def show_message(self, message):
        Popup(title=" ", content=Label(text=message), size_hint=(0.6,0.3)).open()

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
    birthday_display_text = StringProperty("Select Birthday")

    def show_tag_warning(self, message):
        content = BoxLayout(orientation="vertical", padding=dp(18), spacing=dp(12))
        with content.canvas.before:
            Color(0.74, 0.78, 0.45, 1)
            content.bg = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(18),])
        content.bind(pos=lambda obj, pos: setattr(obj.bg, 'pos', pos), size=lambda obj, size: setattr(obj.bg, 'size', size))

        title = Label(
            text="Warning !",
            size_hint_y=None,
            height=dp(70),
            halign="left",
            valign="middle",
            color=(0.46, 0.57, 0.26, 1),
            font_size=dp(44),
            font_name="screens/fonts/Valekon.otf",
            text_size=(0, None),
        )
        title.bind(width=lambda inst, width: setattr(inst, "text_size", (width, None)))

        message_label = Label(
            text=message,
            halign="left",
            valign="middle",
            color=(0, 0, 0, 1),
            font_size=dp(24),
            text_size=(0, None),
        )
        message_label.bind(width=lambda inst, width: setattr(inst, "text_size", (width, None)))

        content.add_widget(title)
        content.add_widget(message_label)

        Popup(
            title="",
            content=content,
            size_hint=(0.76, 0.28),
            auto_dismiss=True,
            separator_height=0,
            background="",
            background_color=(0, 0, 0, 0),
        ).open()

    def remove_tag(self, tag_layout):
        parent = tag_layout.parent
        parent.remove_widget(tag_layout)

    def add_tag_prompt(self, section):
        content = BoxLayout(orientation='vertical', padding=dp(18), spacing=dp(14))
        with content.canvas.before:
            Color(0.74, 0.78, 0.45, 1)
            content.bg = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(18),])
        content.bind(pos=lambda obj, pos: setattr(obj.bg, 'pos', pos), size=lambda obj, size: setattr(obj.bg, 'size', size))

        title = Label(
            text="Add Tag",
            size_hint_y=None,
            height=dp(34),
            halign="left",
            valign="middle",
            color=(1, 1, 1, 1),
            font_size=dp(22),
            font_name="screens/fonts/Valekon.otf",
            text_size=(0, None),
        )
        title.bind(width=lambda inst, width: setattr(inst, "text_size", (width, None)))

        text_input = TextInput(
            hint_text="Enter tag...",
            font_size='20sp',
            multiline=False,
            size_hint_y=None,
            height=dp(60),
            background_normal="",
            background_active="",
            background_color=(0.97, 0.97, 0.97, 1),
            foreground_color=(0.12, 0.12, 0.12, 1),
            cursor_color=(0.12, 0.12, 0.12, 1),
            cursor_width=dp(2),
            padding=(dp(14), dp(18)),
        )
        btn_layout = BoxLayout(spacing=dp(14), size_hint_y=None, height=dp(56))
        btn_submit = Button(
            text="Add",
            background_normal="",
            background_color=(0.47, 0.60, 0.25, 1),
            color=(1, 1, 1, 1),
            font_name="screens/fonts/Valekon.otf",
            font_size=dp(22),
        )
        btn_cancel = Button(
            text="Cancel",
            background_normal="",
            background_color=(0.93, 0.84, 0.41, 1),
            color=(1, 1, 1, 1),
            font_name="screens/fonts/Valekon.otf",
            font_size=dp(22),
        )
        btn_layout.add_widget(btn_submit)
        btn_layout.add_widget(btn_cancel)
        content.add_widget(title)
        content.add_widget(text_input)
        content.add_widget(btn_layout)

        popup = Popup(
            title="",
            content=content,
            size_hint=(0.72, 0.34),
            auto_dismiss=False,
            separator_height=0,
            background="",
            background_color=(0, 0, 0, 0),
        )

        def add_tag(instance):
            tag_text = text_input.text.strip()
            if not tag_text:
                return

            if len(tag_text) > 32:
                self.show_tag_warning("Tags cannot exceed 32 characters")
                return

            self.add_tag_to_section(section, tag_text)
            popup.dismiss()

        def cancel(instance):
            popup.dismiss()

        btn_submit.bind(on_press=add_tag)
        btn_cancel.bind(on_press=cancel)
        popup.open()

    def add_tag_to_section(self, section, tag_text):
        tag_box = BoxLayout(
            size_hint=(None, None),
            height=dp(46),
            spacing=dp(8),
            padding=[dp(18), dp(8), dp(10), dp(8)],
        )

        # Background for tag box
        with tag_box.canvas.before:
            Color(1, 1, 1, 1)
            tag_box.rect = RoundedRectangle(pos=tag_box.pos, size=tag_box.size, radius=[dp(23),])

        tag_box.bind(
            pos=lambda obj, pos: setattr(obj.rect, 'pos', pos),
            size=lambda obj, size: setattr(obj.rect, 'size', size)
        )

        label = Label(
            text=tag_text,
            font_size=dp(20),
            color=(0, 0, 0, 1),
            halign='left',
            valign='center'
        )
        label.bind(size=label.setter('text_size'))

        close_btn = Button(
            text="×",
            size_hint=(None, None),
            size=(dp(34), dp(34)),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=(0.90, 0.35, 0.25, 1),
            font_size=dp(30)
        )
        close_btn.bind(on_press=lambda x: self.remove_tag(tag_box))

        tag_box.add_widget(label)
        tag_box.add_widget(close_btn)

        # size the pill to the text it contains, but keep it compact
        tag_box.width = max(dp(130), label.texture_size[0] + dp(70))
        label.bind(texture_size=lambda inst, size: setattr(tag_box, "width", max(dp(130), size[0] + dp(70))))

        if section == "likes":
            container = self.ids.likes_container
        elif section == "dislikes":
            container = self.ids.dislikes_container
        elif section == "goals":
            container = self.ids.goals_container
        else:
            return

        container.add_widget(tag_box)

    def open_birthday_picker(self):
        current = self.ids.birthday_input.text.strip() if "birthday_input" in self.ids else ""
        today = datetime.now()

        month_value, day_value, year_value = "01", "01", str(today.year)
        if current:
            parts = current.split("/")
            if len(parts) == 3:
                month_value, day_value, year_value = parts[0], parts[1], parts[2]

        content = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(14))
        with content.canvas.before:
            Color(0.74, 0.78, 0.45, 1)
            content.bg = RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(18),])
        content.bind(pos=lambda obj, pos: setattr(obj.bg, 'pos', pos), size=lambda obj, size: setattr(obj.bg, 'size', size))

        title = Label(
            text="Add Birthday",
            size_hint_y=None,
            height=dp(42),
            font_name="screens/fonts/Valekon.otf",
            font_size=dp(28),
            color=DARK_COLOR,
            halign="left",
            valign="middle",
            text_size=(0, None),
        )
        title.bind(width=lambda inst, width: setattr(inst, "text_size", (width, None)))

        row = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(14))

        month_spinner = Spinner(
            text="Month" if month_value == "01" else month_value,
            values=[f"{i:02d}" for i in range(1, 13)],
            size_hint_x=0.33,
            height=dp(56),
            background_normal="",
            background_color=(1, 1, 1, 1),
            color=(0.1, 0.1, 0.1, 1),
            font_size=dp(20),
        )
        day_spinner = Spinner(
            text="Day" if day_value == "01" else day_value,
            values=[f"{i:02d}" for i in range(1, 32)],
            size_hint_x=0.33,
            height=dp(56),
            background_normal="",
            background_color=(1, 1, 1, 1),
            color=(0.1, 0.1, 0.1, 1),
            font_size=dp(20),
        )
        year_spinner = Spinner(
            text="Year" if year_value == str(today.year) else year_value,
            values=[str(y) for y in range(today.year, 1900, -1)],
            size_hint_x=0.34,
            height=dp(56),
            background_normal="",
            background_color=(1, 1, 1, 1),
            color=(0.1, 0.1, 0.1, 1),
            font_size=dp(20),
        )

        row.add_widget(month_spinner)
        row.add_widget(day_spinner)
        row.add_widget(year_spinner)

        buttons = BoxLayout(size_hint_y=None, height=dp(54), spacing=dp(14))
        ok_button = Button(
            text="ADD",
            background_normal="",
            background_color=(0.47, 0.60, 0.25, 1),
            color=(1, 1, 1, 1),
            font_name="screens/fonts/Valekon.otf",
            font_size=dp(24),
        )
        cancel_button = Button(
            text="CANCEL",
            background_normal="",
            background_color=(0.93, 0.84, 0.41, 1),
            color=(1, 1, 1, 1),
            font_name="screens/fonts/Valekon.otf",
            font_size=dp(24),
        )
        buttons.add_widget(ok_button)
        buttons.add_widget(cancel_button)

        content.add_widget(title)
        content.add_widget(row)
        content.add_widget(buttons)

        popup = Popup(title="", content=content, size_hint=(0.7, 0.35))

        def set_date(instance):
            month_text = month_spinner.text if month_spinner.text != "Month" else "01"
            day_text = day_spinner.text if day_spinner.text != "Day" else "01"
            year_text = year_spinner.text if year_spinner.text != "Year" else str(today.year)
            birthday_text = f"{month_text}/{day_text}/{year_text}"
            if "birthday_input" in self.ids:
                self.ids.birthday_input.text = birthday_text
            self.birthday_display_text = birthday_text
            popup.dismiss()

        def dismiss_popup(instance):
            popup.dismiss()

        ok_button.bind(on_press=set_date)
        cancel_button.bind(on_press=dismiss_popup)
        popup.open()

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
            result = children_col.insert_one(child_doc)
            print(f"✅ Child profile saved with ID: {result.inserted_id}")

            self.show_message("Profile saved successfully!")
            self.manager.current = "login"

        except Exception as e:
            print("❌ Error saving profile:", e)
            self.show_message("Failed to save. Check your internet connection.")

    def on_pre_enter(self):
        # Clear form text inputs
        self.birthday_display_text = "Select Birthday"
        for fid in ("name_input", "birthday_input", "gender_input", "username_input", "password_input"):
            if fid in self.ids:
                self.ids[fid].text = ""

        if "profile_image" in self.ids:
            try:
                self.ids.profile_image.source = ""
            except Exception:
                pass

        # Remove tag BoxLayout widgets but keep non-Box children (e.g. the "+" button)
        for cid in ("likes_container", "dislikes_container", "goals_container"):
            if cid in self.ids:
                cont = self.ids[cid]
                for child in list(cont.children):
                    if isinstance(child, BoxLayout):
                        cont.remove_widget(child)

        # Optionally reset selected profile image path on the app
        try:
            app = App.get_running_app()
            app.profile_image_path = ""
        except Exception:
            pass