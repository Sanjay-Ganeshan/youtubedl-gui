import kivy
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image, AsyncImage
from kivy.core.image import Image as RawImage
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.checkbox import CheckBox
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.graphics import Rectangle, Color as IColor
from kivy.resources import resource_find
from kivy.properties import NumericProperty, BooleanProperty, StringProperty
from kivy.effects.scroll import ScrollEffect

import os
import typing as T
from .dlmanager import DownloadEntry, extract_url_ids, playlist_items

import random



PLACEHOLDER_TITLES = ["Legends Never Die", "The Phoenix", "Fighting the World", "Ice Ice Baby", "Pacific Rim Theme", "117", "Warriors", "Demons", "Monster"]
PLACEHOLDER_IMG = resource_find("placeholder.png")
ICON_MUSIC = resource_find("icon_music.png")
ICON_FOLDER = resource_find("icon_folder.png")
ICON_DONE = resource_find("icon_done.png")
ICON_DELETE = resource_find("icon_delete.png")
ICON_DOWNLOAD = resource_find("icon_download.png")



class Placeholder(Image):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, source=PLACEHOLDER_IMG, **kwargs)

class ImageButton(Button):
    source = StringProperty("")

    def __init__(self, source="", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.img = None
        self.img_src = ""
        self.rect = Rectangle(pos=(0,0), size=(1,1), texture=None)
        self.bind(source=self.refresh_rect, size=self.refresh_rect, pos=self.refresh_rect)
        self.source = source
        self.canvas.add(IColor(rgb=(1,1,1)))

    def refresh_rect(self, *args):
        if str(self.source) == self.img_src:
            # Already up to date
            pass

        else:
            if self.source == "":
                self.img = None
                self.img_src = ""
                self.rect.texture = None
                if self.rect in self.canvas.children:
                    self.canvas.remove(self.rect)
            else:
                self.img = RawImage(self.source)
                self.img_src = str(self.source)
                self.rect.texture = self.img.texture
                if self.rect not in self.canvas.children:
                    self.canvas.add(self.rect)
        

        if self.img is not None:
            mypos = tuple(map(int, self.pos))
            mysize = tuple(map(int, self.size))

            # We want to maintain aspect ratio
            wmult = mysize[0]*0.9 / self.img.width
            hmult = mysize[1]*0.9 / self.img.height

            bettermult = min(wmult, hmult)

            outw = int(self.img.width * bettermult)
            outh = int(self.img.height * bettermult)

            paddingw = (mysize[0] - outw) // 2
            paddingh = (mysize[1] - outh) // 2

            self.rect.pos = (paddingw+mypos[0], paddingh+mypos[1])
            self.rect.size = (outw, outh)

class YTDLQueueControls(BoxLayout):
    def __init__(self, ui_root, *args, **kwargs):
        super().__init__(*args, orientation="horizontal", **kwargs)
        self.ui_root = ui_root
        self.url_input = TextInput(multiline=False, size_hint=(0.8, 1.0))
        self.add_video = Button(text="Video", on_press=self.submit_video, size_hint=(0.1, 1.0), disabled=True)
        self.add_playlist = Button(text="Playlist", on_press=self.submit_playlist, size_hint=(0.1, 1.0), disabled=True)

        self.url_input.bind(text=self.on_text_changed, on_text_validate=self.submit_playlist_or_video)

        self.add_widget(self.url_input)
        self.add_widget(self.add_video)
        self.add_widget(self.add_playlist)
    
    def get_entered_ids(self):
        inp = str(self.url_input.text).strip()
        if inp.startswith("http"):
            # It's a url
            v_id, pl_id = extract_url_ids(inp)
            if v_id is not None and len(v_id) != 11:
                v_id = None
            return v_id, pl_id

        else:
            v_id = inp if len(inp) == 11 else None
            return v_id, None

    def on_text_changed(self, *args):
        v_id, pl_id = self.get_entered_ids()
        self.add_video.disabled = v_id is None
        self.add_playlist.disabled = pl_id is None
    
    def submit_video(self, *args):
        v_id, pl_id = self.get_entered_ids()
        if v_id is not None:
            self.ui_root.dl_queue.add_new_download(url=v_id)
            self.url_input.text = ""
        
    def submit_playlist(self, *args):
        v_id, pl_id = self.get_entered_ids()
        if pl_id is not None:
            items = playlist_items(pl_id)
            if items is not None:
                # Valid playlist
                for each_video in items:
                    self.ui_root.dl_queue.add_new_download(url=each_video)
                self.url_input.text = ""
    
    def submit_playlist_or_video(self, *args):
        v_id, pl_id = self.get_entered_ids()
        if pl_id is not None:
            self.submit_playlist()
        elif v_id is not None:
            self.submit_video()
        else:
            # Do nothing
            pass
    
class YTDLQueueEntry(BoxLayout):
    download_progress = NumericProperty(0.0)
    done = BooleanProperty(False)

    def __init__(self, ui_root, url=None, *args, **kwargs):
        super().__init__(*args, orientation='horizontal', **kwargs)
        self.ui_root = ui_root

        self.info = DownloadEntry()
        self.info.set_url(url)
        self.info.bind(progress=self.dl_on_progress, done=self.dl_on_done)

        self.thumbnail = AsyncImage(source=PLACEHOLDER_IMG, size_hint=(0.1, 1.0), allow_stretch=True)
        self.description = Label(text="URL Needed", size_hint=(0.6, 1.0))
        self.description.font_size = 20
        self.description.text_size = self.description.size
        self.description.bind(size=self.on_desc_size_changed)

        self.remove_from_queue = ImageButton(on_press=self.on_remove_pressed, size_hint=(0.1, 1.0), source=ICON_DELETE)
        self.reveal_icon = ICON_FOLDER
        self.download_icon = ICON_DOWNLOAD
        self.download_or_reveal = ImageButton(on_press=self.on_dl_or_reveal_pressed, size_hint=(0.1, 1.0))

        self.add_widget(self.thumbnail)
        self.add_widget(self.description)
        self.add_widget(self.remove_from_queue)

        self.refresh_from_info()
        self.bind(done=self.refresh_from_info)

    def on_dl_or_reveal_pressed(self, *args):
        if self.info.is_revealable():
            self.on_reveal_pressed()
        elif self.info.is_downloadable():
            self.on_dl_pressed()

    def refresh_buttons(self, *args):
        self.remove_from_queue.disabled = not self.info.is_forgettable()

        which_icon = None

        if self.info.is_revealable():
            which_icon = self.reveal_icon
        elif self.info.is_downloadable():
            which_icon = self.download_icon
        else:
            which_icon = None

        if which_icon is None:
            if self.download_or_reveal in self.children:
                self.remove_widget(self.download_or_reveal)
        else:
            if self.download_or_reveal not in self.children:
                self.add_widget(self.download_or_reveal)
            self.download_or_reveal.source = which_icon

    def dl_on_progress(self, amount: float):
        self.download_progress = amount
    
    def dl_on_done(self, success: bool):
        self.done = success
        self.ui_root.refresh()

    def on_dl_pressed(self, *args):
        self.ui_root.details.update_info()
        self.info.download()
        self.ui_root.refresh()
    
    def on_remove_pressed(self, *args):
        self.ui_root.remove_queue_entry(self)

    def on_reveal_pressed(self, *args):
        self.info.reveal_in_explorer()

    def on_touch_up(self, touch):
        if ((
                self.thumbnail.collide_point(*touch.pos) or 
                self.description.collide_point(*touch.pos)
            ) and not (
                self.download_or_reveal.collide_point(*touch.pos) or
                self.remove_from_queue.collide_point(*touch.pos)
            )):
            self.ui_root.select_entry(self)
            return True
        else:
            return False

    def on_desc_size_changed(self, inst, val):
        self.description.text_size=self.description.size

    def refresh_from_info(self, *args):
        if self.info.valid():
            if self.info.audio_only:
                self.thumbnail.source = ICON_MUSIC
            else:
                self.thumbnail.source = self.info.vthumbnail()
        else:
            self.thumbnail.source = PLACEHOLDER_IMG
        desctext = f"{self.info.otitle()} ({self.info.vformattedduration()})"
        if len(desctext) == 0:
            desctext = "NEEDS INFO"
        self.description.text = desctext
        self.refresh_buttons()

    def select(self):
        self.description.color = (0.7, 0.7, 1.0, 1.0)
        self.description.bold = True

    def deselect(self):
        self.description.color = (1.0, 1.0, 1.0, 1.0)
        self.description.bold = False

class YTDLDownloadQueueContents(BoxLayout):
    per_entry_height = NumericProperty(40)

    def __init__(self, ui_root, *args, **kwargs):
        super().__init__(*args, orientation='vertical', **kwargs)
        self.ui_root = ui_root
        self.entries = []

        self.bind(per_entry_height=self.change_all_heights)
        self.change_all_heights(self, self.per_entry_height)

    def refresh_all(self):
        for entry in self.entries:
            entry.refresh_from_info()


    def change_all_heights(self, inst, val):
        for entry in self.entries:
            entry.height = self.per_entry_height
        self.height = self.per_entry_height * len(self.entries)

    def add_new_download(self, url=None):
        new_entry = YTDLQueueEntry(self.ui_root, url=url, size_hint=(1.0, None))
        self.entries.append(new_entry)
        self.add_widget(new_entry)
        self.change_all_heights(self, self.per_entry_height)
        return new_entry
    
    def remove_queue_entry(self, wdg):
        if wdg in self.entries:
            self.entries.remove(wdg)
            self.remove_widget(wdg)
            self.change_all_heights(self, self.per_entry_height)
        self.refresh_all()

    def get_first_download(self) -> T.Optional[YTDLQueueEntry]:
        for each_entry in self.entries:
            if each_entry.info.is_downloadable():
                return each_entry
        else:
            return None

class YTDLDownloadQueueScroller(ScrollView):
    def __init__(self, ui_root, *args, **kwargs):
        super().__init__(*args, do_scroll_x = False, always_overscroll = False, scroll_type=['bars', 'content'], **kwargs)
        self.effect_cls = ScrollEffect
        self.ui_root = ui_root
        self.contents = YTDLDownloadQueueContents(ui_root, size_hint_x=1.0, size_hint_y=None, height=10)
        self.add_widget(self.contents)
        self.bind(height=self.on_height_changed)
        self.on_height_changed(self, self.height)

    def refresh_all(self):
        self.contents.refresh_all()

    def select_entry(self, wdg):
        self.scroll_to(wdg)

    def add_new_download(self, url=None):
        wdg = self.contents.add_new_download(url)
        if wdg is not None:
            self.ui_root.select_entry(wdg)

    def on_height_changed(self, inst, val):
        self.contents.per_entry_height = self.height // 10
    
    def remove_queue_entry(self, wdg):
        self.contents.remove_queue_entry(wdg)
        self.refresh_all()

    def get_first_download(self) -> T.Optional[YTDLQueueEntry]:
        return self.contents.get_first_download()

class YTDLConfigEntryView(BoxLayout):
    def __init__(self, ui_root, *args, **kwargs):
        super().__init__(*args, orientation='vertical', **kwargs)
        self.ui_root = ui_root

        # URL
        self.url_entry = BoxLayout(orientation='horizontal', size_hint=(1.0, 0.1))
        self.lbl_url = Label(text='URL:', size_hint=(0.1, 1.0))
        self.txt_url = TextInput(multiline=False, size_hint=(0.9, 1.0))

        self.url_entry.add_widget(self.lbl_url)
        self.url_entry.add_widget(self.txt_url)

        # Audio Only
        self.dltype_entry = BoxLayout(orientation='horizontal', size_hint=(1.0, 0.1))
        self.dltype_audio = ToggleButton(text='Audio Only', group='dltype', size_hint=(0.5, 1.0), state='down')
        self.dltype_video = ToggleButton(text='Video', group='dltype', size_hint=(0.5, 1.0))

        self.dltype_entry.add_widget(self.dltype_audio)
        self.dltype_entry.add_widget(self.dltype_video)

        self.subtitle_entry = BoxLayout(orientation='horizontal', size_hint=(1.0, 0.1))
        self.chk_subtitles = CheckBox(size_hint=(0.1, 1.0))
        self.lbl_subtitles = Label(text="Download Subtitles", size_hint=(0.9, 1.0))
        self.lbl_subtitles.bind(size=self.align_subtitle)
        self.align_subtitle()

        self.subtitle_entry.add_widget(self.chk_subtitles)
        self.subtitle_entry.add_widget(self.lbl_subtitles)
        
        self.title_entry = BoxLayout(orientation='horizontal', size_hint=(1.0, 0.1))
        self.lbl_title = Label(text="Title:", size_hint=(0.2, 1.0))
        self.txt_title = TextInput(multiline=False, size_hint=(0.8, 1.0))
        self.title_entry.add_widget(self.lbl_title)
        self.title_entry.add_widget(self.txt_title)

        self.author_entry = BoxLayout(orientation='horizontal', size_hint=(1.0, 0.1))
        self.lbl_author = Label(text="Author:", size_hint=(0.2, 1.0))
        self.txt_author = TextInput(multiline=False, size_hint=(0.8, 1.0))
        self.author_entry.add_widget(self.lbl_author)
        self.author_entry.add_widget(self.txt_author)

        self.add_widget(self.url_entry)
        self.add_widget(self.dltype_entry)
        self.add_widget(self.subtitle_entry)
        self.add_widget(self.title_entry)
        self.add_widget(self.author_entry)
    
    def align_subtitle(self, *args):
        self.lbl_subtitles.text_size = self.lbl_subtitles.size
        self.lbl_subtitles.halign = 'left'
        self.lbl_subtitles.valign = 'middle'

class YTDLDetailView(BoxLayout):
    editable = BooleanProperty(False)

    def __init__(self, ui_root, *args, **kwargs):
        super().__init__(*args, orientation='vertical', **kwargs)
        self.ui_root = ui_root
        self.thumbnail = AsyncImage(source=PLACEHOLDER_IMG, size_hint=(1.0, 0.5), allow_stretch=True)
        self.config_entry = YTDLConfigEntryView(ui_root, size_hint=(1.0, 0.5))
        self.add_widget(self.thumbnail)
        self.add_widget(self.config_entry)

        self.selected_download = None
        self.populate(None)

        self.config_entry.txt_title.bind(on_text_validate=self.update_info, focus=self.on_focus)
        self.config_entry.txt_author.bind(on_text_validate=self.update_info, focus=self.on_focus)
        self.config_entry.txt_url.bind(on_text_validate=self.update_info, focus=self.on_focus)
        self.config_entry.dltype_audio.on_press = self.update_info
        self.config_entry.dltype_video.on_press = self.update_info
        self.config_entry.chk_subtitles.on_press = self.update_info
        self.bind(editable=self.on_editable_changed)
    
    def on_focus(self, inst, val):
        if not val:
            self.update_info()

    def populate(self, info: DownloadEntry):
        self.selected_download = info
        self.refresh()

    def on_editable_changed(self, *args):
        self.config_entry.txt_url.disabled = not self.editable
        self.config_entry.txt_title.disabled = not self.editable
        self.config_entry.txt_author.disabled = not self.editable
        self.config_entry.dltype_audio.disabled = not self.editable
        self.config_entry.dltype_video.disabled = not self.editable
        self.config_entry.chk_subtitles.disabled = not self.editable

    def update_info(self, *args):
        none_for_empty = lambda s: None if len(s.strip()) == 0 else s
        clean = lambda s: " ".join(s.split()).strip()

        if self.selected_download is not None:
            self.selected_download.set_url(none_for_empty(clean(self.config_entry.txt_url.text)))
            self.selected_download.title = none_for_empty(clean(self.config_entry.txt_title.text))
            self.selected_download.author = none_for_empty(clean(self.config_entry.txt_author.text))
            self.selected_download.subtitles = self.config_entry.chk_subtitles.active
            self.selected_download.audio_only = self.config_entry.dltype_audio.state == 'down'
            self.refresh()


    def refresh(self):
        if self.selected_download is not None:
            self.thumbnail.source = self.selected_download.vthumbnail()
            self.config_entry.txt_url.text = self.selected_download.url if self.selected_download.url is not None else ""
            self.config_entry.txt_title.text = self.selected_download.otitle()
            self.config_entry.txt_author.text = self.selected_download.oauthor()
            self.config_entry.chk_subtitles.active = self.selected_download.subtitles
            if self.selected_download.audio_only:
                self.config_entry.dltype_audio.state = 'down'
                self.config_entry.dltype_video.state = 'normal'
            else:
                self.config_entry.dltype_audio.state = 'normal'
                self.config_entry.dltype_video.state = 'down'
            self.editable = self.selected_download.editable
        else:
            self.config_entry.txt_url.text = ""
            self.config_entry.txt_title.text = ""
            self.config_entry.txt_author.text = ""
            self.config_entry.chk_subtitles.active = False
            self.config_entry.dltype_audio.state = 'normal'
            self.config_entry.dltype_video.state = 'normal'
            self.editable = False
        self.ui_root.dl_queue.refresh_all()

class YTDLRoot(BoxLayout):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, orientation='vertical', **kwargs)
        self.controls = YTDLQueueControls(self, size_hint=(1.0, 0.05))

        self.main_body = BoxLayout(orientation='horizontal', size_hint=(1.0, 0.9))
        self.dl_queue = YTDLDownloadQueueScroller(self, size_hint=(0.5, 1.0))
        self.details = YTDLDetailView(self, size_hint=(0.5, 1.0))
        self.main_body.add_widget(self.dl_queue)
        self.main_body.add_widget(self.details)

        self.progress_body = BoxLayout(orientation='horizontal', size_hint=(1.0, 0.05))
        self.download_all_button = Button(text="Download All", on_press = self.download_all, size_hint=(0.2, 1.0))
        self.progress = ProgressBar(max = 100, size_hint=(0.4, 1.0))
        self.lbl_progress = Label(text="Idle", size_hint=(0.4, 1.0))
        self.progress_body.add_widget(self.download_all_button)
        self.progress_body.add_widget(self.lbl_progress)
        self.progress_body.add_widget(self.progress)
        
        self.add_widget(self.controls)
        self.add_widget(self.main_body)
        self.add_widget(self.progress_body)
        self.bound_wdg = None

        self.current_download = None

        self.hide_details()

    def select_entry(self, wdg):
        is_new = not (self.bound_wdg == wdg)
        if wdg is not None:
            self.deselect()
            if is_new:
                self.bound_wdg = wdg
                self.dl_queue.select_entry(wdg)
                self.details.populate(wdg.info)
                wdg.select()
                self.show_details()
                self.refresh()
    
    def deselect(self):
        # Whenever you deselect, make sure updates get pushed
        self.details.update_info()
        self.details.populate(None)
        if self.bound_wdg is not None:
            self.bound_wdg.deselect()
            self.bound_wdg = None
        self.hide_details()
        self.refresh()

    def remove_queue_entry(self, wdg):
        self.deselect()
        self.dl_queue.remove_queue_entry(wdg)

    def refresh(self):
        self.details.refresh()
        self.dl_queue.refresh_all()

    def reset_progress(self, *args):
        self.lbl_progress.text = "Downloading"
        self.progress.value = 0

    def on_dl_progress(self, inst, val):
        self.progress.value = int(val * 100)
        if self.progress.value >= 99:
            self.lbl_progress.text = "Converting"
        else:
            self.lbl_progress.text = "Downloading"
    
    def on_dl_done(self, inst, val):
        self.progress.value = 100 if val else 0
        self.lbl_progress.text = "Done!"

    def show_details(self):
        if self.details not in self.main_body.children:
            self.main_body.add_widget(self.details)

    def hide_details(self):
        if self.details in self.main_body.children:
            self.main_body.remove_widget(self.details)
        
    def get_first_download(self) -> T.Optional[YTDLQueueEntry]:
        return self.dl_queue.get_first_download()
    
    def download_all(self, *args):
        if self.current_download is not None:
            self.current_download.unbind(download_progress=self.on_dl_progress, done=self.download_all)
        self.current_download = self.get_first_download()
        if self.current_download is not None:
            self.reset_progress()
            self.current_download.bind(download_progress=self.on_dl_progress, done=self.download_all)
            # Just trigger the "download button pressed" event
            self.current_download.on_dl_pressed()
            

class YTDLApp(App):
    def build(self):
        return YTDLRoot()
