from kivy.uix.screenmanager import Screen
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.app import App
from db import children_col
import uuid
from datetime import datetime
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button

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

class MakeAccountPage(Screen):
    # copy the add/remove tag and save_profile methods from original
    pass