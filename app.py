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
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps
import numpy as np
import io

# ==================== ФИКС ДЛЯ ANTIALIAS ====================
from PIL import Image as PILImage
if not hasattr(PILImage, 'ANTIALIAS'):
    PILImage.ANTIALIAS = PILImage.LANCZOS
    print("✅ Фикс ANTIALIAS применён!")

# ==================== УСТАНОВКА ЗАВИСИМОСТЕЙ ====================
try:
    from moviepy.editor import *
except ImportError:
    subprocess.check_call(['pip', 'install', 'moviepy'])
    from moviepy.editor import *

try:
    import edge_tts
except ImportError:
    subprocess.check_call(['pip', 'install', 'edge-tts'])
    import edge_tts

# ==================== ВСТРОЕННАЯ БАЗА SCP ====================
SCP_DATABASE = [
    {
        "number": "173",
        "name": "Скульптура",
        "author": "М. Роджерс",
        "appearance": "Бетонная статуя с лицом в виде красного иероглифа, без рук и ног",
        "text": "SCP-173 - это статуя из бетона и арматуры. Она неподвижна, когда на неё смотрят."
    },
    {
        "number": "049",
        "name": "Чумной доктор",
        "author": "Габриэль",
        "appearance": "Гуманоид в средневековом костюме чумного доктора с клювовидной маской",
        "text": "SCP-049 - гуманоид, который считает себя врачом. Он пытается 'лечить' людей."
    },
    {
        "number": "096",
        "name": "Застенчивый парень",
        "author": "Доктор Дэн",
        "appearance": "Высокое, неестественно худое существо с белой кожей и огромными челюстями",
        "text": "SCP-096 - существо, которое не переносит, когда на него смотрят."
    },
    {
        "number": "106",
        "name": "Старый человек",
        "author": "Доктор Гирс",
        "appearance": "Гуманоид с гниющей кожей, покрытой коррозией, в старом военном обмундировании",
        "text": "SCP-106 - гуманоид, который может проходить сквозь твёрдые материалы."
    },
    {
        "number": "682",
        "name": "Трудный для уничтожения ящер",
        "author": "Доктор Гирс",
        "appearance": "Крупное рептилоидное существо с невероятной регенерацией, покрытое шрамами",
        "text": "SCP-682 - огромная рептилия, которая не умирает. Фонд пытался уничтожить её сотнями способов."
    },
    {
        "number": "999",
        "name": "Щекочущий монстр",
        "author": "Доктор Кейн",
        "appearance": "Желейное существо оранжевого цвета, похожее на слизь, с улыбающимся лицом",
        "text": "SCP-999 - дружелюбное существо, которое щекочет людей и вызывает у них эйфорию."
    },
    {
        "number": "087",
        "name": "Лестница в подвал",
        "author": "Доктор У. Уилсон",
        "appearance": "Тёмная лестница, ведущая в подвал, на которой слышны шаги и плач ребёнка",
        "text": "SCP-087 - бесконечная лестница. На каждом уровне слышен плач ребёнка."
    },
    {
        "number": "3000",
        "name": "Анаджвари",
        "author": "Доктор В. Д.",
        "appearance": "Огромный морской змей с раздвоенным хвостом, обитающий на дне океана",
        "text": "SCP-3000 - гигантский змей, который питается воспоминаниями людей."
    }
]

# ==================== КОНФИГУРАЦИЯ ====================
CONFIG = {
    'output_dir': './videos',
    'temp_dir': './temp'
}

for folder in [CONFIG['output_dir'], CONFIG['temp_dir'], f"{CONFIG['temp_dir']}/images", f"{CONFIG['temp_dir']}/audio"]:
    Path(folder).mkdir(parents=True, exist_ok=True)

# ==================== UNSPLASH API (БЕСПЛАТНО) ====================
class UnsplashBackgrounds:
    """Скачивает реальные фоны из Unsplash"""
    
    # Бесплатные изображения для фонов (прямые ссылки на изображения)
    BACKGROUNDS = [
        "https://images.unsplash.com/photo-1519120944692-1a8d8cfc107f?w=720&h=1280&fit=crop",  # тёмный коридор
        "https://images.unsplash.com/photo-1546013868-3ae4def4b1f9?w=720&h=1280&fit=crop",  # старая лестница
        "https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?w=720&h=1280&fit=crop",  # тёмная комната
        "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?w=720&h=1280&fit=crop",  # тёмный коридор
        "https://images.unsplash.com/photo-1519681393784-d120267933ba?w=720&h=1280&fit=crop",  # ночь
        "https://images.unsplash.com/photo-1532272691065-bcfd22a0ab07?w=720&h=1280&fit=crop",  # заброшенное здание
        "https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=720&h=1280&fit=crop",  # тёмное поле
        "https://images.unsplash.com/photo-1487621167305-5d248087c724?w=720&h=1280&fit=crop",  # тёмный лес
        "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?w=720&h=1280&fit=crop",  # туман
        "https://images.unsplash.com/photo-1501785888041-af3ef285b470?w=720&h=1280&fit=crop",  # тёмное озеро
    ]
    
    @classmethod
    def get_background(cls, seed: int) -> Image.Image:
        """Получает случайный фон из Unsplash"""
        url = cls.BACKGROUNDS[seed % len(cls.BACKGROUNDS)]
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                img = Image.open(io.BytesIO(response.content))
                # Приводим к нужному размеру
                img = img.resize((720, 1280), PILImage.LANCZOS)
                return img
        except Exception as e:
            print(f"Ошибка загрузки фона: {e}")
        
        # Если не загрузилось - создаём тёмный фон
        return Image.new('RGB', (720, 1280), color=(8, 8, 12))

# ==================== ГЕНЕРАТОР СЦЕНАРИЕВ ====================
class ScriptGenerator:
    def generate_script(self, scp_data: dict) -> dict:
        scenes = [
            {
                "voice_text": f"Я нашёл это в старом архиве. SCP-{scp_data['number']} - {scp_data['name']}. Оно не должно было попасть ко мне.",
                "duration": 7
            },
            {
                "voice_text": f"Исследователи говорят, что {scp_data['text'][:60]}... Это слишком древнее. Слишком злое.",
                "duration": 7
            },
            {
                "voice_text": "Оно двигается. Не как человек. Слишком плавно. Слишком неестественно.",
                "duration": 7
            },
            {
                "voice_text": "Я слышал голоса. Они звали меня по имени. Но я был один.",
                "duration": 7
            },
            {
                "voice_text": "Оно знает, что я здесь. Оно смотрит прямо на меня. И улыбается.",
                "duration": 7
            },
            {
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

# ==================== ГЕНЕРАТОР КАРТИНОК С ФОНАМИ ====================
class ImageGenerator:
    def generate_frames(self, script: dict) -> list:
        frames = []
        scp_data = script['scp_data']
        
        for i, scene in enumerate(script['scenes']):
            frame_path = f"{CONFIG['temp_dir']}/images/frame_{i:02d}.png"
            self._create_realistic_image(frame_path, i, scp_data)
            frames.append({'path': frame_path, 'duration': scene.get('duration', 7)})
        return frames
    
    def _create_realistic_image(self, path: str, seed: int, scp_data: dict):
        """Создаёт изображение с реальным фоном и нарисованным персонажем"""
        
        width, height = 720, 1280
        
        # 1. Скачиваем реальный фон
        img = UnsplashBackgrounds.get_background(seed + int(scp_data['number']))
        img = img.resize((width, height))
        
        # 2. Превращаем в мрачный стиль (чёрно-белое + зерно)
        img = img.convert('L')  # Чёрно-белое
        img = img.convert('RGB')
        
        # 3. Добавляем зернистость
        pixels = img.load()
        for _ in range(3000):
            x = random.randint(0, width-1)
            y = random.randint(0, height-1)
            try:
                r, g, b = pixels[x, y]
                noise = random.randint(-20, 20)
                pixels[x, y] = (min(255, max(0, r+noise)), min(255, max(0, g+noise)), min(255, max(0, b+noise)))
            except:
                pass
        
        # 4. Добавляем тёмную виньетку
        mask = Image.new('L', (width, height), 255)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse([80, 80, width-80, height-80], fill=200)
        mask_draw.ellipse([150, 150, width-150, height-150], fill=255)
        enhancer = ImageEnhance.Brightness(img)
        img.paste(enhancer.enhance(0.5), mask=mask)
        
        # 5. Рисуем персонажа СКЕТЧЕМ поверх фона
        draw = ImageDraw.Draw(img)
        cx, cy = width//2, height//2 - 50
        
        random.seed(seed + int(scp_data['number']) + 100)
        scp_type = int(scp_data['number']) % 5
        
        # Выбираем цвет для скетча (белый/серый на тёмном фоне)
        color_main = (200, 200, 210)
        color_outline = (150, 150, 160)
        color_eyes = (180, 30, 30)  # Красные глаза
        
        if scp_type == 0:
            # SCP-173: Статуя (только контуры)
            # Тело (прямоугольник с закруглениями)
            draw.rectangle([cx-80, cy-40, cx+80, cy+220], outline=color_main, width=4)
            # Голова (круг)
            draw.ellipse([cx-65, cy-120, cx+65, cy-20], outline=color_main, width=4)
            # Иероглиф на лице
            draw.rectangle([cx-35, cy-90, cx+35, cy-50], outline=color_eyes, width=3)
            draw.line([cx-25, cy-70, cx+25, cy-70], fill=color_eyes, width=3)
            draw.line([cx, cy-80, cx, cy-60], fill=color_eyes, width=3)
            
        elif scp_type == 1:
            # SCP-049: Чумной доктор (только контуры)
            # Плащ
            draw.polygon([(cx-90, cy-30), (cx+90, cy-30), (cx+120, cy+250), (cx-120, cy+250)], 
                        outline=color_main, width=3)
            # Голова с маской
            draw.ellipse([cx-55, cy-130, cx+55, cy-10], outline=color_main, width=3)
            # Клюв
            draw.polygon([(cx, cy-110), (cx+65, cy-70), (cx, cy-30)], outline=color_main, width=3)
            # Глаза
            draw.ellipse([cx-20, cy-90, cx-5, cy-75], outline=color_eyes, width=2)
            draw.ellipse([cx+5, cy-90, cx+20, cy-75], outline=color_eyes, width=2)
            
        elif scp_type == 2:
            # SCP-096: Застенчивый парень (только контуры)
            # Тело (вытянутое)
            draw.rectangle([cx-45, cy-20, cx+45, cy+260], outline=color_main, width=4)
            # Голова с челюстями
            draw.ellipse([cx-80, cy-90, cx+80, cy+10], outline=color_main, width=4)
            # Глаза (маленькие)
            draw.ellipse([cx-15, cy-50, cx-5, cy-40], outline=color_outline, width=2)
            draw.ellipse([cx+5, cy-50, cx+15, cy-40], outline=color_outline, width=2)
            # Длинные руки
            draw.line([cx-45, cy+40, cx-110, cy+170], fill=color_main, width=4)
            draw.line([cx+45, cy+40, cx+110, cy+170], fill=color_main, width=4)
            
        elif scp_type == 3:
            # SCP-106: Старый человек (только контуры)
            # Тело (разрушенное)
            draw.rectangle([cx-70, cy-10, cx+70, cy+240], outline=color_main, width=3)
            # Голова
            draw.ellipse([cx-55, cy-100, cx+55, cy-5], outline=color_main, width=3)
            # Глаза-дыры
            draw.ellipse([cx-25, cy-70, cx-10, cy-55], outline=color_outline, width=2)
            draw.ellipse([cx+10, cy-70, cx+25, cy-55], outline=color_outline, width=2)
            # Коррозия (пятна)
            for _ in range(15):
                rx = random.randint(cx-60, cx+60)
                ry = random.randint(cy, cy+220)
                draw.ellipse([rx-8, ry-10, rx+8, ry+10], outline=(100, 40, 40), width=2)
            
        else:
            # SCP-682: Ящер (только контуры)
            # Тело
            draw.polygon([(cx-110, cy+90), (cx-50, cy-40), (cx+50, cy-40), (cx+110, cy+90)], 
                        outline=color_main, width=4)
            # Голова
            draw.ellipse([cx-70, cy-110, cx+70, cy-20], outline=color_main, width=4)
            # Глаза
            draw.ellipse([cx-25, cy-80, cx-10, cy-65], outline=color_eyes, width=2)
            draw.ellipse([cx+10, cy-80, cx+25, cy-65], outline=color_eyes, width=2)
            # Пасть
            draw.line([cx-45, cy-30, cx+45, cy-30], fill=color_eyes, width=4)
            # Шрамы
            for _ in range(6):
                x1 = random.randint(cx-70, cx+70)
                y1 = random.randint(cy-80, cy+70)
                draw.line([x1, y1, x1+random.randint(-30, 30), y1+random.randint(-30, 30)], 
                         fill=color_outline, width=2)
        
        # 6. Добавляем эффект "старого кино" (полосы, царапины)
        for _ in range(10):
            x = random.randint(0, width-1)
            y = random.randint(0, height-1)
            draw.line([x, y, x+random.randint(20, 100), y], fill=(50, 50, 50), width=1)
        
        # 7. Сохраняем
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
                clip = ColorClip(size=(720, 1280), color=(0, 0, 0), duration=frame_data['duration'])
                clips.append(clip)
        
        if not clips:
            clip = ColorClip(size=(720, 1280), color=(0, 0, 0), duration=10)
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
    def __init__(self):
        self.script_gen = ScriptGenerator()
        self.image_gen = ImageGenerator()
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
                
                self._add_status("🎨 Кадры с реальными фонами...")
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
    st.set_page_config(
        page_title="SCP Video Bot",
        page_icon="🎬",
        layout="wide"
    )
    
    st.title("🎬 SCP Video Generator")
    st.markdown("Создаёт полноценные видео по SCP с реальными фонами")
    st.markdown("---")
    
    with st.sidebar:
        st.header("⚙️ Настройки")
        count = st.number_input("Количество видео:", min_value=1, max_value=8, value=1)
        st.markdown("---")
        st.info("📸 Используются реальные фото из Unsplash")
        st.info("✏️ Персонажи рисуются поверх в стиле скетч")
        st.info("⏱️ 1-2 минуты на видео")
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
        st.subheader("📚 Доступные SCP")
        for scp in SCP_DATABASE[:8]:
            st.markdown(f"**SCP-{scp['number']}** - {scp['name']}")

if __name__ == "__main__":
    main()
