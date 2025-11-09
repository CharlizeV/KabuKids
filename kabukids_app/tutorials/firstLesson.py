import kivy
kivy.require('2.0.0')
from kivy.app import App
from kivy.uix.label import Label

class FirstLessonApp(App):
    def build(self):
        return Label(text='Hello, Kivy!')
    
if __name__ == '__main__':
    FirstLessonApp().run()