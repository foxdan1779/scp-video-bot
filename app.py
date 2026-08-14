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
        "appearance": "Бетонная статуя с лицом в виде красного иероглифа",
        "text": "SCP-173 - это статуя из бетона и арматуры. Она неподвижна, когда на неё смотрят."
    },
    {
        "number": "049",
        "name": "Чумной доктор",
        "author": "Габриэль",
        "appearance": "Гуманоид в средневековом костюме чумного доктора",
        "text": "SCP-049 - гуманоид, который считает себя врачом."
    },
    {
        "number": "096",
        "name": "Застенчивый парень",
        "author": "Доктор Дэн",
        "appearance": "Высокое, неестественно худое существо с белой кожей",
        "text": "SCP-096 - существо, которое не переносит, когда на него смотрят."
    },
    {
        "number": "106",
        "name": "Старый человек",
        "author": "Доктор Гирс",
        "appearance": "Гуманоид с гниющей кожей, в старом военном обмундировании",
        "text": "SCP-106 - гуманоид, который может проходить сквозь твёрдые материалы."
    },
    {
        "number": "682",
        "name": "Трудный для уничтожения ящер",
        "author": "Доктор Гирс",
        "appearance": "Крупное рептилоидное существо с шрамами",
        "text": "SCP-682 - огромная рептилия, которая не умирает."
    },
    {
        "number": "999",
        "name": "Щекочущий монстр",
        "author": "Доктор Кейн",
        "appearance": "Желейное существо оранжевого цвета",
        "text": "SCP-999 - дружелюбное существо, которое щекочет людей."
    },
    {
        "number": "087",
        "name": "Лестница в подвал",
        "author": "Доктор У. Уилсон",
        "appearance": "Тёмная лестница, ведущая в подвал",
        "text": "SCP-087 - бесконечная лестница. На каждом уровне слышен плач ребёнка."
    },
    {
        "number": "3000",
        "name": "Анаджвари",
        "author": "Доктор В. Д.",
        "appearance": "Огромный морской змей с раздвоенным хвостом",
        "text": "SCP-3000 - гигантский змей, который питается воспоминаниями."
    }
]

# ==================== КОНФИГУРАЦИЯ ====================
CONFIG = {
    'output_dir': './videos',
    'temp_dir': './temp'
}

for folder in [CONFIG['output_dir'], CONFIG['temp_dir'], f"{CONFIG['temp_dir']}/images", f"{CONFIG['temp_dir']}/audio"]:
    Path(folder).mkdir(parents=True, exist_ok=True)

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

# ==================== ГЕНЕРАТОР РИСОВАННЫХ КАДРОВ ====================
class SketchGenerator:
    """Генерирует изображения в стиле карандашного скетча"""
    
    @staticmethod
    def create_sketch_background(width: int, height: int, seed: int) -> Image.Image:
        """Создаёт фон в стиле бумаги для скетча"""
        
        random.seed(seed)
        
        # Бумажный фон (немного кремовый)
        img = Image.new('RGB', (width, height), color=(240, 235, 225))
        draw = ImageDraw.Draw(img)
        
        # Добавляем текстуру бумаги (мелкие точки и линии)
        for _ in range(5000):
            x = random.randint(0, width-1)
            y = random.randint(0, height-1)
            brightness = random.randint(200, 240)
            try:
                draw.point((x, y), fill=(brightness, brightness-5, brightness-10))
            except:
                pass
        
        # Лёгкие полосы как у старой бумаги
        for _ in range(20):
            y = random.randint(0, height-1)
            x1 = random.randint(0, width-1)
            x2 = random.randint(0, width-1)
            draw.line([x1, y, x2, y], fill=(200, 195, 185), width=1)
        
        # Тёмная виньетка по краям
        mask = Image.new('L', (width, height), 255)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse([50, 50, width-50, height-50], fill=200)
        mask_draw.ellipse([150, 150, width-150, height-150], fill=255)
        enhancer = ImageEnhance.Brightness(img)
        img.paste(enhancer.enhance(0.7), mask=mask)
        
        return img
    
    @staticmethod
    def draw_sketch_character(draw: ImageDraw.Draw, cx: int, cy: int, scp_type: int, seed: int):
        """Рисует персонажа в стиле карандашного скетча"""
        
        random.seed(seed + 100)
        
        # Цвета для скетча (как карандаш)
        pencil_dark = (30, 30, 35)
        pencil_medium = (60, 60, 65)
        pencil_light = (100, 100, 105)
        pencil_red = (120, 30, 30)
        
        # Толщина линий (как карандаш разной степени нажима)
        stroke_weight = random.randint(3, 5)
        
        # Рисуем персонажа прерывистыми линиями (эффект скетча)
        def sketch_line(x1, y1, x2, y2, color, width):
            """Рисует линию с эффектом скетча (прерывистую)"""
            steps = max(10, int(((x2-x1)**2 + (y2-y1)**2)**0.5) // 5)
            for i in range(steps):
                t = i / steps
                x = x1 + (x2 - x1) * t
                y = y1 + (y2 - y1) * t
                if random.random() > 0.15:  # 15% пропусков (прерывистость)
                    draw.ellipse([x-width//2, y-width//2, x+width//2, y+width//2], 
                                fill=color, outline=color)
        
        def sketch_ellipse(x1, y1, x2, y2, color, width):
            """Рисует эллипс прерывистыми линиями"""
            steps = 60
            for i in range(steps):
                angle = 2 * 3.14159 * i / steps
                cx_el = (x1 + x2) / 2
                cy_el = (y1 + y2) / 2
                rx = (x2 - x1) / 2
                ry = (y2 - y1) / 2
                x = cx_el + rx * np.cos(angle)
                y = cy_el + ry * np.sin(angle)
                if random.random() > 0.15:
                    draw.ellipse([x-width//2, y-width//2, x+width//2, y+width//2], 
                                fill=color, outline=color)
        
        if scp_type == 0:
            # SCP-173: Статуя (скетч)
            # Тело (неровный прямоугольник)
            points = [
                (cx-85, cy-50 + random.randint(-5, 5)),
                (cx-85 + random.randint(-5, 5), cy+230),
                (cx+85 + random.randint(-5, 5), cy+230),
                (cx+85, cy-50 + random.randint(-5, 5))
            ]
            for i in range(4):
                x1, y1 = points[i]
                x2, y2 = points[(i+1) % 4]
                sketch_line(x1, y1, x2, y2, pencil_dark, stroke_weight)
            
            # Голова (неровный круг)
            sketch_ellipse(cx-70, cy-130, cx+70, cy-20, pencil_dark, stroke_weight)
            
            # Иероглиф на лице
            sketch_rectangle(cx-40, cy-90, cx+40, cy-50, pencil_red, stroke_weight-1)
            sketch_line(cx-30, cy-70, cx+30, cy-70, pencil_red, stroke_weight-1)
            sketch_line(cx, cy-80, cx, cy-60, pencil_red, stroke_weight-1)
            
        elif scp_type == 1:
            # SCP-049: Чумной доктор (скетч)
            # Плащ
            points = [
                (cx-95, cy-30 + random.randint(-5, 5)),
                (cx+95, cy-30 + random.randint(-5, 5)),
                (cx+125, cy+250 + random.randint(-5, 5)),
                (cx-125, cy+250 + random.randint(-5, 5))
            ]
            for i in range(4):
                x1, y1 = points[i]
                x2, y2 = points[(i+1) % 4]
                sketch_line(x1, y1, x2, y2, pencil_dark, stroke_weight+1)
            
            # Голова с маской
            sketch_ellipse(cx-60, cy-135, cx+60, cy-10, pencil_dark, stroke_weight)
            # Клюв
            points = [(cx, cy-115), (cx+70, cy-75), (cx, cy-35)]
            for i in range(3):
                x1, y1 = points[i]
                x2, y2 = points[(i+1) % 3]
                sketch_line(x1, y1, x2, y2, pencil_dark, stroke_weight-1)
            # Глаза
            sketch_ellipse(cx-25, cy-95, cx-5, cy-80, pencil_red, stroke_weight-1)
            sketch_ellipse(cx+5, cy-95, cx+25, cy-80, pencil_red, stroke_weight-1)
            
        elif scp_type == 2:
            # SCP-096: Застенчивый парень (скетч)
            # Худое тело
            points = [
                (cx-50 + random.randint(-5, 5), cy-20),
                (cx-50 + random.randint(-5, 5), cy+270),
                (cx+50 + random.randint(-5, 5), cy+270),
                (cx+50 + random.randint(-5, 5), cy-20)
            ]
            for i in range(4):
                x1, y1 = points[i]
                x2, y2 = points[(i+1) % 4]
                sketch_line(x1, y1, x2, y2, pencil_dark, stroke_weight)
            
            # Огромные челюсти
            sketch_ellipse(cx-85, cy-95, cx+85, cy+15, pencil_dark, stroke_weight)
            # Глаза
            sketch_ellipse(cx-18, cy-55, cx-5, cy-45, pencil_medium, stroke_weight-1)
            sketch_ellipse(cx+5, cy-55, cx+18, cy-45, pencil_medium, stroke_weight-1)
            # Длинные руки
            sketch_line(cx-50, cy+50, cx-115, cy+175, pencil_dark, stroke_weight-1)
            sketch_line(cx+50, cy+50, cx+115, cy+175, pencil_dark, stroke_weight-1)
            
        elif scp_type == 3:
            # SCP-106: Старый человек (скетч)
            points = [
                (cx-75 + random.randint(-5, 5), cy-10),
                (cx-75 + random.randint(-5, 5), cy+245),
                (cx+75 + random.randint(-5, 5), cy+245),
                (cx+75 + random.randint(-5, 5), cy-10)
            ]
            for i in range(4):
                x1, y1 = points[i]
                x2, y2 = points[(i+1) % 4]
                sketch_line(x1, y1, x2, y2, pencil_dark, stroke_weight)
            
            sketch_ellipse(cx-60, cy-105, cx+60, cy-5, pencil_dark, stroke_weight)
            sketch_ellipse(cx-25, cy-75, cx-10, cy-60, pencil_medium, stroke_weight-1)
            sketch_ellipse(cx+10, cy-75, cx+25, cy-60, pencil_medium, stroke_weight-1)
            
            # Коррозия (пятна)
            for _ in range(15):
                rx = random.randint(cx-60, cx+60)
                ry = random.randint(cy+10, cy+230)
                sketch_ellipse(rx-10, ry-12, rx+10, ry+12, pencil_red, 2)
            
        else:
            # SCP-682: Ящер (скетч)
            points = [
                (cx-115, cy+95),
                (cx-55, cy-45),
                (cx+55, cy-45),
                (cx+115, cy+95)
            ]
            for i in range(4):
                x1, y1 = points[i]
                x2, y2 = points[(i+1) % 4]
                sketch_line(x1, y1, x2, y2, pencil_dark, stroke_weight+1)
            
            sketch_ellipse(cx-75, cy-115, cx+75, cy-20, pencil_dark, stroke_weight)
            sketch_ellipse(cx-25, cy-85, cx-10, cy-70, pencil_red, stroke_weight-1)
            sketch_ellipse(cx+10, cy-85, cx+25, cy-70, pencil_red, stroke_weight-1)
            sketch_line(cx-45, cy-35, cx+45, cy-35, pencil_red, stroke_weight)
            
            # Шрамы
            for _ in range(6):
                x1 = random.randint(cx-70, cx+70)
                y1 = random.randint(cy-85, cy+75)
                x2 = x1 + random.randint(-30, 30)
                y2 = y1 + random.randint(-30, 30)
                sketch_line(x1, y1, x2, y2, pencil_medium, 2)
    
    @classmethod
    def create_frame(cls, seed: int, scp_data: dict) -> Image.Image:
        """Создаёт полноценный кадр в стиле скетча"""
        
        width, height = 720, 1280
        scp_type = int(scp_data['number']) % 5
        
        # 1. Создаём бумажный фон
        img = cls.create_sketch_background(width, height, seed)
        draw = ImageDraw.Draw(img)
        
        # 2. Рисуем персонажа
        cx, cy = width//2, height//2 - 50
        cls.draw_sketch_character(draw, cx, cy, scp_type, seed)
        
        # 3. Добавляем штриховку (как в скетчах)
        for _ in range(100):
            x = random.randint(50, width-50)
            y = random.randint(50, height-50)
            length = random.randint(5, 20)
            angle = random.randint(0, 360)
            dx = length * np.cos(angle)
            dy = length * np.sin(angle)
            draw.line([x, y, x+dx, y+dy], fill=(50, 50, 55), width=1)
        
        # 4. Добавляем немного "грязи" (как на старой бумаге)
        for _ in range(100):
            x = random.randint(0, width-1)
            y = random.randint(0, height-1)
            size = random.randint(1, 3)
            brightness = random.randint(180, 210)
            draw.ellipse([x-size, y-size, x+size, y+size], 
                        fill=(brightness, brightness-5, brightness-10))
        
        # 5. Добавляем лёгкое размытие (эффект мягкого карандаша)
        img = img.filter(ImageFilter.GaussianBlur(radius=0.3))
        
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

# ==================== ГЕНЕРАТОР КАДРОВ ====================
class ImageGenerator:
    def generate_frames(self, script: dict) -> list:
        frames = []
        scp_data = script['scp_data']
        
        for i, scene in enumerate(script['scenes']):
            frame_path = f"{CONFIG['temp_dir']}/images/frame_{i:02d}.png"
            img = SketchGenerator.create_frame(i + int(scp_data['number']), scp_data)
            img.save(frame_path)
            frames.append({'path': frame_path, 'duration': scene.get('duration', 7)})
        return frames

# ==================== ВИДЕО-ГЕНЕРАТОР ====================
class VideoGenerator:
    def create_video(self, frames: list, audio_path: str, script: dict) -> str:
        clips = []
        
        for frame_data in frames:
            try:
                clip = ImageClip(frame_data['path'])
                clip = clip.resize(height=1280, width=720)
                clip = clip.set_duration(frame_data['duration'])
                # Добавляем лёгкое покачивание (эффект рисованной анимации)
                clip = clip.resize(lambda t: 1 + 0.005 * np.sin(t))
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
                
                self._add_status("✏️ Рисование кадров в стиле скетч...")
                frames = self.image_gen.generate_frames(script)
                self._add_status(f"   ✅ {len(frames)} кадров нарисовано")
                
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
        page_title="SCP Sketch Video Bot",
        page_icon="✏️",
        layout="wide"
    )
    
    st.title("✏️ SCP Sketch Video Generator")
    st.markdown("Создаёт видео в стиле карандашного скетча (как Доктор Войд)")
    st.markdown("---")
    
    with st.sidebar:
        st.header("⚙️ Настройки")
        count = st.number_input("Количество видео:", min_value=1, max_value=8, value=1)
        st.markdown("---")
        st.info("✏️ Стиль: карандашный скетч")
        st.info("📄 Фон: бумага")
        st.info("🎨 Персонажи: рисованные")
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
        if st.button("✏️ Сгенерировать видео", type="primary", use_container_width=True):
            with st.spinner("Рисование видео..."):
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
