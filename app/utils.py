# utils.py
import json
import os
import re
import asyncio
import random
import yt_dlp
import discord
from mutagen import File
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.mp4 import MP4
from mutagen.oggvorbis import OggVorbis
from mutagen.wave import WAVE
from mutagen.id3 import TIT2, TPE1, TALB
import config

def load_json(filepath):
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def sanitize_filename(name):
    return re.sub(r'[\\/:*?"<>|]', '', name)

async def fetch_url_title(url):
    ydl_opts = {'quiet': True, 'extract_flat': True, 'force_generic_extractor': False}
    try:
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
            return info.get('title')
    except:
        return None

def save_metadata_to_file(filepath, metadata):
    try:
        if not os.path.exists(filepath): return False
        audio = File(filepath)
        if audio is None: return False
        
        title = metadata.get('title', '')
        artist = metadata.get('artist', '')
        album = metadata.get('album', '')

        if isinstance(audio, MP3):
            if not audio.tags:
                try: audio.add_tags()
                except: pass
            audio.tags['TIT2'] = TIT2(encoding=3, text=[title])
            audio.tags['TPE1'] = TPE1(encoding=3, text=[artist])
            audio.tags['TALB'] = TALB(encoding=3, text=[album])
        elif isinstance(audio, FLAC):
            audio['title'] = title
            audio['artist'] = artist
            audio['album'] = album
        elif isinstance(audio, MP4):
            audio['\xa9nam'] = [title]
            audio['\xa9ART'] = [artist]
            audio['\xa9alb'] = [album]
        elif isinstance(audio, OggVorbis):
            audio['title'] = title
            audio['artist'] = artist
            audio['album'] = album
        elif isinstance(audio, WAVE):
            try: audio.add_tags()
            except: pass
            if audio.tags:
                audio.tags['TIT2'] = TIT2(encoding=3, text=[title])
                audio.tags['TPE1'] = TPE1(encoding=3, text=[artist])
                audio.tags['TALB'] = TALB(encoding=3, text=[album])
        audio.save()
        return True
    except Exception as e:
        print(f"[Metadata Error] {e}")
        return False

# --- UI Views ---
class PraiseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) 
    @discord.ui.button(label="宮本ちゃんを褒める！(なでなで)", style=discord.ButtonStyle.green, emoji="👋")
    async def praise(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled = True
        button.label = "えへへ…ご主人様…❤️"
        button.style = discord.ButtonStyle.secondary
        await interaction.response.edit_message(view=self)
        msg = random.choice(config.PRAISE_MESSAGES)
        await interaction.followup.send(msg, ephemeral=True)

class ComfortView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="宮本ちゃんを慰める(よしよし)", style=discord.ButtonStyle.red, emoji="🥺")
    async def comfort(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled = True
        button.label = "元気でました…！✨"
        button.style = discord.ButtonStyle.secondary
        await interaction.response.edit_message(view=self)
        msg = random.choice(config.COMFORT_MESSAGES)
        await interaction.followup.send(msg, ephemeral=True)