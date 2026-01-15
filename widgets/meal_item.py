from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle
from kivy.app import App
from colors import DARK_COLOR, LIGHT_COLOR, ACCENT_COLOR, PRIMARY_COLOR, SECONDARY_COLOR, SUPER_LIGHT


class MealItem(BoxLayout):
    def __init__(self, meal_id, date, start_time, end_time, **kwargs):
        self.meal_id = meal_id
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(60)
        with self.canvas.before:
            # outer border
            Color(*SUPER_LIGHT)
            self.border_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
            # inner background (inset so border shows)
            Color(*PRIMARY_COLOR)
            inset = dp(3)
            self.bg_rect = RoundedRectangle(pos=(self.x + inset, self.y + inset),
                                            size=(self.width - inset*2, self.height - inset*2),
                                            radius=[dp(6)])
        self.bind(pos=self._update_rect, size=self._update_rect)

        info_layout = BoxLayout(orientation='vertical', padding=[dp(10), dp(5)])
        info_layout.add_widget(Label(text=date, font_size='14sp', color=SECONDARY_COLOR, size_hint_y=None, height=dp(20)))
        info_layout.add_widget(Label(text=f"Start: {start_time} | End: {end_time}", font_size='12sp', color=LIGHT_COLOR, size_hint_y=None, height=dp(16)))
        self.add_widget(info_layout)

        more_btn = Button(
            text="More",
            size_hint_x=None,
            width=dp(70),
            background_normal='',
            background_color=ACCENT_COLOR,
            color=PRIMARY_COLOR,
            bold=True
        )
        more_btn.bind(on_press=self.go_to_report)
        self.add_widget(more_btn)

    def _update_rect(self, *args):
        # update border rect
        try:
            self.border_rect.pos = self.pos
            self.border_rect.size = self.size
            # update inner/bg rect with same inset used in init
            inset = dp(3)
            self.bg_rect.pos = (self.x + inset, self.y + inset)
            self.bg_rect.size = (self.width - inset*2, self.height - inset*2)
        except Exception:
            pass

    def go_to_report(self, instance):
        app = App.get_running_app()
        app.selected_meal_id = self.meal_id
        app.root.current = "report"