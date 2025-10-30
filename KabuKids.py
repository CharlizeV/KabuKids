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

from kivy.uix.popup import Popup
from kivy.uix.checkbox import CheckBox
from kivy.uix.textinput import TextInput


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
    def __init__(self, date, start_time, end_time, **kwargs):
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
        from kivy.app import App
        App.get_running_app().root.current = "report"

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

        # Example meal data — replace with real data from DB, file, etc.
        meals = [
            {"date": "Oct 20, 2025", "start": "12:30 PM", "end": "1:15 PM"},
            {"date": "Oct 18, 2025", "start": "7:00 AM", "end": "7:45 AM"},
            {"date": "Oct 15, 2025", "start": "6:15 PM", "end": "7:00 PM"},
        ]

        for meal in meals:
            item = MealItem(
                date=meal["date"],
                start_time=meal["start"],
                end_time=meal["end"]
            )
            self.ids.meals_list.add_widget(item)

class CameraPage(Screen):
    pass

class ProfilePage(Screen):
    pass

class ReportPage(Screen):
    pass

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

class SuggestionsPage(Screen):
    pass

class WindowManager(ScreenManager):
    pass

# Load the kv file
kv = Builder.load_file("KabuKids.kv")

class MultiScreenApp(App):
    def build(self):
        return kv

if __name__ == '__main__':
    MultiScreenApp().run()