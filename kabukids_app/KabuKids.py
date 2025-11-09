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

from kivy.network.urlrequest import UrlRequest
import json

from datetime import datetime


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
    def __init__(self, **kwargs):
        date = kwargs.pop('date', 'No Date')
        start_time = kwargs.pop('start_time', 'N/A')
        end_time = kwargs.pop('end_time', 'N/A')
        transcript = kwargs.pop('transcript', 'No transcript')
        
        super().__init__(**kwargs)
        
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(80)
        self.spacing = dp(10)
        
        with self.canvas.before:
            Color(0.95, 0.95, 0.95, 1)
            self.rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(8)]
            )
        self.bind(pos=self._update_rect, size=self._update_rect)

        # This layout holds all the text
        info_layout = BoxLayout(orientation='vertical', padding=[dp(10), dp(5)], spacing=dp(5))
        
        # --- TRANSCRIPT LABEL ---
        transcript_label = Label(
            text=transcript,
            font_size='16sp',
            color=(0.1, 0.1, 0.1, 1), 
            halign='left',
            valign='top',
            size_hint_y=None,
            height=dp(25)
        )
        # This line fixes the text wrapping:
        transcript_label.bind(width=lambda *x: transcript_label.setter('text_size')(transcript_label, (transcript_label.width, None)))
        info_layout.add_widget(transcript_label)
        
        # --- DATE LABEL ---
        date_label = Label(
            text=date,
            font_size='14sp',
            color=(0.2, 0.2, 0.2, 1),
            size_hint_y=None,
            height=dp(20),
            halign='left'
        )
        # This line fixes the text wrapping:
        date_label.bind(width=lambda *x: date_label.setter('text_size')(date_label, (date_label.width, None)))
        info_layout.add_widget(date_label)
        
        # --- TIME LABEL ---
        time_label = Label(
            text=f"Start: {start_time} | End: {end_time}",
            font_size='12sp',
            color=(0.4, 0.4, 0.4, 1),
            size_hint_y=None,
            height=dp(16),
            halign='left'
        )
        # This line fixes the text wrapping:
        time_label.bind(width=lambda *x: time_label.setter('text_size')(time_label, (time_label.width, None)))
        info_layout.add_widget(time_label)
        
        self.add_widget(info_layout)

        # The "More" button
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
        App.get_running_app().root.current = "report"

# Define all screen classes
class SplashScreen(Screen):
    pass

class LoginPage(Screen):
    def do_login(self):
        try:
            username = self.ids.username_input.text
            password = self.ids.password_input.text
        except KeyError:
            print("KIVY ERROR: Make sure your TextInputs in login.kv have id: username_input and id: password_input")
            return

        print(f"Attempting login for user: {username}") 

        api_url = "http://127.0.0.1:3000/login" 
        headers = {'Content-type': 'application/json'}
        body = json.dumps({"username": username, "password": password})
        
        UrlRequest(
            api_url,
            req_body=body,
            req_headers=headers,
            on_success=self.on_login_success,
            on_failure=self.on_login_failure,
            on_error=self.on_login_error
        )

    def on_login_success(self, request, result):
        print("--- LOGIN SUCCESS ---")
        print("Server sent back:", result) 
        
        # Store user data globally in the app
        App.get_running_app().user_data = result 
        
        # Go to the dashboard
        self.manager.current = "dashboard"

    def on_login_failure(self, request, result):
        print("\n--- LOGIN FAILED (on_login_failure) ---")
        print("The server rejected the login.")
        print("Status Code:", request.resp_status)
        print("Server Response:", result) # This will show "Invalid username or password"

    def on_login_error(self, request, error):
        print("\n--- LOGIN ERROR (on_login_error) ---")
        print("Could not connect to the server. Is it running?")
        print("Error:", error)

class MakeAccountPage(Screen):
    pass

class DashboardPage(Screen):
    def on_enter(self, *args):
        # Clear previous items
        self.ids.meals_list.clear_widgets()

        # Get the user data that was stored during login
        user_data = App.get_running_app().user_data
        
        # Check if login was successful. If not, go back to login screen.
        if not user_data:
            print("No user data found, returning to login.")
            self.manager.current = "login"
            return 
        
        # Get the MongoDB user ID
        user_id = user_data.get('_id') 

        if not user_id:
            print("User data exists but has no _id")
            self.manager.current = "login" 
            return

        # Request this user's meals from the API
        print(f"Fetching meals for user_id: {user_id}")
        api_url = f"http://127.0.0.1:3000/meals/{user_id}"
        UrlRequest(
            api_url,
            on_success=self.on_meals_loaded,
            on_failure=lambda req, res: print("Failed to load meals:", res),
            on_error=lambda req, err: print("Error loading meals:", err)
        )

    def on_meals_loaded(self, request, meals_data):
        print("Successfully loaded meals data:", meals_data)
        
        if not meals_data:
            print("No meals found for this user.")
            return
            
        for meal in meals_data:
            # Parse the date strings from MongoDB
            date_str = self.format_date(meal.get("date", ""))
            start_str = self.format_time(meal.get("startTime", ""))
            end_str = self.format_time(meal.get("endTime", ""))
            
            # Get the transcript from the meal data
            transcript_str = meal.get("transcript", "No transcript")
            
            # Create the MealItem widget
            item = MealItem(
                date=date_str,
                start_time=start_str,
                end_time=end_str,
                transcript=transcript_str
            )
            # Add the widget to the list in your .kv file
            self.ids.meals_list.add_widget(item)
            
    def format_date(self, date_string):
        """ Helper function to format MongoDB's ISO date string. """
        if not date_string:
            return "No Date"
        try:
            # Parse the ISO format string (e.g., "2023-11-09T...Z")
            dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            # Format it as "Nov 09, 2023"
            return dt.strftime("%b %d, %Y")
        except ValueError:
            return date_string
            
    def format_time(self, date_string):
        """ Helper function to format MongoDB's ISO date string to time. """
        if not date_string:
            return "N/A"
        try:
            dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            # Format it as "08:51 PM"
            return dt.strftime("%I:%M %p")
        except ValueError:
            return date_string

class PictureMealPage(Screen):
    pass

class InputIngredientsPage(Screen):
    pass

class CameraPage(Screen):
    pass

class ProfilePage(Screen):
    def remove_tag(self, tag_layout):
        parent = tag_layout.parent
        parent.remove_widget(tag_layout)
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

class WindowManager(ScreenManager):
    pass

# Load the kv file
kv = Builder.load_file("KabuKids.kv")

class MultiScreenApp(App):
    user_data = None
    
    def build(self):
        return kv

if __name__ == '__main__':
    MultiScreenApp().run()