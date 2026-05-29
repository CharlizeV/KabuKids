from kivy.logger import Logger
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.clock import Clock
import threading
import uuid
from widgets.meal_item import MealItem
from services.models import SAMPLE_REPORTS, fetch_reports_for_user
from db import meals_col, db
from kivy.metrics import dp
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

    def on_pre_enter(self, *args):
        app = App.get_running_app()
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

        report = SAMPLE_REPORTS.get(meal_id, {})
        for msg in report.get("transcript", []):
            role = msg["speaker"]
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

            speaker_text = ("Kabu" if role == "kabu" else "Child")
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
                color=LIGHT_COLOR,
                font_size='12sp',
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
            if role == "kabu":
                dislike_btn = ImageButton(
                    source="screens/icons/dislike.png",
                    size_hint_x=None,
                    size_hint_y=0.4,
                    width=dp(15),
                    height=dp(15),
                    allow_stretch=True,
                    keep_ratio=True
                )
                dislike_btn.bind(on_press=lambda inst, m=text: self.open_dislike_popup(m))
                # add image-button immediately after label (left side)
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