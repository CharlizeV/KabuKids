from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, ListProperty
from kivy.clock import Clock
from db import db
import os
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.metrics import dp
from kivy.app import App
from kivy.graphics import Color, Rectangle

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