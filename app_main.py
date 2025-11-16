from kivy.app import App
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.screenmanager import ScreenManager


# import grouped screen modules so Builder can find class names in KV
import screens.auth
import screens.dashboard_report
import screens.profile
import screens.meal_flow
# import widgets used by KV
import widgets.meal_item

class WindowManager(ScreenManager):
    pass

class MultiScreenApp(App):
    profile_image_path = StringProperty("")
    selected_meal_id = StringProperty("")

    def build(self):
        return Builder.load_file("KabuKids.kv")

if __name__ == "__main__":
    MultiScreenApp().run()