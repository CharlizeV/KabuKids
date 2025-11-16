from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle
from kivy.app import App

DARK_COLOR = (0, 0, 0, 1)

class MealItem(BoxLayout):
    def __init__(self, meal_id, date, start_time, end_time, **kwargs):
        self.meal_id = meal_id
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(60)
        with self.canvas.before:
            Color(0.95,0.95,0.95,1)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
        self.bind(pos=self._update_rect, size=self._update_rect)

        info_layout = BoxLayout(orientation='vertical', padding=[dp(10), dp(5)])
        info_layout.add_widget(Label(text=date, font_size='14sp', color=DARK_COLOR, size_hint_y=None, height=dp(20)))
        info_layout.add_widget(Label(text=f"Start: {start_time} | End: {end_time}", font_size='12sp', color=(0.35,0.35,0.35,1), size_hint_y=None, height=dp(16)))
        self.add_widget(info_layout)

        more_btn = Button(text="More", size_hint_x=None, width=dp(70))
        more_btn.bind(on_press=self.go_to_report)
        self.add_widget(more_btn)

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def go_to_report(self, instance):
        app = App.get_running_app()
        app.selected_meal_id = self.meal_id
        app.root.current = "report"