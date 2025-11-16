from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.checkbox import CheckBox
from services.models import CURRENT_MEAL, init_current_meal, clear_current_meal, SAMPLE_REPORTS
from db import meals_col
from kivy.app import App
from kivy.metrics import dp
from datetime import datetime
import uuid

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

class SessionPage(Screen):
    pass