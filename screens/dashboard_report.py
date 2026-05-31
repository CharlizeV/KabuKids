from kivy.logger import Logger
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.clock import Clock
import threading
import uuid
from widgets.meal_item import MealItem
from services.models import SAMPLE_REPORTS, fetch_reports_for_user
from db import meals_col, db
from kivy.metrics import dp, sp
from datetime import datetime

# Kivy properties and app/widget classes used in this file
from kivy.properties import StringProperty
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from bson.objectid import ObjectId
from mainsession import mongodb

# Fallback color constants if not defined elsewhere in the project
from colors import DARK_COLOR, LIGHT_COLOR, ACCENT_COLOR, PRIMARY_COLOR, SECONDARY_COLOR, SUPER_LIGHT

from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
from kivy.uix.widget import Widget

# simple tappable image widget
class ImageButton(ButtonBehavior, Image):
    pass

class DashboardPage(Screen):
    _reports_loaded = False
    user_name = StringProperty("User Name")   # <-- new property
    first_name = StringProperty("User")

    def _derive_first_name(self, value):
        if not value:
            return "User"
        first = str(value).strip().split()
        return first[0] if first else "User"

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
            self.first_name = self._derive_first_name(name)
        else:
            self.user_name = "User"
            self.first_name = "User"

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
            #----DEBUG CHECKINGGG
            print(f"[dashboard_report] on_reports_fetched called, reports_count={len(reports)}")

            # Normalize reports -> ensure string ids and normalized fields
            normalized = {}
            # support reports as dict or list
            items = reports.items() if isinstance(reports, dict) else enumerate(reports)
            for _, r in items:
                try:
                    rep = dict(r) if isinstance(r, dict) else dict(r)
                except Exception:
                    rep = {}
                # normalize id to string
                raw_id = rep.get("_id") or rep.get("meal_id") or rep.get("id")
                rep["_id"] = str(raw_id) if raw_id is not None else str(rep.get("meal_id", "")) or str(uuid.uuid4())

                # normalize/attach user id (string)
                raw_user = rep.get("user_id") or rep.get("userId") or rep.get("user") or rep.get("owner")
                rep["user_id"] = str(raw_user) if raw_user is not None else ""

                # ensure transcript exists
                rep["transcript"] = rep.get("transcript") or []

                # normalize conversation suggestions to list
                conv = rep.get("conversation_suggestions") or rep.get("conversationSuggestions") or rep.get("recommendations") or []
                if isinstance(conv, str):
                    conv = [conv]
                rep["conversation_suggestions"] = list(conv)

                # normalize ingredient / disliked suggestions to list of strings
                raw_disliked = rep.get("ingredient_suggestions") or rep.get("ingredientSuggestions") or rep.get("disliked_foods") or []
                ingredient_list = []
                if isinstance(raw_disliked, dict):
                    for k, v in raw_disliked.items():
                        if isinstance(v, (list, tuple)):
                            ingredient_list.append(f"{k}: {', '.join(map(str, v))}")
                        else:
                            ingredient_list.append(f"{k}: {v}")
                elif isinstance(raw_disliked, (list, tuple)):
                    ingredient_list = [str(x) for x in raw_disliked]
                elif raw_disliked:
                    ingredient_list = [str(raw_disliked)]
                rep["ingredient_suggestions"] = ingredient_list

                # ensure food arrays exist
                rep["food_before_meal"] = rep.get("food_before_meal") or []
                rep["food_after_meal"] = rep.get("food_after_meal") or []
                normalized[rep["_id"]] = rep

            # FILTER: keep only reports that belong to this user_id
            try:
                user_id_str = str(user_id) if user_id is not None else ""
                filtered = {k: v for k, v in normalized.items() if (v.get("user_id", "") == user_id_str)}
                print(f"[dashboard_report] fetched {len(normalized)} reports, {len(filtered)} match user_id={user_id_str}")
            except Exception:
                filtered = normalized

            SAMPLE_REPORTS = filtered
            self._reports_loaded = True
            Clock.schedule_once(lambda dt: self._populate_list(), 0)

        thread = threading.Thread(target=fetch_reports_for_user, args=(user_id, on_reports_fetched))
        thread.daemon = True
        thread.start()

    def _populate_list(self):
        self.ids.meals_list.clear_widgets()
        # self.ids.loading_label.text = ""  # ← REMOVED

        if not SAMPLE_REPORTS:
            self.ids.meals_list.add_widget(Label(text="No reports found.", color=DARK_COLOR, size_hint_y=None, height=dp(40)))
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


class ReportDashboardPage(Screen):
    _reports_loaded = False
    user_name = StringProperty("User Name")
    first_name = StringProperty("User")

    def _derive_first_name(self, value):
        if not value:
            return "User"
        first = str(value).strip().split()
        return first[0] if first else "User"

    def on_enter(self, *args):
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
            self.first_name = self._derive_first_name(name)
        else:
            self.user_name = "User"
            self.first_name = "User"

        self.ids.meals_list.clear_widgets()
        self._reports_loaded = False
        self.load_reports_from_db()

    def load_reports_from_db(self):
        DashboardPage.load_reports_from_db(self)

    def _populate_list(self):
        DashboardPage._populate_list(self)

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
    first_name = StringProperty("User")

    def _derive_first_name(self, value):
        if not value:
            return "User"
        first = str(value).strip().split()
        return first[0] if first else "User"

    def on_pre_enter(self, *args):
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
            self.first_name = self._derive_first_name(name)
        else:
            self.first_name = "User"

        try:
            meal_id = app.selected_meal_id
            Logger.info(f"ReportPage: on_pre_enter meal_id={meal_id}")
        except Exception as e:
            Logger.info(f"ReportPage: on_pre_enter error getting meal_id: {e}")
            meal_id = None
        if not meal_id or meal_id not in SAMPLE_REPORTS:
            # Fallback or error handling
            self.date = "N/A"
            self.summary_text = "Report not found."
            return
        
        data = mongodb.find_meal(meal_id)
        Logger.info(data)
        Logger.info("Here")
        Logger.info("Here")
        Logger.info("Here")
        Logger.info("Here")
        Logger.info("Here")
        Logger.info("Here")
        Logger.info("Here")
        Logger.info("Here")
        Logger.info("Here")
        Logger.info("Here")
        Logger.info("Here")
        Logger.info("Here")
        Logger.info("Here")

        # Date & time
        self.date = data["date"]
        self.time_range = f"{data['start_time']} – {data['end_time']}"

        # Summary
        self.summary_text = data.get("summary", "No summary available.")

        # Food lists (with real newlines)
        self.food_before_text = "\n".join([f"• {food}" for food in data["food_before_meal"]])
        self.food_not_finished_text = "\n".join([f"• {food}" for food in data["food_not_finished"]]) if data["food_not_finished"] else "• None"

        # # Images
        # self.portion_before_source = data["portion_before_image"]
        # self.portion_after_source = data["portion_after_image"]

        # Suggestions (with real newlines)
        self.formatted_ingredient_suggestions = "\n".join([f"• {s}" for s in data["ingredient_suggestions"]])
        self.formatted_conversation_suggestions = "\n".join([f'• "{s}"' for s in data["conversation_suggestions"]])
class TranscriptPage(Screen):
    # expose header text used by transcript.kv
    meal_date_text = StringProperty("")
    meal_time_text = StringProperty("")
    first_name = StringProperty("User")

    def _derive_first_name(self, value):
        if not value:
            return "User"
        first = str(value).strip().split()
        return first[0] if first else "User"

    def _format_message_time(self, value):
        if not value:
            return ""
        if isinstance(value, datetime):
            return f"({value.strftime('%I:%M%p').lstrip('0')})"

        text = str(value).strip()
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%I:%M %p",
            "%I:%M%p",
        ):
            try:
                dt = datetime.strptime(text, fmt)
                return f"({dt.strftime('%I:%M%p').lstrip('0')})"
            except Exception:
                continue

        # If the value already looks like a time, clean common ISO leftovers.
        if "T" in text:
            text = text.split("T", 1)[-1]
        text = text.replace("+00:00", "").replace("Z", "")
        return f"({text})" if text else ""

    def _plain_emotion(self, emotion):
        if emotion is None:
            return ""
        text = str(emotion).strip()
        text = text.strip("[]").strip("'").strip('"')
        return text

    def _get_user_photo_source(self):
        app = App.get_running_app()
        current_user = getattr(app, "current_user", None)

        source = ""
        if current_user:
            try:
                if isinstance(current_user, dict):
                    source = current_user.get("profile_picture", "") or ""
                else:
                    source = getattr(current_user, "profile_picture", "") or ""
            except Exception:
                source = ""

        if not source:
            source = getattr(app, "profile_image_path", "") or ""

        return source

    def _make_avatar(self, source, bg_rgba):
        avatar = BoxLayout(size_hint=(None, None), size=(dp(56), dp(56)))
        with avatar.canvas.before:
            from kivy.graphics import Color, Ellipse
            Color(rgba=bg_rgba)
            avatar._ellipse = Ellipse(pos=avatar.pos, size=avatar.size)

        def _sync_avatar(*_args):
            avatar._ellipse.pos = avatar.pos
            avatar._ellipse.size = avatar.size

        avatar.bind(pos=_sync_avatar, size=_sync_avatar)
        image_source = source or self._get_user_photo_source() or "screens/icons/user.png"
        avatar.add_widget(Image(source=image_source, allow_stretch=True, keep_ratio=True))
        return avatar

    def _make_message_row(self, role, text, emotion, time_text):
        role_text = str(role).strip().lower()
        is_kabu = role_text == "kabu" or role_text == "assistant" or role_text == "bot"

        row = BoxLayout(size_hint_y=None, height=dp(92), spacing=dp(12), padding=[0, dp(2), 0, dp(2)])

        spacer_left = Widget(size_hint_x=1)
        spacer_right = Widget(size_hint_x=1)

        bubble = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            width=dp(520),
            padding=[dp(14), dp(10), dp(14), dp(10)],
            spacing=dp(2),
        )
        bubble_bg = SECONDARY_COLOR if not is_kabu else (0.98, 0.95, 0.86, 1)
        with bubble.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(rgba=bubble_bg)
            bubble._bg = RoundedRectangle(pos=bubble.pos, size=bubble.size, radius=[dp(16)] * 4)

        def _sync_bubble(*_args):
            bubble._bg.pos = bubble.pos
            bubble._bg.size = bubble.size

        bubble.bind(pos=_sync_bubble, size=_sync_bubble)

        header = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(4))
        name = "Kabu" if is_kabu else self.first_name or "User"
        name_label = Label(
            text=name,
            font_name="screens/fonts/Valekon.otf",
            font_size=sp(28),
            bold=True,
            color=DARK_COLOR,
            size_hint_x=None,
            halign='left',
            valign='middle',
        )
        name_label.bind(texture_size=lambda inst, ts: setattr(inst, 'width', inst.texture_size[0] + dp(4)))

        time_label = Label(
            text=time_text,
            font_size=sp(18),
            color=DARK_COLOR,
            size_hint_x=None,
            halign='left',
            valign='middle',
        )
        time_label.bind(texture_size=lambda inst, ts: setattr(inst, 'width', inst.texture_size[0] + dp(4)))

        header.add_widget(name_label)
        if time_text:
            header.add_widget(time_label)
        if is_kabu:
            # put the icon inside a fixed-size container to ensure the visual size is constrained
            icon_container = BoxLayout(size_hint=(None, None), size=(dp(25), dp(25)), pos_hint={'center_y': 0.50})
            dislike_btn = ImageButton(
                source="screens/icons/dislike.png",
                size_hint=(1, 1),
                allow_stretch=True,
                keep_ratio=False,
            )
            dislike_btn.bind(on_press=lambda inst, m=text: self.open_dislike_popup(m))
            icon_container.add_widget(dislike_btn)
            header.add_widget(icon_container)
            # force texture reload so Kivy updates the scaled texture for the smaller widget size
            try:
                dislike_btn.reload()
            except Exception:
                pass
        header.add_widget(Widget())

        emotion_text = self._plain_emotion(emotion)
        emotion_label = Label(
            text=emotion_text,
            font_size=sp(16),
            color=DARK_COLOR,
            size_hint_y=None,
            size_hint_x=1,
            height=dp(20),
            halign='left',
            valign='middle',
        )
        # keep emotion left-aligned by setting its text_size to its width
        emotion_label.bind(
            width=lambda inst, w: setattr(inst, 'text_size', (w - dp(6), None)),
            texture_size=lambda inst, ts: setattr(inst, 'height', max(dp(20), inst.texture_size[1]))
        )

        message_label = Label(
            text=text,
            font_size=sp(20),
            color=DARK_COLOR,
            halign='left',
            valign='top',
            size_hint_y=None,
        )
        message_label.bind(
            width=lambda inst, w: setattr(inst, 'text_size', (w - dp(6), None)),
            texture_size=lambda inst, size: setattr(inst, 'height', size[1]),
        )

        bubble.add_widget(header)
        if emotion_text:
            bubble.add_widget(emotion_label)
        bubble.add_widget(message_label)
        bubble.bind(minimum_height=bubble.setter('height'))

        if is_kabu:
            row.add_widget(self._make_avatar('screens/icons/logo.PNG', (0.98, 0.93, 0.55, 1)))
            row.add_widget(bubble)
            row.add_widget(spacer_right)
        else:
            row.add_widget(spacer_left)
            row.add_widget(bubble)
            row.add_widget(self._make_avatar(self._get_user_photo_source(), (0.73, 0.79, 0.45, 1)))

        row.bind(minimum_height=row.setter('height'))
        return row

    def on_pre_enter(self, *args):
        content = self.ids.transcript_content
        content.clear_widgets()

        app = App.get_running_app()
        meal_id = getattr(app, 'selected_meal_id', None)

        current_user = getattr(app, "current_user", None)
        if current_user:
            try:
                if isinstance(current_user, dict):
                    name = current_user.get("name") or current_user.get("username") or "User"
                else:
                    name = getattr(current_user, "name", None) or getattr(current_user, "username", "User")
            except Exception:
                name = "User"
            self.first_name = self._derive_first_name(name)
        else:
            self.first_name = "User"

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

        report = SAMPLE_REPORTS.get(meal_id, {})
        # set header properties so KV can display the meal's date/time
        self.meal_date_text = report.get("date", "")
        start_time = report.get("start_time", "")
        end_time = report.get("end_time", "")
        if start_time and end_time:
            self.meal_time_text = f"{start_time} - {end_time}"
        else:
            self.meal_time_text = start_time or end_time or ""
        for msg in report.get("transcript", []):
            role = msg.get("speaker", "child")
            text = msg.get("text", "")
            emotion = msg.get("emotion", "")

            time_val = None
            for time_key in ("time", "timestamp", "time_str", "created_at"):
                if msg.get(time_key):
                    time_val = msg.get(time_key)
                    break

            time_text = self._format_message_time(time_val)
            content.add_widget(self._make_message_row(role, text, emotion, time_text))

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
            color=DARK_COLOR,
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
            lbl.color = DARK_COLOR
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
                Popup(title="", content=Label(text="Please select or enter a reason.", color=DARK_COLOR, halign='center'), size_hint=(0.6,0.3)).open()
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
            Popup(title="", content=Label(text="Thanks for the feedback.", color=DARK_COLOR), size_hint=(0.6,0.3)).open()

        submit = Button(text="Submit", size_hint_y=None, height=dp(44))
        popup = Popup(title='', content=content, size_hint=(0.86, 0.62))
        submit.bind(on_press=lambda btn: on_submit(btn, popup))
        content.add_widget(submit)
        popup.open()
        self.popup = popup