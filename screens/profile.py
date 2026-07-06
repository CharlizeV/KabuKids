from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, ListProperty
from kivy.clock import Clock
from db import children_col
import os
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.metrics import dp
from kivy.app import App
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.uix.spinner import Spinner
from datetime import datetime
from colors import DARK_COLOR

class ProfilePage(Screen):
    # values bound to KV
    first_name = StringProperty("User")
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
                self.first_name = (self.display_name.split()[0] if self.display_name.strip() else "User")
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
                self.first_name = (self.display_name.split()[0] if self.display_name.strip() else "User")
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
            self.first_name = "User"
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

class EditProfilePage(Screen):
    profile_data = StringProperty("")   # << add this
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

        popup = Popup(
            title="",
            content=content,
            size_hint=(0.7, 0.35),
            auto_dismiss=False,
            separator_height=0,
            background="",
            background_color=(0, 0, 0, 0),
        )

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

    def add_tag_to_section(self, section, tag_text):
        try:
            container = self.ids[f"{section}_container"]
        except Exception:
            return

        if not tag_text:
            return

        tag_box = BoxLayout(
            size_hint=(None, None),
            height=dp(46),
            spacing=dp(8),
            padding=[dp(18), dp(8), dp(10), dp(8)],
        )

        with tag_box.canvas.before:
            Color(1, 1, 1, 1)
            tag_box.rect = RoundedRectangle(pos=tag_box.pos, size=tag_box.size, radius=[dp(23),])

        tag_box.bind(
            pos=lambda obj, pos: setattr(obj.rect, 'pos', pos),
            size=lambda obj, size: setattr(obj.rect, 'size', size)
        )

        label = Label(
            text=str(tag_text),
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

        def update_tag_size(*args):
            max_width = max(dp(130), container.width - dp(20))
            inner_width = max_width - dp(70)
            label.text_size = (inner_width, None)
            label.texture_update()
            tag_box.width = min(max(dp(130), label.texture_size[0] + dp(70)), max_width)
            tag_box.height = max(dp(46), label.texture_size[1] + dp(16))

        update_tag_size()
        container.bind(width=lambda *args: update_tag_size())
        tag_box.bind(size=lambda *args: update_tag_size())
        container.add_widget(tag_box)

    def on_pre_enter(self, *args):
        app = App.get_running_app()
        user = getattr(app, "current_user", None)
        if not user:
            return

        try:
            if isinstance(user, dict):
                self.ids.name_input.text = user.get("name", "")
                self.ids.username_input.text = user.get("username", "")
                self.ids.password_input.text = ""
                self.ids.birthday_input.text = user.get("birthday", "")
                self.ids.gender_input.text = user.get("gender", "")
                self.birthday_display_text = user.get("birthday", "") or "Select Birthday"
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
                self.birthday_display_text = getattr(user, "birthday", "") or "Select Birthday"
                likes = getattr(user, "likes", []) or []
                dislikes = getattr(user, "dislikes", []) or []
                goals = getattr(user, "goals", []) or []
                existing_pic = getattr(user, "profile_picture", "") or ""
        except Exception as e:
            print("❌ EditProfilePage.on_pre_enter:", e)
            likes = dislikes = goals = []
            existing_pic = ""
            self.birthday_display_text = "Select Birthday"

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

        for section_name, tags in (("likes", likes), ("dislikes", dislikes), ("goals", goals)):
            container = self.ids.get(f"{section_name}_container")
            if not container:
                continue
            container.clear_widgets()
            for tag in tags:
                self.add_tag_to_section(section_name, tag)

    def remove_tag(self, widget):
        parent = widget.parent
        if parent:
            parent.remove_widget(widget)

    def _collect_tags(self, container_id):
        container = self.ids[container_id]
        tags = []
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
        tags.reverse()
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
            if password:
                update["password"] = password

            result = children_col.update_one({"_id": user_id}, {"$set": update})
            if result.matched_count:
                updated = children_col.find_one({"_id": user_id})
                app.current_user = updated

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