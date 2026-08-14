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
from bs4 import BeautifulSoup

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

# ==================== CLIP (для семантического поиска) ====================
CLIP_AVAILABLE = False
try:
    from transformers import CLIPProcessor, CLIPModel
    import torch
    CLIP_AVAILABLE = True
except ImportError:
    st.warning("⚠️ Библиотеки для CLIP не установлены. Семантический поиск отключён.")
    # Если нет, можно попробовать установить, но это не рекомендуется в рантайме,
    # поэтому просто предупреждаем.

# ==================== ФИКС ДЛЯ ANTIALIAS ====================
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

# ==================== КОНФИГУРАЦИЯ ====================
CONFIG = {
    'output_dir': './videos',
    'temp_dir': './temp'
}

for folder in [CONFIG['output_dir'], CONFIG['temp_dir'], f"{CONFIG['temp_dir']}/images", f"{CONFIG['temp_dir']}/audio"]:
    Path(folder).mkdir(parents=True, exist_ok=True)

# ==================== БАЗА SCP ====================
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

# ==================== ОСНОВНЫЕ ИЗОБРАЖЕНИЯ (СМЫСЛОВЫЕ) ====================
# Это изображения, которые ТОЧНО соответствуют SCP (приоритет выше поиска)
PRIMARY_IMAGES = {
    "173": [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/SCP-173_Photo.jpg/800px-SCP-173_Photo.jpg"
    ],
    "049": [
        "https://static.wikia.nocookie.net/scp-foundation/images/3/38/SCP-049.jpg"
    ],
    "096": [
        "https://static.wikia.nocookie.net/scp-foundation/images/0/09/SCP-096.jpg"
    ],
    "106": [
        "https://static.wikia.nocookie.net/scp-foundation/images/8/8a/SCP-106.jpg"
    ],
    "682": [
        "https://static.wikia.nocookie.net/scp-foundation/images/5/5a/SCP-682.jpg"
    ],
    "999": [
        "https://static.wikia.nocookie.net/scp-foundation/images/6/68/SCP-999.jpg"
    ],
    "087": [
        "https://static.wikia.nocookie.net/scp-foundation/images/1/19/SCP-087.jpg"
    ],
    "3000": [
        "https://static.wikia.nocookie.net/scp-foundation/images/3/3d/SCP-3000.jpg"
    ]
}

# ==================== ПОИСК ИЗОБРАЖЕНИЙ В ИНТЕРНЕТЕ (Bing) ====================
class BingImageSearcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def search(self, query: str, max_results: int = 10) -> List[str]:
        urls = []
        try:
            search_url = f"https://www.bing.com/images/search?q={query.replace(' ', '+')}&form=HDRSC2&first=1&count={max_results*2}"
            response = self.session.get(search_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Ищем изображения
                for img in soup.find_all('img', class_='mimg'):
                    src = img.get('src')
                    if src and src.startswith('http'):
                        urls.append(src)
                # Если не нашли, пробуем другие атрибуты
                if not urls:
                    for img in soup.find_all('img', attrs={'data-src': True}):
                        src = img['data-src']
                        if src.startswith('http'):
                            urls.append(src)
        except Exception as e:
            st.warning(f"Ошибка Bing-поиска: {e}")
        return urls[:max_results]

# ==================== СЕМАНТИЧЕСКОЕ РАНЖИРОВАНИЕ (CLIP) ====================
class SemanticRanker:
    def __init__(self):
        self.model = None
        self.processor = None
        self.device = "cpu"
        self.ready = False
        if CLIP_AVAILABLE:
            try:
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
                self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(self.device)
                self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
                self.ready = True
                st.info(f"✅ CLIP загружен на {self.device.upper()}")
            except Exception as e:
                st.error(f"❌ Ошибка загрузки CLIP: {e}")
                self.ready = False
        else:
            st.warning("⚠️ CLIP не доступен. Будет использован обычный поиск.")
    
    def rank_images(self, query: str, image_urls: List[str], top_k: int = 1) -> List[str]:
        """Возвращает URL изображений, отсортированные по релевантности к запросу."""
        if not self.ready or not image_urls:
            return image_urls[:top_k] if image_urls else []
        
        # Загружаем изображения
        images = []
        valid_urls = []
        for url in image_urls[:10]:  # не более 10 для скорости
            try:
                response = requests.get(url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
                if response.status_code == 200 and 'image' in response.headers.get('content-type', ''):
                    img = Image.open(io.BytesIO(response.content)).convert('RGB')
                    images.append(img)
                    valid_urls.append(url)
            except Exception as e:
                continue
        
        if not images:
            return image_urls[:top_k]
        
        # Подготовка данных для CLIP
        inputs = self.processor(
            text=[query] * len(images),
            images=images,
            return_tensors="pt",
            padding=True
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits_per_image = outputs.logits_per_image  # (n_images, n_texts)
            scores = logits_per_image.squeeze().cpu().numpy()
        
        # Сортировка по убыванию сходства
        sorted_indices = scores.argsort()[::-1]
        sorted_urls = [valid_urls[i] for i in sorted_indices[:top_k]]
        return sorted_urls

# ==================== ГЕНЕРАТОР СЦЕНАРИЕВ ====================
class ScriptGenerator:
    def generate_script(self, scp_data: dict) -> dict:
        scenes = [
            {
                "keywords": f"SCP-{scp_data['number']} {scp_data['name']} horror dark atmosphere",
                "voice_text": f"Я нашёл это в старом архиве. SCP-{scp_data['number']} - {scp_data['name']}.",
                "duration": 7
            },
            {
                "keywords": f"SCP-{scp_data['number']} {scp_data['name']} closeup detailed",
                "voice_text": f"{scp_data['text']}",
                "duration": 8
            },
            {
                "keywords": f"SCP-{scp_data['number']} creepy movement",
                "voice_text": "Оно двигается. Не как человек. Слишком плавно.",
                "duration": 7
            },
            {
                "keywords": f"SCP-{scp_data['number']} shadows horror",
                "voice_text": "Я слышал голоса. Они звали меня по имени.",
                "duration": 7
            },
            {
                "keywords": f"SCP-{scp_data['number']} scary eyes",
                "voice_text": "Оно знает, что я здесь. Оно смотрит прямо на меня.",
                "duration": 7
            },
            {
                "keywords": f"SCP-{scp_data['number']} behind you",
                "voice_text": "Я закрыл глаза. Но когда открыл... оно стояло прямо за мной.",
                "duration": 7
            }
        ]
        return {
            "title": f"SCP-{scp_data['number']} | {scp_data['name']}",
            "scp_number": scp_data['number'],
            "scp_name": scp_data['name'],
            "author": scp_data['author'],
            "scenes": scenes,
            "scp_data": scp_data
        }

# ==================== ГЕНЕРАТОР КАДРОВ ====================
class ImageGenerator:
    def __init__(self, ranker: SemanticRanker):
        self.ranker = ranker
        self.bing = BingImageSearcher()
        self.fallback = PRIMARY_IMAGES
    
    def generate_frames(self, script: dict) -> list:
        frames = []
        total = len(script['scenes'])
        scp_num = script['scp_number']
        
        # Основные изображения для SCP (если есть)
        primary_urls = self.fallback.get(scp_num, [])
        
        for i, scene in enumerate(script['scenes']):
            frame_path = f"{CONFIG['temp_dir']}/images/frame_{i:02d}.png"
            
            # 1. Пытаемся использовать основное изображение (точное)
            if primary_urls:
                url = primary_urls[i % len(primary_urls)]
                st.text(f"   🖼️ Основное изображение SCP-{scp_num} (кадр {i+1}/{total})")
                if self._download_image(url, frame_path):
                    frames.append({'path': frame_path, 'duration': scene['duration']})
                    continue
            
            # 2. Семантический поиск через Bing + CLIP
            st.text(f"   🧠 Семантический поиск: '{scene['keywords']}'...")
            # Сначала получаем несколько URL через Bing
            raw_urls = self.bing.search(scene['keywords'], max_results=6)
            if raw_urls:
                # Ранжируем через CLIP
                ranked_urls = self.ranker.rank_images(scene['keywords'], raw_urls, top_k=1)
                if ranked_urls:
                    if self._download_image(ranked_urls[0], frame_path):
                        frames.append({'path': frame_path, 'duration': scene['duration']})
                        continue
            
            # 3. Если ничего не сработало — создаём заглушку
            st.text(f"   🎨 Заглушка для кадра {i+1}")
            img = self._create_fallback_image(i + int(scp_num))
            img.save(frame_path)
            frames.append({'path': frame_path, 'duration': scene['duration']})
        
        return frames
    
    @staticmethod
    def _download_image(url: str, save_path: str) -> bool:
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200 and 'image' in response.headers.get('content-type', ''):
                img = Image.open(io.BytesIO(response.content))
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                w, h = img.size
                if w > h:
                    crop = h
                    left = (w - crop) // 2
                    img = img.crop((left, 0, left + crop, h))
                img = img.resize((720, 1280), Image.LANCZOS)
                img.save(save_path)
                return True
        except Exception as e:
            print(f"Ошибка скачивания: {e}")
        return False
    
    @staticmethod
    def _create_fallback_image(seed: int) -> Image.Image:
        width, height = 720, 1280
        img = Image.new('RGB', (width, height), color=(240, 235, 225))
        draw = ImageDraw.Draw(img)
        random.seed(seed)
        for _ in range(1000):
            x = random.randint(0, width-1)
            y = random.randint(0, height-1)
            br = random.randint(200, 240)
            draw.point((x, y), fill=(br, br-5, br-10))
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
    def __init__(self, ranker: SemanticRanker):
        self.script_gen = ScriptGenerator()
        self.image_gen = ImageGenerator(ranker)
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
                self._add_status("🖼️ Генерация кадров (семантический поиск)...")
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
    st.set_page_config(page_title="SCP Video Bot (Semantic AI)", page_icon="🧠", layout="wide")
    st.title("🧠 SCP Video Bot — семантический поиск изображений")
    st.markdown("Использует CLIP для поиска самых осмысленных кадров по сценарию")
    st.markdown("---")
    
    # Инициализация семантического ранкера
    ranker = SemanticRanker()
    
    with st.sidebar:
        st.header("⚙️ Настройки")
        count = st.number_input("Количество видео:", min_value=1, max_value=3, value=1)
        st.markdown("---")
        if ranker.ready:
            st.success("✅ Семантический поиск активен (CLIP)")
        else:
            st.warning("⚠️ Работает только поиск по ключевым словам (без CLIP)")
        st.info("🖼️ Приоритет: точные изображения SCP → семантический поиск → заглушки")
        st.info("⏱️ ~2-3 минуты на видео")
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
        if st.button("🧠 Сгенерировать видео", type="primary", use_container_width=True):
            with st.spinner("Поиск и сборка видео..."):
                bot = SCPBot(ranker)
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
