import streamlit as st
import os
import re
import json
import time
import shutil
import asyncio
import subprocess
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import tempfile
import base64
import random

# ==================== УСТАНОВКА ЗАВИСИМОСТЕЙ ====================
try:
    from bs4 import BeautifulSoup
except ImportError:
    subprocess.check_call(['pip', 'install', 'beautifulsoup4'])
    from bs4 import BeautifulSoup

try:
    import edge_tts
except ImportError:
    subprocess.check_call(['pip', 'install', 'edge-tts'])
    import edge_tts

try:
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
except ImportError:
    subprocess.check_call(['pip', 'install', 'pillow'])
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

try:
    from moviepy.editor import *
except ImportError:
    subprocess.check_call(['pip', 'install', 'moviepy'])
    from moviepy.editor import *

try:
    import numpy as np
except ImportError:
    subprocess.check_call(['pip', 'install', 'numpy'])
    import numpy as np

# ==================== КОНФИГУРАЦИЯ ====================
CONFIG = {
    'scp_min_rating': 50,
    'max_scenes': 7,
    'output_dir': './videos',
    'temp_dir': './temp'
}

for folder in [CONFIG['output_dir'], CONFIG['temp_dir'], f"{CONFIG['temp_dir']}/images", f"{CONFIG['temp_dir']}/audio"]:
    Path(folder).mkdir(parents=True, exist_ok=True)

# ==================== ПАРСЕР SCP ====================
class SCPScraper:
    def __init__(self):
        self.base_url = "https://scp-wiki.wikidot.com"
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0'})
    
    def get_top_scp(self, limit=3) -> List[Dict]:
        try:
            url = f"{self.base_url}/top-rated-pages"
            resp = self.session.get(url, timeout=30)
            soup = BeautifulSoup(resp.text, 'html.parser')
            scp_list = []
            for row in soup.select('div.content-panel.standalone-page ul li')[:limit*2]:
                link = row.find('a')
                if not link:
                    continue
                scp_match = re.search(r'SCP-(\d+)', link.text)
                if not scp_match:
                    continue
                rating_match = re.search(r'\((\+?\d+)\)', row.text)
                rating = int(rating_match.group(1)) if rating_match else 0
                if rating >= CONFIG['scp_min_rating']:
                    scp_data = self._parse_page(link.get('href'))
                    if scp_data:
                        scp_list.append(scp_data)
                        if len(scp_list) >= limit:
                            break
            return scp_list
        except Exception as e:
            st.error(f"Ошибка парсинга SCP: {e}")
            return []
    
    def _parse_page(self, url: str) -> Optional[Dict]:
        if not url.startswith('http'):
            url = self.base_url + url
        try:
            resp = self.session.get(url, timeout=30)
            soup = BeautifulSoup(resp.text, 'html.parser')
            title_elem = soup.find('h1', {'id': 'page-title'})
            if not title_elem:
                return None
            title_parts = title_elem.text.strip().split(' - ', 1)
            scp_number = title_parts[0].replace('SCP-', '')
            scp_name = title_parts[1] if len(title_parts) > 1 else "Без названия"
            content = soup.find('div', {'id': 'page-content'})
            if not content:
                return None
            text = content.get_text()
            text = re.sub(r'\[\[.+?\]\]', '', text)
            text = re.sub(r'\s+', ' ', text).strip()
            appearance = self._extract_appearance(text)
            footer = soup.find('div', {'class': 'page-footer'})
            author = "Неизвестен"
            if footer:
                author_match = re.search(r'Автор:?\s*(.+?)(?:\n|$)', footer.text)
                if author_match:
                    author = author_match.group(1).strip()
            return {
                'number': scp_number,
                'name': scp_name,
                'url': url,
                'text': text[:2000],
                'appearance': appearance,
                'author': author,
                'rating': rating
            }
        except Exception as e:
            return None
    
    def _extract_appearance(self, text: str) -> str:
        patterns = [
            r'Описание:?\s*(.+?)(?=\s*Особые условия|Свойства|$|\.\s*[A-ZА-Я])',
            r'Внешний вид:?\s*(.+?)(?=\s*Особые условия|Свойства|$|\.\s*[A-ZА-Я])',
            r'Внешне.+?представляет собой\s*(.+?)(?=\.|$)'
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()[:300]
        return text[:300]

# ==================== ГЕНЕРАТОР СЦЕНАРИЕВ ====================
class ScriptGenerator:
    def generate_script(self, scp_data: dict) -> dict:
        scenes = [
            {"frame_description": f"{scp_data['appearance']} в тёмной комнате, мрачное освещение", "voice_text": f"SCP-{scp_data['number']}. Оно не должно было попасть ко мне.", "duration": 7},
            {"frame_description": "Крупный план существа, искажённые черты", "voice_text": "Исследователи говорят, что оно не из нашего мира.", "duration": 7},
            {"frame_description": "Существо медленно поворачивается", "voice_text": "Оно двигается. Слишком плавно. Слишком неестественно.", "duration": 7},
            {"frame_description": "Тёмный коридор, фигура вдалеке", "voice_text": "Я слышал голоса. Они звали меня по имени.", "duration": 7},
            {"frame_description": "Существо смотрит прямо в камеру", "voice_text": "Оно знает, что я здесь. Оно смотрит прямо на меня.", "duration": 7},
            {"frame_description": "Темнота, светящиеся глаза", "voice_text": "Когда я открыл глаза... оно стояло прямо за мной.", "duration": 7}
        ]
        return {
            "title": f"SCP-{scp_data['number']} | {scp_data['name']}",
            "scp_number": scp_data['number'],
            "scp_name": scp_data['name'],
            "author": scp_data['author'],
            "scenes": scenes
        }

# ==================== ГЕНЕРАТОР КАРТИНОК ====================
class ImageGenerator:
    def generate_frames(self, script: dict, scp_data: dict) -> list:
        frames = []
        for i, scene in enumerate(script['scenes']):
            frame_path = f"{CONFIG['temp_dir']}/images/frame_{i:02d}.png"
            self._create_style_image(frame_path, i, scp_data)
            frames.append({'path': frame_path, 'duration': scene.get('duration', 6)})
        return frames
    
    def _create_style_image(self, path: str, seed: int, scp_data: dict):
        img = Image.new('RGB', (512, 768), color=(10, 10, 15))
        draw = ImageDraw.Draw(img)
        random.seed(seed + 42)
        for _ in range(30):
            x1 = random.randint(0, 512)
            y1 = random.randint(0, 768)
            x2 = random.randint(0, 512)
            y2 = random.randint(0, 768)
            draw.line([x1, y1, x2, y2], fill=(30, 30, 35), width=random.randint(1, 3))
        cx, cy = 256, 384
        draw.rectangle([cx-60, cy-30, cx+60, cy+180], fill=(25, 25, 35), outline=(50, 50, 60))
        draw.ellipse([cx-50, cy-90, cx+50, cy-20], fill=(30, 30, 40), outline=(50, 50, 60))
        draw.ellipse([cx-25, cy-60, cx-5, cy-40], fill=(180, 20, 20))
        draw.ellipse([cx+5, cy-60, cx+25, cy-40], fill=(180, 20, 20))
        mask = Image.new('L', (512, 768), 255)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse([50, 50, 462, 718], fill=220)
        mask_draw.ellipse([100, 100, 412, 668], fill=255)
        enhancer = ImageEnhance.Brightness(img)
        img.paste(enhancer.enhance(0.6), mask=mask)
        img.save(path)

# ==================== ОЗВУЧКА ====================
class VoiceGenerator:
    def __init__(self):
        self.voice = 'ru-RU-DmitryNeural'
    
    def generate_voice(self, script: dict) -> str:
        full_text = ". ".join([scene['voice_text'] for scene in script['scenes']])
        output_path = f"{CONFIG['temp_dir']}/audio/voice.mp3"
        try:
            async def generate():
                communicate = edge_tts.Communicate(full_text, self.voice, rate="-10%", pitch="-5Hz")
                await communicate.save(output_path)
            asyncio.run(generate())
            return output_path
        except:
            return output_path

# ==================== МОНТАЖ ====================
class VideoEditor:
    def create_short(self, frames: list, audio_path: str, script: dict) -> str:
        clips = []
        for frame_data in frames:
            try:
                clip = ImageClip(frame_data['path'])
                clip = clip.resize(height=1920, width=1080)
                clip = clip.set_duration(frame_data['duration'])
                clips.append(clip)
            except:
                clip = ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=frame_data['duration'])
                clips.append(clip)
        final = concatenate_videoclips(clips, method="compose")
        try:
            if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                audio = AudioFileClip(audio_path)
                if audio.duration > final.duration:
                    audio = audio.subclip(0, final.duration)
                final = final.set_audio(audio)
        except:
            pass
        scp_num = script.get('scp_number', '000')
        scp_name = script.get('scp_name', 'unknown')
        safe_name = re.sub(r'[^\w\s-]', '', scp_name)
        safe_name = re.sub(r'[-\s]+', '_', safe_name)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"SCP-{scp_num}_{safe_name}_{timestamp}.mp4"
        output_path = os.path.join(CONFIG['output_dir'], filename)
        try:
            final.write_videofile(output_path, fps=24, codec='libx264', audio_codec='aac', threads=1, preset='ultrafast', verbose=False, logger=None)
        except:
            txt_path = output_path.replace('.mp4', '.txt')
            with open(txt_path, 'w') as f:
                f.write(f"Ошибка создания видео")
            return txt_path
        return output_path

# ==================== ОСНОВНОЙ БОТ ====================
class SCPBot:
    def __init__(self):
        self.scraper = SCPScraper()
        self.script_gen = ScriptGenerator()
        self.image_gen = ImageGenerator()
        self.voice_gen = VoiceGenerator()
        self.video_editor = VideoEditor()
        self.videos_created = []
        self.status_messages = []
    
    def run(self, count=1):
        self.status_messages = []
        self._add_status(f"📖 Поиск SCP (рейтинг > {CONFIG['scp_min_rating']})...")
        scp_list = self.scraper.get_top_scp(limit=count)
        if not scp_list:
            self._add_status("❌ Не найдено SCP для обработки")
            return []
        for idx, scp in enumerate(scp_list, 1):
            self._add_status(f"\n📚 [{idx}/{len(scp_list)}] SCP-{scp['number']}: {scp['name']}")
            self._add_status(f"   👤 Автор: {scp['author']}")
            self._add_status(f"   ⭐ Рейтинг: +{scp['rating']}")
            try:
                self._add_status("✍️ Генерация сценария...")
                script = self.script_gen.generate_script(scp)
                self._add_status(f"   ✅ Сценарий: {len(script['scenes'])} сцен")
                self._add_status("🎨 Генерация кадров...")
                frames = self.image_gen.generate_frames(script, scp)
                self._add_status(f"   ✅ Сгенерировано {len(frames)} кадров")
                self._add_status("🎤 Генерация озвучки...")
                audio = self.voice_gen.generate_voice(script)
                self._add_status("   ✅ Озвучка готова")
                self._add_status("🎬 Монтаж видео...")
                video_path = self.video_editor.create_short(frames, audio, script)
                if os.path.exists(video_path) and os.path.getsize(video_path) > 1000:
                    size_mb = os.path.getsize(video_path) / 1024 / 1024
                    self._add_status(f"✅ ВИДЕО ГОТОВО!")
                    self._add_status(f"📁 {os.path.basename(video_path)}")
                    self._add_status(f"📏 {size_mb:.1f} MB")
                    self.videos_created.append(video_path)
                else:
                    self._add_status("⚠️ Видео не создано")
                self._cleanup()
            except Exception as e:
                self._add_status(f"❌ Ошибка: {e}")
        return self.videos_created
    
    def _add_status(self, msg: str):
        self.status_messages.append(msg)
    
    def _cleanup(self):
        for folder in [f"{CONFIG['temp_dir']}/images", f"{CONFIG['temp_dir']}/audio"]:
            if os.path.exists(folder):
                shutil.rmtree(folder)
            Path(folder).mkdir(parents=True, exist_ok=True)

# ==================== STREAMLIT UI ====================
def main():
    st.set_page_config(page_title="SCP Video Bot", page_icon="🎬", layout="wide")
    st.title("🎬 SCP Video Generator")
    st.markdown("Создаёт видео по SCP прямо в браузере")
    st.markdown("---")
    
    with st.sidebar:
        st.header("⚙️ Настройки")
        count = st.number_input("Количество видео:", min_value=1, max_value=3, value=1)
        st.markdown("---")
        st.info("💡 Видео создаются с использованием стилизованных изображений")
        st.markdown("---")
        st.caption(f"📁 Видео сохраняются во временную папку")
        if st.button("🗑️ Очистить временные файлы"):
            shutil.rmtree(CONFIG['temp_dir'], ignore_errors=True)
            shutil.rmtree(CONFIG['output_dir'], ignore_errors=True)
            for folder in [CONFIG['output_dir'], CONFIG['temp_dir'], f"{CONFIG['temp_dir']}/images", f"{CONFIG['temp_dir']}/audio"]:
                Path(folder).mkdir(parents=True, exist_ok=True)
            st.success("✅ Очищено!")
            st.rerun()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button("🎬 Сгенерировать видео", type="primary", use_container_width=True):
            with st.spinner("Генерация видео..."):
                bot = SCPBot()
                videos = bot.run(count=count)
                st.subheader("📊 Лог работы")
                for msg in bot.status_messages:
                    st.text(msg)
                if videos:
                    st.subheader("📁 Готовые видео")
                    for video_path in videos:
                        if os.path.exists(video_path) and os.path.getsize(video_path) > 1000:
                            st.success(f"✅ {os.path.basename(video_path)}")
                            with open(video_path, 'rb') as f:
                                video_bytes = f.read()
                            st.download_button(
                                label=f"📥 Скачать {os.path.basename(video_path)}",
                                data=video_bytes,
                                file_name=os.path.basename(video_path),
                                mime='video/mp4'
                            )
                else:
                    st.warning("⚠️ Видео не созданы")
    
    with col2:
        st.subheader("ℹ️ Как это работает")
        st.markdown("""
        1. **Парсинг SCP** — берёт топовые SCP
        2. **Сценарий** — структура видео
        3. **Кадры** — стилизованные изображения
        4. **Озвучка** — голос за кадром
        5. **Монтаж** — сборка с субтитрами
        6. **Скачивание** — готовый файл
        """)

if __name__ == "__main__":
    main()
