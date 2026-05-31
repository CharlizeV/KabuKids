from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.metrics import dp, sp
from kivy.graphics import Color, RoundedRectangle
from kivy.app import App
from colors import DARK_COLOR, LIGHT_COLOR, ACCENT_COLOR, PRIMARY_COLOR, SECONDARY_COLOR


class MealItem(BoxLayout):
    def __init__(self, meal_id, date, start_time, end_time, **kwargs):
        self.meal_id = meal_id
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint = (None, None)
        self.size = (dp(300), dp(200))
        self.size_hint_y = None
        self.height = dp(200)
        self.padding = (dp(20), dp(18))
        self.spacing = dp(12)
        with self.canvas.before:
            Color(0.71, 0.76, 0.45, 1)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=self._update_rect, size=self._update_rect)

        info_layout = BoxLayout(orientation='vertical', spacing=dp(8), padding=(0, dp(20), 0, 0))

        date_label = Label(
            text=date,
            font_name="screens/fonts/Valekon.otf",
            font_size=sp(24),
            color=DARK_COLOR,
            bold=True,
            halign='left',
            valign='middle',
            text_size=(dp(216), None),
            size_hint_y=None,
            height=dp(30),
        )
        date_label.bind(texture_size=lambda instance, size: setattr(instance, 'height', size[1]))
        info_layout.add_widget(date_label)
        time_text = f"{start_time} - {end_time}" if start_time and end_time else (start_time or end_time or "")
        info_layout.add_widget(Label(
            text=time_text,
            font_size=sp(15),
            color=PRIMARY_COLOR,
            halign='left',
            valign='middle',
            text_size=(dp(216), None),
            size_hint_y=None,
            height=dp(30),
        ))
        info_layout.add_widget(BoxLayout())
        self.add_widget(info_layout)

        more_btn = Button(
            text="View More",
            size_hint=(None, None),
            width=dp(100),
            height=dp(28),
            background_normal='',
            background_down='',
            background_color=(0, 0, 0, 0),
            color=DARK_COLOR,
            font_name="screens/fonts/Valekon.otf",
            font_size=sp(14),
            bold=True,
            pos_hint={'right': 1},
        )
        with more_btn.canvas.before:
            Color(0.95, 0.82, 0.35, 1)
            more_btn.bg_rect = RoundedRectangle(pos=more_btn.pos, size=more_btn.size, radius=[dp(8)])
        more_btn.bind(pos=self._update_button_rect, size=self._update_button_rect)
        more_btn.bind(on_press=self.go_to_report)
        self.add_widget(more_btn)

    def _update_rect(self, *args):
        try:
            self.bg_rect.pos = self.pos
            self.bg_rect.size = self.size
        except Exception:
            pass

    def _update_button_rect(self, button, *args):
        try:
            button.bg_rect.pos = button.pos
            button.bg_rect.size = button.size
        except Exception:
            pass

    def go_to_report(self, instance):
        app = App.get_running_app()
        app.selected_meal_id = self.meal_id
        app.root.current = "report"