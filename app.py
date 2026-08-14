import streamlit as st
import os
import re
import json
import time
import shutil
import asyncio
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import random
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
import io

# ==================== ФИКС ДЛЯ ANTIALIAS ====================
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

# ==================== УСТАНОВКА ЗАВИСИМОСТЕЙ ====================
try:
    from moviepy.editor import *
except ImportError:
    import subprocess
    subprocess.check_call(['pip', 'install', 'moviepy'])
    from moviepy.editor import *

try:
    import edge_tts
except ImportError:
    import subprocess
    subprocess.check_call(['pip', 'install', 'edge-tts'])
    import edge_tts

# ==================== КОНФИГУРАЦИЯ ====================
CONFIG = {
    'output_dir': './videos',
    'temp_dir': './temp',
    'unsplash_key': ''  # Оставьте пустым для 50 запросов/час, или вставьте свой ключ
}

for folder in [CONFIG['output_dir'], CONFIG['temp_dir'], f"{CONFIG['temp_dir']}/images", f"{CONFIG['temp_dir']}/audio"]:
    Path(folder).mkdir(parents=True, exist_ok=True)

# ==================== БАЗА SCP (только текст) ====================
SCP_DATABASE = [
    {
        "number": "173",
        "name": "Скульптура",
        "author": "М. Роджерс",
        "text": "SCP-173 - статуя из бетона и арматуры. Она неподвижна, когда на неё смотрят."
    },
    {
        "number": "049",
        "name": "Чумной доктор",
        "author": "Габриэль",
        "text": "SCP-049 - гуманоид, который считает себя врачом."
    },
    {
        "number": "096",
        "name": "Застенчивый парень",
        "author": "Доктор Дэн",
        "text": "SCP-096 - существо, которое не переносит, когда на него смотрят."
    },
    {
        "number": "106",
        "name": "Старый человек",
        "author": "Доктор Гирс",
        "text": "SCP-106 - гуманоид, который может проходить сквозь твёрдые материалы."
    },
    {
        "number": "682",
        "name": "Трудный для уничтожения ящер",
        "author": "Доктор Гирс",
        "text": "SCP-682 - огромная рептилия, которая не умирает."
    },
    {
        "number": "999",
        "name": "Щекочущий монстр",
        "author": "Доктор Кейн",
        "text": "SCP-999 - дружелюбное существо, которое щекочет людей."
    },
    {
        "number": "087",
        "name": "Лестница в подвал",
        "author": "Доктор У. Уилсон",
        "text": "SCP-087 - бесконечная лестница."
    },
    {
        "number": "3000",
        "name": "Анаджвари",
        "author": "Доктор В. Д.",
        "text": "SCP-3000 - гигантский змей."
    }
]

# ==================== ПОИСК ИЗОБРАЖЕНИЙ В ИНТЕРНЕТЕ ====================
class ImageSearcher:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.base_url = "https://api.unsplash.com/search/photos"
        self.headers = {"Authorization": f"Client-ID {api_key}"} if api_key else {}
    
    def search(self, query: str, per_page: int = 1) -> List[str]:
        """Ищет изображения по запросу и возвращает список URL"""
        params = {
            "query": query,
            "per_page": per_page,
            "orientation": "portrait"  # Для вертикальных видео
        }
        try:
            response = requests.get(self.base_url, headers=self.headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                urls = [result['urls']['regular'] for result in data.get('results', [])]
                return urls
            elif response.status_code == 403 and "rate limit" in response.text.lower():
                st.warning("⚠️ Превышен лимит запросов Unsplash (50/час). Использую заглушки.")
                return []
            else:
                st.warning(f"Ошибка поиска: {response.status_code}")
                return []
        except Exception as e:
            st.warning(f"Ошибка соединения: {e}")
            return []
    
    @staticmethod
    def download_image(url: str, save_path: str) -> bool:
        """Скачивает изображение по URL"""
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                img = Image.open(io.BytesIO(response.content))
                # Приводим к вертикальному формату
                width, height = img.size
                if width > height:
                    crop = height
                    left = (width - crop) // 2
                    img = img.crop((left, 0, left + crop, height))
                img = img.resize((720, 1280), Image.LANCZOS)
                img.save(save_path)
                return True
        except Exception as e:
            print(f"Ошибка скачивания: {e}")
        return False
    
    @staticmethod
    def create_fallback_image(seed: int) -> Image.Image:
        """Заглушка (скетч) если поиск не дал результатов"""
        width, height = 720, 1280
        img = Image.new('RGB', (width, height), color=(240, 235, 225))
        draw = ImageDraw.Draw(img)
        random.seed(seed)
        for _ in range(1000):
            x = random.randint(0, width-1)
            y = random.randint(0, height-1)
            br = random.randint(200, 240)
            draw.point((x, y), fill=(br, br-5, br-10))
        # Рисуем абстрактную фигуру (скетч)
        cx, cy = width//2, height//2
        draw.rectangle([cx-100, cy-50, cx+100, cy+250], outline=(50, 50, 60), width=3)
        draw.ellipse([cx-80, cy-140, cx+80, cy-30], outline=(50, 50, 60), width=3)
        draw.ellipse([cx-30, cy-90, cx-10, cy-70], fill=(150, 40, 40))
        draw.ellipse([cx+10, cy-90, cx+30, cy-70], fill=(150, 40, 40))
        mask = Image.new('L', (width, height), 255)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse([80, 80, width-80, height-80], fill=200)
        mask_draw.ellipse([180, 180, width-180, height-180], fill=255)
        enhancer = ImageEnhance.Brightness(img)
        img.paste(enhancer.enhance(0.6), mask=mask)
        return img

# ==================== ГЕНЕРАТОР СЦЕНАРИЕВ И КЛЮЧЕВЫХ СЛОВ ====================
class ScriptGenerator:
    def generate_script(self, scp_data: dict) -> dict:
        scenes = [
            {"keywords": f"{scp_data['name']} dark atmosphere horror", "voice_text": f"Я нашёл это в старом архиве. SCP-{scp_data['number']} - {scp_data['name']}.", "duration": 7},
            {"keywords": f"{scp_data['name']} close up details", "voice_text": f"{scp_data['text']}", "duration": 8},
            {"keywords": f"{scp_data['name']} creepy movement", "voice_text": "Оно двигается. Не как человек. Слишком плавно.", "duration": 7},
            {"keywords": f"{scp_data['name']} shadows horror", "voice_text": "Я слышал голоса. Они звали меня по имени.", "duration": 7},
            {"keywords": f"{scp_data['name']} scary eyes", "voice_text": "Оно знает, что я здесь. Оно смотрит прямо на меня.", "duration": 7},
            {"keywords": f"{scp_data['name']} behind you", "voice_text": "Я закрыл глаза. Но когда открыл... оно стояло прямо за мной.", "duration": 7}
        ]
        return {
            "title": f"SCP-{scp_data['number']} | {scp_data['name']}",
            "scp_number": scp_data['number'],
            "scp_name": scp_data['name'],
            "author": scp_data['author'],
            "scenes": scenes,
            "scp_data": scp_data
        }

# ==================== ГЕНЕРАТОР КАДРОВ (с поиском) ====================
class ImageGenerator:
    def __init__(self, searcher: ImageSearcher):
        self.searcher = searcher
    
    def generate_frames(self, script: dict) -> list:
        frames = []
        total = len(script['scenes'])
        
        for i, scene in enumerate(script['scenes']):
            st.text(f"   🔍 Поиск кадра {i+1}/{total}: '{scene['keywords']}'...")
            
            # Ищем изображение
            urls = self.searcher.search(scene['keywords'], per_page=1)
            frame_path = f"{CONFIG['temp_dir']}/images/frame_{i:02d}.png"
            
            if urls:
                # Скачиваем первое изображение
                success = self.searcher.download_image(urls[0], frame_path)
                if not success:
                    # Если скачать не удалось, создаём заглушку
                    img = self.searcher.create_fallback_image(i + int(script['scp_number']))
                    img.save(frame_path)
            else:
                # Если поиск не дал результатов, создаём заглушку
                img = self.searcher.create_fallback_image(i + int(script['scp_number']))
                img.save(frame_path)
            
            frames.append({'path': frame_path, 'duration': scene.get('duration', 7)})
        
        return frames

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
        except Exception as e:
            st.warning(f"Ошибка озвучки: {e}")
            return None

# ==================== ВИДЕО-ГЕНЕРАТОР ====================
class VideoGenerator:
    def create_video(self, frames: list, audio_path: str, script: dict) -> str:
        clips = []
        for frame_data in frames:
            try:
                clip = ImageClip(frame_data['path'])
                clip = clip.resize(height=1280, width=720)
                clip = clip.set_duration(frame_data['duration'])
                clips.append(clip)
            except Exception as e:
                st.warning(f"Ошибка клипа: {e}")
                clip = ColorClip(size=(720, 1280), color=(240, 235, 225), duration=frame_data['duration'])
                clips.append(clip)
        
        if not clips:
            clip = ColorClip(size=(720, 1280), color=(240, 235, 225), duration=10)
            clips.append(clip)
        
        final = concatenate_videoclips(clips, method="compose")
        if audio_path and os.path.exists(audio_path) and os.path.getsize(audio_path) > 1000:
            try:
                audio = AudioFileClip(audio_path)
                if audio.duration > final.duration:
                    audio = audio.subclip(0, final.duration)
                final = final.set_audio(audio)
            except Exception as e:
                st.warning(f"Аудио: {e}")
        
        scp_num = script.get('scp_number', '000')
        scp_name = script.get('scp_name', 'unknown')
        safe_name = re.sub(r'[^\w\s-]', '', scp_name)
        safe_name = re.sub(r'[-\s]+', '_', safe_name)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"SCP-{scp_num}_{safe_name}_{timestamp}.mp4"
        output_path = os.path.join(CONFIG['output_dir'], filename)
        
        try:
            final.write_videofile(
                output_path,
                fps=24,
                codec='libx264',
                audio_codec='aac',
                threads=1,
                preset='ultrafast',
                bitrate='500k',
                verbose=False,
                logger=None
            )
        except Exception as e:
            st.error(f"Ошибка видео: {e}")
            txt_path = output_path.replace('.mp4', '.txt')
            with open(txt_path, 'w') as f:
                f.write(f"Ошибка: {e}")
            return txt_path
        
        return output_path

# ==================== ОСНОВНОЙ БОТ ====================
class SCPBot:
    def __init__(self, searcher: ImageSearcher):
        self.script_gen = ScriptGenerator()
        self.image_gen = ImageGenerator(searcher)
        self.voice_gen = VoiceGenerator()
        self.video_gen = VideoGenerator()
        self.videos_created = []
        self.status_messages = []
    
    def run(self, count=1):
        self.status_messages = []
        scp_list = SCP_DATABASE[:count]
        if not scp_list:
            self._add_status("❌ База SCP пуста")
            return []
        self._add_status(f"📚 Найдено SCP: {len(scp_list)}")
        for idx, scp in enumerate(scp_list, 1):
            self._add_status(f"\n📚 [{idx}/{len(scp_list)}] SCP-{scp['number']}: {scp['name']}")
            try:
                self._add_status("✍️ Сценарий...")
                script = self.script_gen.generate_script(scp)
                self._add_status("🔍 Поиск изображений в интернете...")
                frames = self.image_gen.generate_frames(script)
                self._add_status(f"   ✅ {len(frames)} кадров")
                self._add_status("🎤 Озвучка...")
                audio = self.voice_gen.generate_voice(script)
                if audio:
                    self._add_status("   ✅ Готово")
                else:
                    self._add_status("   ⚠️ Без звука")
                self._add_status("🎬 Видео...")
                video_path = self.video_gen.create_video(frames, audio, script)
                if os.path.exists(video_path) and os.path.getsize(video_path) > 1000:
                    size_mb = os.path.getsize(video_path) / 1024 / 1024
                    self._add_status(f"✅ ГОТОВО! {size_mb:.1f} MB")
                    self.videos_created.append(video_path)
                else:
                    self._add_status("⚠️ Ошибка")
                self._cleanup()
            except Exception as e:
                self._add_status(f"❌ Ошибка: {e}")
                import traceback
                self._add_status(traceback.format_exc())
        return self.videos_created
    
    def _add_status(self, msg: str):
        self.status_messages.append(msg)
        print(msg)
    
    def _cleanup(self):
        for folder in [f"{CONFIG['temp_dir']}/images", f"{CONFIG['temp_dir']}/audio"]:
            if os.path.exists(folder):
                shutil.rmtree(folder)
            Path(folder).mkdir(parents=True, exist_ok=True)

# ==================== STREAMLIT UI ====================
def main():
    st.set_page_config(page_title="SCP Video Bot (Internet Search)", page_icon="🌐", layout="wide")
    st.title("🌐 SCP Video Bot — поиск кадров в интернете")
    st.markdown("Автоматически ищет изображения по сценарию и собирает видео")
    st.markdown("---")
    
    # Инициализируем поисковик
    searcher = ImageSearcher(CONFIG['unsplash_key'])
    
    with st.sidebar:
        st.header("⚙️ Настройки")
        count = st.number_input("Количество видео:", min_value=1, max_value=3, value=1)
        st.markdown("---")
        st.info("🔍 Поиск через Unsplash (бесплатно)")
        if CONFIG['unsplash_key']:
            st.success("✅ Ключ установлен (5000 запросов/час)")
        else:
            st.warning("⚠️ Без ключа — 50 запросов/час")
            st.markdown("Получите бесплатный ключ на [unsplash.com](https://unsplash.com/developers)")
        st.info("⏱️ ~1-2 минуты на видео")
        st.markdown("---")
        if st.button("🗑️ Очистить временные файлы"):
            shutil.rmtree(CONFIG['temp_dir'], ignore_errors=True)
            shutil.rmtree(CONFIG['output_dir'], ignore_errors=True)
            for folder in [CONFIG['output_dir'], CONFIG['temp_dir'], f"{CONFIG['temp_dir']}/images", f"{CONFIG['temp_dir']}/audio"]:
                Path(folder).mkdir(parents=True, exist_ok=True)
            st.success("✅ Очищено!")
            st.rerun()
    
    col1, col2 = st.columns([2, 1])
    with col1:
        if st.button("🌐 Сгенерировать видео", type="primary", use_container_width=True):
            with st.spinner("Поиск и сборка видео..."):
                bot = SCPBot(searcher)
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
        st.subheader("📚 Доступные SCP")
        for scp in SCP_DATABASE[:8]:
            st.markdown(f"**SCP-{scp['number']}** - {scp['name']}")

if __name__ == "__main__":
    main()
