from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
import threading
import asyncio
import webbrowser

from search_logic import TelegramSearcher

API_ID = 2040
API_HASH = 'b18441a1ff607e10a989891a5462e627'


class MainApp(App):
    def build(self):
        self.searcher = TelegramSearcher(API_ID, API_HASH, session_name='app_session')
        self.logged_in = False

        root = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.status = Label(text='Введите номер телефона и нажмите «Войти»', size_hint_y=None, height=50)
        root.add_widget(self.status)

        self.phone_input = TextInput(hint_text='+79505645808', multiline=False, size_hint_y=None, height=50)
        root.add_widget(self.phone_input)

        self.code_input = TextInput(hint_text='Код из Telegram', multiline=False, size_hint_y=None, height=50)
        root.add_widget(self.code_input)

        self.login_btn = Button(text='Войти в Telegram', size_hint_y=None, height=50)
        self.login_btn.bind(on_press=self.do_login)
        root.add_widget(self.login_btn)

        self.query_input = TextInput(hint_text='Что искать? (например: мои фото)', multiline=False, size_hint_y=None, height=50)
        root.add_widget(self.query_input)

        self.search_btn = Button(text='Искать группы', size_hint_y=None, height=50)
        self.search_btn.bind(on_press=self.do_search)
        root.add_widget(self.search_btn)

        self.scroll = ScrollView()
        self.results_layout = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.results_layout.bind(minimum_height=self.results_layout.setter('height'))
        self.scroll.add_widget(self.results_layout)
        root.add_widget(self.scroll)
        return root

    def do_login(self, instance):
        phone = self.phone_input.text.strip()
        if not phone:
            self.status.text = 'Введите номер телефона!'
            return
        self.status.text = 'Подключение...'
        threading.Thread(target=self._login_thread, args=(phone,), daemon=True).start()

    def _login_thread(self, phone):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.searcher.connect())
            Clock.schedule_once(lambda dt: setattr(self.status, 'text', 'Код отправлен! Введите его.'))
        except Exception as e:
            Clock.schedule_once(lambda dt: setattr(self.status, 'text', f'Ошибка: {e}'))
        finally:
            loop.close()

    def do_search(self, instance):
        query = self.query_input.text.strip()
        if not query:
            self.status.text = 'Введите запрос для поиска!'
            return
        self.status.text = 'Поиск...'
        self.results_layout.clear_widgets()
        threading.Thread(target=self._search_thread, args=(query,), daemon=True).start()

    def _search_thread(self, query):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            async def run_search():
                if self.code_input.text.strip():
                    await self.searcher.client.sign_in(self.phone_input.text.strip(), self.code_input.text.strip())
                return await self.searcher.search_groups(
                    queries=[query],
                    keywords=['фото', 'видео', 'мои', 'наши', 'семейн'],
                    max_year=2026,
                    min_photos=0,
                    min_videos=0,
                    progress=lambda msg: Clock.schedule_once(lambda dt: setattr(self.status, 'text', msg))
                )
            results = loop.run_until_complete(run_search())
            Clock.schedule_once(lambda dt: self.show_results(results))
        except Exception as e:
            Clock.schedule_once(lambda dt: setattr(self.status, 'text', f'Ошибка: {e}'))
        finally:
            loop.close()

    def show_results(self, results):
        self.status.text = f'Найдено: {len(results)}'
        for r in results:
            btn = Button(
                text=f"{r['title']}\nфото: {r['photos']} | видео: {r['videos']}\nсоздана: {r['created']}",
                size_hint_y=None, height=100
            )
            btn.bind(on_press=lambda inst, link=r['link']: webbrowser.open(link))
            self.results_layout.add_widget(btn)


if __name__ == '__main__':
    MainApp().run()
