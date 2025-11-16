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

    def select_profile_picture(self):
        """Open a native file dialog to pick an image and update profile image widgets."""
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            path = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp")])
            root.destroy()
        except Exception:
            path = ""

        if not path:
            return

        # store for screens to read
        self.profile_image_path = path

        # Try to update common screens that show a profile image
        for screen_name in ("edit_profile", "profile", "make_account"):
            try:
                screen = self.root.get_screen(screen_name)
                if hasattr(screen, "ids") and "profile_image" in screen.ids:
                    try:
                        screen.ids.profile_image.source = path
                        screen.ids.profile_image.reload()
                    except Exception:
                        pass
            except Exception:
                pass

if __name__ == "__main__":
    MultiScreenApp().run()