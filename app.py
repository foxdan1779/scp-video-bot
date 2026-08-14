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

CLIP_AVAILABLE = False
try:
    from transformers import CLIPProcessor, CLIPModel
    import torch
    CLIP_AVAILABLE = True
except ImportError:
    pass

# ==================== ФИКС ДЛЯ ANTIALIAS ====================
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

# ==================== КОНФИГУРАЦИЯ ====================
CONFIG = {
    'output_dir': './videos',
    'temp_dir': './temp'
}

# Создаём папки, если их нет
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

# ==================== ОСНОВНЫЕ ИЗОБРАЖЕНИЯ (для быстрого старта) ====================
PRIMARY_IMAGES = {
    "173": ["https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/SCP-173_Photo.jpg/800px-SCP-173_Photo.jpg"],
    "049": ["https://static.wikia.nocookie.net/scp-foundation/images/3/38/SCP-049.jpg"],
    "096": ["https://static.wikia.nocookie.net/scp-foundation/images/0/09/SCP-096.jpg"],
    "106": ["https://static.wikia.nocookie.net/scp-foundation/images/8/8a/SCP-106.jpg"],
    "682": ["https://static.wikia.nocookie.net/scp-foundation/images/5/5a/SCP-682.jpg"],
    "999": ["https://static.wikia.nocookie.net/scp-foundation/images/6/68/SCP-999.jpg"],
    "087": ["https://static.wikia.nocookie.net/scp-foundation/images/1/19/SCP-087.jpg"],
    "3000": ["https://static.wikia.nocookie.net/scp-foundation/images/3/3d/SCP-3000.jpg"]
}

# ==================== ПОИСК ИЗОБРАЖЕНИЙ (Bing с улучшенными запросами) ====================
class BingImageSearcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
    
    def search(self, query: str, max_results: int = 6) -> List[str]:
        """Ищет изображения с добавлением контекста SCP"""
        # Улучшаем запрос, добавляя ключевые слова
        enhanced_query = f"{query} SCP Foundation horror art"
        search_url = f"https://www.bing.com/images/search?q={enhanced_query.replace(' ', '+')}&form=HDRSC2&first=1&count={max_results*2}"
        urls = []
        try:
            response = self.session.get(search_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                for img in soup.find_all('img', class_='mimg'):
                    src = img.get('src')
                    if src and src.startswith('http'):
                        urls.append(src)
                if not urls:
                    for img in soup.find_all('img', attrs={'data-src': True}):
                        src = img['data-src']
                        if src.startswith('http'):
                            urls.append(src)
        except Exception as e:
            st.warning(f"Ошибка Bing-поиска: {e}")
        return urls[:max_results]

    def search_wiki(self, scp_number: str) -> List[str]:
        """Ищет изображения на вики SCP (прямые ссылки)"""
        urls = []
        try:
            wiki_url = f"https://scp-wiki.wikidot.com/scp-{scp_number}"
            response = self.session.get(wiki_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                for img in soup.find_all('img'):
                    src = img.get('src')
                    if src and src.startswith('http'):
                        # Фильтруем только изображения, содержащие 'thumb' или 'large'
                        if 'thumb' in src or 'large' in src:
                            urls.append(src)
        except:
            pass
        return urls[:3]

# ==================== СЕМАНТИЧЕСКИЙ РАНКЕР (CLIP) ====================
class SemanticRanker:
    def __init__(self):
        self.model = None
        self.processor = None
        self.device = "cpu"
        self.ready = False
        if CLIP_AVAILABLE:
            try:
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
                # Используем более точную модель
                self.model = CLIPModel.from_pretrained("laion/CLIP-ViT-B-32-laion2B-s34B-b79K").to(self.device)
                self.processor = CLIPProcessor.from_pretrained("laion/CLIP-ViT-B-32-laion2B-s34B-b79K")
                self.ready = True
            except Exception as e:
                st.warning(f"Не удалось загрузить CLIP: {e}")
                self.ready = False
    
    def rank_images(self, query: str, image_urls: List[str], top_k: int = 4) -> List[str]:
        if not self.ready or not image_urls:
            return image_urls[:top_k]
        images = []
        valid_urls = []
        for url in image_urls[:10]:
            try:
                response = requests.get(url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
                if response.status_code == 200 and 'image' in response.headers.get('content-type', ''):
                    img = Image.open(io.BytesIO(response.content)).convert('RGB')
                    images.append(img)
                    valid_urls.append(url)
            except:
                continue
        if not images:
            return image_urls[:top_k]
        inputs = self.processor(text=[query] * len(images), images=images, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = self.model(**inputs)
            scores = outputs.logits_per_image.squeeze().cpu().numpy()
        sorted_indices = scores.argsort()[::-1]
        sorted_urls = [valid_urls[i] for i in sorted_indices[:top_k]]
        return sorted_urls

# ==================== ЗАГРУЗЧИК И ОБРАБОТЧИК ИЗОБРАЖЕНИЙ ====================
def download_image(url: str) -> Optional[Image.Image]:
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200 and 'image' in response.headers.get('content-type', ''):
            img = Image.open(io.BytesIO(response.content))
            if img.mode != 'RGB':
                img = img.convert('RGB')
            return img
    except:
        return None
    return None

def resize_to_portrait(img: Image.Image) -> Image.Image:
    w, h = img.size
    if w > h:
        crop = h
        left = (w - crop) // 2
        img = img.crop((left, 0, left + crop, h))
    img = img.resize((720, 1280), Image.LANCZOS)
    return img

def create_fallback_image(seed: int) -> Image.Image:
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

def prepare_image_display(img: Image.Image) -> io.BytesIO:
    """Конвертирует PIL Image в BytesIO для отображения без сохранения на диск"""
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf

# ==================== ГЕНЕРАТОР СЦЕНАРИЕВ ====================
def generate_script(scp_data: dict) -> dict:
    scenes = [
        {"keywords": f"SCP-{scp_data['number']} {scp_data['name']} horror dark atmosphere", "voice_text": f"Я нашёл это в старом архиве. SCP-{scp_data['number']} - {scp_data['name']}.", "duration": 7},
        {"keywords": f"SCP-{scp_data['number']} {scp_data['name']} closeup detailed", "voice_text": f"{scp_data['text']}", "duration": 8},
        {"keywords": f"SCP-{scp_data['number']} creepy movement", "voice_text": "Оно двигается. Не как человек. Слишком плавно.", "duration": 7},
        {"keywords": f"SCP-{scp_data['number']} shadows horror", "voice_text": "Я слышал голоса. Они звали меня по имени.", "duration": 7},
        {"keywords": f"SCP-{scp_data['number']} scary eyes", "voice_text": "Оно знает, что я здесь. Оно смотрит прямо на меня.", "duration": 7},
        {"keywords": f"SCP-{scp_data['number']} behind you", "voice_text": "Я закрыл глаза. Но когда открыл... оно стояло прямо за мной.", "duration": 7}
    ]
    return {
        "title": f"SCP-{scp_data['number']} | {scp_data['name']}",
        "scp_number": scp_data['number'],
        "scp_name": scp_data['name'],
        "author": scp_data['author'],
        "scenes": scenes,
        "scp_data": scp_data
    }

# ==================== ОЗВУЧКА ====================
async def generate_voice(text: str) -> str:
    output_path = f"{CONFIG['temp_dir']}/audio/voice.mp3"
    try:
        communicate = edge_tts.Communicate(text, 'ru-RU-DmitryNeural', rate="-10%", pitch="-5Hz")
        await communicate.save(output_path)
        return output_path
    except:
        return None

# ==================== ВИДЕО-СБОРЩИК ====================
def create_video(frames: list, audio_path: str, script: dict) -> str:
    clips = []
    for frame_data in frames:
        try:
            clip = ImageClip(frame_data['path'])
            clip = clip.resize(height=1280, width=720)
            clip = clip.set_duration(frame_data['duration'])
            clips.append(clip)
        except:
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
        final.write_videofile(output_path, fps=24, codec='libx264', audio_codec='aac', threads=1, preset='ultrafast', bitrate='500k', verbose=False, logger=None)
        return output_path
    except:
        return None

# ==================== ИНИЦИАЛИЗАЦИЯ СОСТОЯНИЯ ====================
def init_session_state():
    if 'step' not in st.session_state:
        st.session_state.step = 'select_scp'
    if 'scp_choice' not in st.session_state:
        st.session_state.scp_choice = None
    if 'script' not in st.session_state:
        st.session_state.script = None
    if 'scene_selections' not in st.session_state:
        st.session_state.scene_selections = {}  # ключ: индекс сцены, значение: путь к выбранному изображению
    if 'scene_images' not in st.session_state:
        st.session_state.scene_images = {}      # ключ: индекс сцены, значение: список (BytesIO, PIL.Image)
    if 'audio_path' not in st.session_state:
        st.session_state.audio_path = None
    if 'video_path' not in st.session_state:
        st.session_state.video_path = None
    if 'ranker' not in st.session_state:
        st.session_state.ranker = SemanticRanker()
        st.session_state.bing = BingImageSearcher()
    if 'current_scene' not in st.session_state:
        st.session_state.current_scene = 0

# ==================== ОСНОВНОЙ ПОТОК ====================
def main():
    st.set_page_config(page_title="SCP Video Creator", page_icon="🎬", layout="wide")
    st.title("🎬 SCP Video Creator — пошаговое создание с выбором кадров")
    st.markdown("Выберите SCP, подтвердите сценарий, подберите изображения для каждой сцены (можно загрузить свои)")
    st.markdown("---")
    
    init_session_state()
    
    # ==================== ШАГ 1: ВЫБОР SCP ====================
    if st.session_state.step == 'select_scp':
        st.subheader("1️⃣ Выберите SCP")
        col1, col2 = st.columns([2, 1])
        with col1:
            scp_names = [f"SCP-{s['number']}: {s['name']}" for s in SCP_DATABASE]
            selected = st.selectbox("Доступные SCP:", scp_names, index=0)
            idx = scp_names.index(selected)
            scp = SCP_DATABASE[idx]
            st.write(f"**Автор:** {scp['author']}")
            st.write(f"**Описание:** {scp['text']}")
        with col2:
            if st.button("✅ Выбрать и создать сценарий", use_container_width=True):
                st.session_state.scp_choice = scp
                st.session_state.script = generate_script(scp)
                # Сбрасываем предыдущие выборы
                st.session_state.scene_selections = {}
                st.session_state.scene_images = {}
                st.session_state.current_scene = 0
                st.session_state.audio_path = None
                st.session_state.video_path = None
                st.session_state.step = 'confirm_script'
                st.rerun()
    
    # ==================== ШАГ 2: ПОДТВЕРЖДЕНИЕ СЦЕНАРИЯ ====================
    elif st.session_state.step == 'confirm_script':
        st.subheader("2️⃣ Проверьте сценарий")
        script = st.session_state.script
        st.write(f"**Название:** {script['title']}")
        st.write(f"**Автор:** {script['author']}")
        st.write("**Сцены:**")
        for i, scene in enumerate(script['scenes']):
            st.write(f"  {i+1}. {scene['voice_text']} (длительность: {scene['duration']}с)")
        st.write("---")
        col1, col2, col3 = st.columns([1,1,2])
        with col1:
            if st.button("🔄 Перегенерировать сценарий", use_container_width=True):
                st.session_state.script = generate_script(st.session_state.scp_choice)
                st.rerun()
        with col2:
            if st.button("✅ Принять сценарий", use_container_width=True):
                st.session_state.current_scene = 0
                st.session_state.step = 'select_images'
                st.rerun()
        with col3:
            if st.button("⬅️ Назад к выбору SCP", use_container_width=True):
                st.session_state.step = 'select_scp'
                st.rerun()
    
    # ==================== ШАГ 3: ВЫБОР ИЗОБРАЖЕНИЙ ДЛЯ КАЖДОЙ СЦЕНЫ ====================
    elif st.session_state.step == 'select_images':
        script = st.session_state.script
        scenes = script['scenes']
        total = len(scenes)
        idx = st.session_state.current_scene
        
        if idx < total:
            st.subheader(f"3️⃣ Выберите изображение для сцены {idx+1}/{total}")
            scene = scenes[idx]
            st.write(f"**Текст:** {scene['voice_text']}")
            st.write(f"**Ключевые слова:** {scene['keywords']}")
            
            # Блок загрузки своего изображения (всегда доступен)
            st.write("---")
            st.write("**📤 Загрузите своё изображение (или выберите из предложенных ниже):**")
            uploaded_file = st.file_uploader(f"Загрузить изображение для сцены {idx+1}", type=['png', 'jpg', 'jpeg', 'webp'], key=f"upload_{idx}")
            if uploaded_file is not None:
                try:
                    img = Image.open(uploaded_file)
                    img = resize_to_portrait(img)
                    path = f"{CONFIG['temp_dir']}/images/scene_{idx}_user.png"
                    img.save(path)
                    st.session_state.scene_selections[idx] = path
                    st.success("✅ Изображение загружено!")
                    st.session_state.current_scene += 1
                    # Удаляем временные изображения из памяти, если были
                    if idx in st.session_state.scene_images:
                        del st.session_state.scene_images[idx]
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка загрузки: {e}")
            
            st.write("---")
            st.write("**🔍 Или найдите изображения по ключевым словам:**")
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("🔍 Найти изображения для этой сцены", use_container_width=True):
                    with st.spinner("Поиск..."):
                        # Собираем URL из нескольких источников
                        urls = []
                        # 1. Основные изображения SCP
                        primary = PRIMARY_IMAGES.get(script['scp_number'], [])
                        urls.extend(primary)
                        # 2. Вики SCP
                        wiki_urls = st.session_state.bing.search_wiki(script['scp_number'])
                        urls.extend(wiki_urls)
                        # 3. Bing с улучшенным запросом
                        bing_urls = st.session_state.bing.search(scene['keywords'], max_results=6)
                        urls.extend(bing_urls)
                        # Ранжируем через CLIP
                        if st.session_state.ranker.ready and urls:
                            ranked = st.session_state.ranker.rank_images(scene['keywords'], urls, top_k=4)
                        else:
                            ranked = urls[:4]
                        # Загружаем изображения в память (BytesIO) без сохранения на диск
                        images = []
                        for url in ranked:
                            img = download_image(url)
                            if img:
                                img = resize_to_portrait(img)
                                images.append(img)
                        if not images:
                            # Заглушка
                            img = create_fallback_image(idx + int(script['scp_number']))
                            images.append(img)
                        # Сохраняем список PIL Image в сессии (не сохраняем на диск)
                        st.session_state.scene_images[idx] = images
                        st.rerun()
            with col2:
                # Кнопка пропуска (использовать заглушку)
                if st.button("⏭️ Пропустить (заглушка)", use_container_width=True):
                    img = create_fallback_image(idx + int(script['scp_number']))
                    path = f"{CONFIG['temp_dir']}/images/scene_{idx}_fallback.png"
                    img.save(path)
                    st.session_state.scene_selections[idx] = path
                    st.session_state.current_scene += 1
                    if idx in st.session_state.scene_images:
                        del st.session_state.scene_images[idx]
                    st.rerun()
            
            # Отображение найденных изображений (если есть) с возможностью выбора
            if idx in st.session_state.scene_images and st.session_state.scene_images[idx]:
                images = st.session_state.scene_images[idx]
                st.write("**Выберите изображение (кликните на вариант):**")
                cols = st.columns(min(len(images), 4))
                selected_idx = None
                for i, img in enumerate(images):
                    col = cols[i % len(cols)]
                    with col:
                        # Показываем изображение из памяти
                        buf = prepare_image_display(img)
                        st.image(buf, use_container_width=True)
                        if st.button(f"✅ Выбрать вариант {i+1}", key=f"choose_{idx}_{i}"):
                            selected_idx = i
                if selected_idx is not None:
                    img = images[selected_idx]
                    path = f"{CONFIG['temp_dir']}/images/scene_{idx}_selected.png"
                    img.save(path)
                    st.session_state.scene_selections[idx] = path
                    # Очищаем временные данные, чтобы освободить память
                    del st.session_state.scene_images[idx]
                    st.session_state.current_scene += 1
                    st.rerun()
            else:
                st.info("Нажмите 'Найти изображения' для получения вариантов.")
        else:
            # Все сцены выбраны
            st.session_state.step = 'confirm_images'
            st.rerun()
    
    # ==================== ШАГ 4: ПРОВЕРКА ВСЕХ КАДРОВ ====================
    elif st.session_state.step == 'confirm_images':
        st.subheader("4️⃣ Проверьте все выбранные кадры")
        script = st.session_state.script
        scenes = script['scenes']
        # Проверяем, все ли сцены выбраны
        all_selected = all(i in st.session_state.scene_selections for i in range(len(scenes)))
        if not all_selected:
            st.warning("Не все сцены выбраны. Вернитесь к выбору.")
        else:
            cols = st.columns(3)
            for i, scene in enumerate(scenes):
                col = cols[i % 3]
                with col:
                    path = st.session_state.scene_selections[i]
                    img = Image.open(path)
                    st.image(img, use_container_width=True)
                    st.write(f"**Сцена {i+1}:** {scene['voice_text'][:50]}...")
            st.write("---")
            col1, col2, col3 = st.columns([1,1,2])
            with col1:
                if st.button("⬅️ Вернуться к выбору", use_container_width=True):
                    st.session_state.step = 'select_images'
                    st.rerun()
            with col2:
                if all_selected and st.button("✅ Подтвердить все кадры", use_container_width=True):
                    st.session_state.step = 'generate_audio'
                    st.rerun()
            with col3:
                if st.button("🔄 Перегенерировать сценарий", use_container_width=True):
                    st.session_state.script = generate_script(st.session_state.scp_choice)
                    st.session_state.step = 'confirm_script'
                    st.rerun()
    
    # ==================== ШАГ 5: ОЗВУЧКА ====================
    elif st.session_state.step == 'generate_audio':
        st.subheader("5️⃣ Генерация озвучки")
        script = st.session_state.script
        full_text = ". ".join([scene['voice_text'] for scene in script['scenes']])
        st.write("**Текст для озвучки:**")
        st.text_area("", full_text, height=150)
        if st.button("🎤 Сгенерировать озвучку", use_container_width=True):
            with st.spinner("Генерация аудио..."):
                audio_path = asyncio.run(generate_voice(full_text))
                if audio_path:
                    st.session_state.audio_path = audio_path
                    st.success("✅ Озвучка готова!")
                    st.session_state.step = 'build_video'
                    st.rerun()
                else:
                    st.error("Ошибка генерации озвучки")
        if st.button("⬅️ Назад к кадрам", use_container_width=True):
            st.session_state.step = 'confirm_images'
            st.rerun()
    
    # ==================== ШАГ 6: СБОРКА ВИДЕО ====================
    elif st.session_state.step == 'build_video':
        st.subheader("6️⃣ Сборка видео")
        script = st.session_state.script
        frames = []
        for i, scene in enumerate(script['scenes']):
            path = st.session_state.scene_selections.get(i)
            if not path:
                # Заглушка
                img = create_fallback_image(i + int(script['scp_number']))
                path = f"{CONFIG['temp_dir']}/images/scene_{i}_fallback.png"
                img.save(path)
            frames.append({'path': path, 'duration': scene['duration']})
        
        if st.button("🎬 Собрать видео", use_container_width=True):
            with st.spinner("Сборка видео..."):
                video_path = create_video(frames, st.session_state.audio_path, script)
                if video_path:
                    st.session_state.video_path = video_path
                    st.success("✅ Видео готово!")
                    st.session_state.step = 'download'
                    st.rerun()
                else:
                    st.error("Ошибка сборки видео")
        if st.button("⬅️ Назад к озвучке", use_container_width=True):
            st.session_state.step = 'generate_audio'
            st.rerun()
    
    # ==================== ШАГ 7: СКАЧИВАНИЕ ====================
    elif st.session_state.step == 'download':
        st.subheader("🎉 Видео готово!")
        video_path = st.session_state.video_path
        if video_path and os.path.exists(video_path):
            st.video(video_path)
            with open(video_path, 'rb') as f:
                video_bytes = f.read()
            st.download_button(
                label="📥 Скачать видео",
                data=video_bytes,
                file_name=os.path.basename(video_path),
                mime='video/mp4'
            )
        st.write("---")
        if st.button("🔄 Начать заново", use_container_width=True):
            # Сброс сессии
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

if __name__ == "__main__":
    main()
