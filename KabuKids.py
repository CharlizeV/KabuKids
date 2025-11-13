import kivy
kivy.require('2.0.0')
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle
from kivy.properties import StringProperty, ListProperty, ObjectProperty
from kivy.uix.image import AsyncImage  # or use Image if local paths
from kivy.clock import Clock

from kivy.uix.popup import Popup
from kivy.uix.checkbox import CheckBox
from kivy.uix.textinput import TextInput

# Sample Reports Database (replace with real DB later)
SAMPLE_REPORTS = {
    "R001": {
        "report_id": "R001",
        "user_id": "U123",
        "user_name": "Liam Chen",
        "user_age": 4,
        "date": "October 20, 2025",
        "start_time": "12:30 PM",
        "end_time": "1:15 PM",
        "transcript": "Child said: 'I like green trees!' while eating broccoli. Refused chicken again.",
        "conversation_suggestions": [
            "What color was your favorite food today?",
            "Can you show me how you used your spoon?"
        ],
        "ingredient_suggestions": [
            "Broccoli - Rich in vitamins A, C, and K; supports eye and immune health.",
            "Sweet Potato - Soft, sweet, and high in beta-carotene."
        ],
        "food_before_meal": ["Broccoli", "Grilled Chicken", "Brown Rice", "Sweet Potato"],
        "food_not_finished": ["Grilled Chicken"],
        "portion_before_image": "assets/portion_before_1.jpg",
        "portion_after_image": "assets/portion_after_1.jpg"
    },
    "R002": {
        "report_id": "R002",
        "user_id": "U123",
        "user_name": "Liam Chen",
        "user_age": 4,
        "date": "October 18, 2025",
        "start_time": "7:00 AM",
        "end_time": "7:45 AM",
        "transcript": "Child poured milk himself! Said 'I big boy now!'",
        "conversation_suggestions": [
            "What did you do all by yourself this morning?",
            "What food gave you energy to play today?"
        ],
        "ingredient_suggestions": [
            "Oatmeal - Great source of fiber and sustained energy.",
            "Banana - Easy to eat, rich in potassium."
        ],
        "food_before_meal": ["Oatmeal", "Banana Slices", "Milk", "Toast"],
        "food_not_finished": ["Toast"],
        "portion_before_image": "assets/portion_before_2.jpg",
        "portion_after_image": "assets/portion_after_2.jpg"
    },
    "R003": {
        "report_id": "R003",
        "user_id": "U123",
        "user_name": "Liam Chen",
        "user_age": 4,
        "date": "October 15, 2025",
        "start_time": "6:15 PM",
        "end_time": "7:00 PM",
        "transcript": "Child shared food with doll: 'You eat too, dolly!'",
        "conversation_suggestions": [
            "Who did you share your food with today?",
            "What made dinner fun tonight?"
        ],
        "ingredient_suggestions": [
            "Carrots - Crunchy and great for vision.",
            "Cheese Cubes - Good source of calcium and protein."
        ],
        "food_before_meal": ["Carrot Sticks", "Cheese Cubes", "Apple Slices", "Yogurt"],
        "food_not_finished": [],
        "portion_before_image": "assets/portion_before_3.jpg",
        "portion_after_image": "assets/portion_after_3.jpg"
    }
}

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
    def __init__(self, report_id, date, start_time, end_time, **kwargs):
        self.report_id = report_id  # ← Store report ID
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
        app.selected_report_id = self.report_id  # ← Save which report was clicked
        app.root.current = "report"

# Define all screen classes
class SplashScreen(Screen):
    pass

class LoginPage(Screen):
    pass

class MakeAccountPage(Screen):
    pass

class DashboardPage(Screen):
    def on_enter(self, *args):
        # Clear previous items (in case screen is revisited)
        self.ids.meals_list.clear_widgets()

        # Use real reports from SAMPLE_REPORTS
        for report_id, report in SAMPLE_REPORTS.items():
            item = MealItem(
                report_id=report_id,
                date=report["date"],
                start_time=report["start_time"],
                end_time=report["end_time"]
            )
            self.ids.meals_list.add_widget(item)

class PictureMealPage(Screen):
    pass

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
    user_name = StringProperty("")
    user_age = StringProperty("")
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
        report_id = app.selected_report_id

        if not report_id or report_id not in SAMPLE_REPORTS:
            # Fallback or error handling
            self.user_name = "Unknown"
            self.user_age = ""
            self.date = "N/A"
            self.summary_text = "Report not found."
            return

        data = SAMPLE_REPORTS[report_id]

        # User info
        self.user_name = data["user_name"]
        self.user_age = f"{data['user_age']} years old"

        # Date & time
        self.date = data["date"]
        self.time_range = f"{data['start_time']} – {data['end_time']}"

        # Summary
        self.summary_text = (
            f"During the meal, the child showed interest in vegetables but refused protein sources. "
            f"They engaged positively with caregivers and used utensils independently. "
            f"Foods offered: {', '.join(data['food_before_meal'])}. "
            f"Foods not finished: {', '.join(data['food_not_finished']) if data['food_not_finished'] else 'None'}."
        )

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
    def open_like_popup(self):
        content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))

        # Title - properly aligned
        title = Label(
            text="What do you like about this response?",
            font_size='16sp',
            halign='left',
            valign='middle',
            size_hint_y=None,
            height=dp(40),
            text_size=(content.width - dp(40), None)  # Account for padding
        )
        content.add_widget(title)

        # Options: Checkbox + Text properly aligned
        options = [
            "Promotes healthy eating",
            "Effective",
            "Encourage positive communication",
            "Other"
        ]

        for opt in options:
            row = BoxLayout(
                size_hint_y=None, 
                height=dp(30), 
                spacing=dp(10),
                padding=[0, 0, 0, 0]
            )
            cb = CheckBox(
                size_hint_x=None, 
                width=dp(30),
                size_hint_y=None,
                height=dp(30)
            )
            lbl = Label(
                text=opt,
                font_size='14sp',
                halign='left',
                valign='middle',
                size_hint_x=1,
                size_hint_y=None,
                height=dp(30),
                text_size=(None, None)  # Allow text to determine size
            )
            row.add_widget(cb)
            row.add_widget(lbl)
            content.add_widget(row)

        # Other input field
        other_input = TextInput(
            hint_text="Specify other...",
            font_size='14sp',
            size_hint_y=None,
            height=dp(40),
            multiline=False,
            background_color=[1, 1, 1, 1],
            foreground_color=[0, 0, 0, 1]
        )
        content.add_widget(other_input)

        # Submit button
        submit_btn = Button(
            text="Submit",
            size_hint_y=None,
            height=dp(45),
            background_color=[0.7, 0.7, 0.7, 1],
            color=[0, 0, 0, 1],
            on_press=lambda x: self.close_popup(popup)
        )
        content.add_widget(submit_btn)

        popup = Popup(
            title='',
            content=content,
            size_hint=(0.8, 0.6),
            auto_dismiss=True,
            background_color=[0, 0, 0, 1]
        )
        
        # Bind after popup creation to get proper sizing
        def on_open(instance):
            title.text_size = (content.width - dp(40), None)
            for child in content.children:
                if isinstance(child, BoxLayout) and len(child.children) == 2:
                    lbl = child.children[0]  # Label is first due to reverse order
                    if isinstance(lbl, Label):
                        lbl.text_size = (child.width - dp(40), None)
        
        popup.bind(on_open=on_open)
        popup.bind(on_dismiss=lambda x: setattr(self, 'popup', None))
        popup.open()
        self.popup = popup

    def open_dislike_popup(self):
        content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))

        title = Label(
            text="What do you dislike about this response?",
            font_size='16sp',
            halign='left',
            valign='middle',
            size_hint_y=None,
            height=dp(40),
            text_size=(content.width - dp(40), None)
        )
        content.add_widget(title)

        options = [
            "Ineffective",
            "Distracting",
            "Doesn't relate to interest",
            "Other"
        ]

        for opt in options:
            row = BoxLayout(
                size_hint_y=None, 
                height=dp(30), 
                spacing=dp(10),
                padding=[0, 0, 0, 0]
            )
            cb = CheckBox(
                size_hint_x=None, 
                width=dp(30),
                size_hint_y=None,
                height=dp(30)
            )
            lbl = Label(
                text=opt,
                font_size='14sp',
                halign='left',
                valign='middle',
                size_hint_x=1,
                size_hint_y=None,
                height=dp(30),
                text_size=(None, None)
            )
            row.add_widget(cb)
            row.add_widget(lbl)
            content.add_widget(row)

        other_input = TextInput(
            hint_text="Specify other...",
            font_size='14sp',
            size_hint_y=None,
            height=dp(40),
            multiline=False,
            background_color=[1, 1, 1, 1],
            foreground_color=[0, 0, 0, 1]
        )
        content.add_widget(other_input)

        submit_btn = Button(
            text="Submit",
            size_hint_y=None,
            height=dp(45),
            background_color=[0.7, 0.7, 0.7, 1],
            color=[0, 0, 0, 1],
            on_press=lambda x: self.close_popup(popup)
        )
        content.add_widget(submit_btn)

        popup = Popup(
            title='',
            content=content,
            size_hint=(0.8, 0.6),
            auto_dismiss=True,
            background_color=[0, 0, 0, 1]
        )
        
        def on_open(instance):
            title.text_size = (content.width - dp(40), None)
            for child in content.children:
                if isinstance(child, BoxLayout) and len(child.children) == 2:
                    lbl = child.children[0]
                    if isinstance(lbl, Label):
                        lbl.text_size = (child.width - dp(40), None)
        
        popup.bind(on_open=on_open)
        popup.bind(on_dismiss=lambda x: setattr(self, 'popup', None))
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
    def build(self):
        self.selected_report_id = None  # ← Add this
        return kv
    
if __name__ == '__main__':
    MultiScreenApp().run()