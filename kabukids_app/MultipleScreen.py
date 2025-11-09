import kivy
kivy.require('2.0.0')
from kivy.app import App
from kivy.uix.label import Label
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen

class MainWindow(Screen):
    pass

class SecondWindow(Screen):
    pass

class WindowManager(ScreenManager):
    pass

kv = Builder.load_file("multiple_screen.kv")

class MultiScreenApp(App):
    def build(self):
        return kv
    
if __name__ == '__main__':
    MultiScreenApp().run()