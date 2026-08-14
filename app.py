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
import random
import numpy as np  # <--- ЭТО ВАЖНО!
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
import io

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
        "text": "SCP-173 - это статуя из бетона и арматуры. Она неподвижна, когда на неё смотрят."
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
        "text": "SCP-087 - бесконечная лестница. На каждом уровне слышен плач ребёнка."
    },
    {
        "number": "3000",
        "name": "Анаджвари",
        "author": "Доктор В. Д.",
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

# ==================== ГЕНЕРАТОР РИСУНКОВ В СТИЛЕ "ДОКТОР ВОЙД" ====================
class VoidSketchGenerator:
    """Генерирует рисунки в стиле Доктор Войд (скетч, мрачный, экспрессионистский)"""
    
    @staticmethod
    def create_sketch(width: int, height: int, scp_data: dict, scene_index: int, total_scenes: int) -> Image.Image:
        """Создаёт рисунок в стиле Доктор Войд"""
        
        # 1. Бумажный фон
        img = Image.new('RGB', (width, height), color=(240, 235, 225))
        draw = ImageDraw.Draw(img)
        
        # 2. Текстура бумаги
        random.seed(scene_index + int(scp_data['number']) * 100)
        for _ in range(3000):
            x = random.randint(0, width-1)
            y = random.randint(0, height-1)
            brightness = random.randint(210, 240)
            draw.point((x, y), fill=(brightness, brightness-5, brightness-10))
        
        # 3. Виньетка
        mask = Image.new('L', (width, height), 255)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse([100, 100, width-100, height-100], fill=200)
        mask_draw.ellipse([200, 200, width-200, height-200], fill=255)
        enhancer = ImageEnhance.Brightness(img)
        img.paste(enhancer.enhance(0.7), mask=mask)
        
        # 4. Рисуем персонажа
        draw = ImageDraw.Draw(img)
        cx, cy = width//2, height//2 - 50
        scp_type = int(scp_data['number']) % 5
        
        # Стиль рисования (прерывистые линии, как карандаш)
        def sketch_line(x1, y1, x2, y2, color, width_val):
            steps = max(10, int(((x2-x1)**2 + (y2-y1)**2)**0.5) // 4)
            for i in range(steps):
                t = i / steps
                x = x1 + (x2 - x1) * t + random.randint(-2, 2)
                y = y1 + (y2 - y1) * t + random.randint(-2, 2)
                if random.random() > 0.2:
                    draw.ellipse([x-width_val//2, y-width_val//2, x+width_val//2, y+width_val//2], 
                                fill=color, outline=color)
        
        def sketch_ellipse(x1, y1, x2, y2, color, width_val):
            steps = 50
            for i in range(steps):
                angle = 2 * 3.14159 * i / steps
                cx_el = (x1 + x2) / 2 + random.randint(-3, 3)
                cy_el = (y1 + y2) / 2 + random.randint(-3, 3)
                rx = (x2 - x1) / 2 + random.randint(-2, 2)
                ry = (y2 - y1) / 2 + random.randint(-2, 2)
                x = cx_el + rx * np.cos(angle)
                y = cy_el + ry * np.sin(angle)
                if random.random() > 0.2:
                    draw.ellipse([x-width_val//2, y-width_val//2, x+width_val//2, y+width_val//2], 
                                fill=color, outline=color)
        
        pencil_dark = (25, 25, 30)
        pencil_medium = (55, 55, 60)
        pencil_red = (140, 30, 30)
        
        # В зависимости от SCP
        if scp_type == 0:
            # SCP-173 - Статуя
            offset_x = random.randint(-10, 10)
            offset_y = random.randint(-5, 5)
            # Тело
            sketch_line(cx-80+offset_x, cy-40+offset_y, cx-80+offset_x, cy+230+offset_y, pencil_dark, 4)
            sketch_line(cx-80+offset_x, cy+230+offset_y, cx+80+offset_x, cy+230+offset_y, pencil_dark, 4)
            sketch_line(cx+80+offset_x, cy+230+offset_y, cx+80+offset_x, cy-40+offset_y, pencil_dark, 4)
            sketch_line(cx+80+offset_x, cy-40+offset_y, cx-80+offset_x, cy-40+offset_y, pencil_dark, 4)
            # Голова
            sketch_ellipse(cx-70+offset_x, cy-130+offset_y, cx+70+offset_x, cy-20+offset_y, pencil_dark, 4)
            # Лицо
            sketch_line(cx-35+offset_x, cy-90+offset_y, cx+35+offset_x, cy-90+offset_y, pencil_red, 3)
            sketch_line(cx-35+offset_x, cy-70+offset_y, cx+35+offset_x, cy-70+offset_y, pencil_red, 3)
            sketch_line(cx+offset_x, cy-100+offset_y, cx+offset_x, cy-60+offset_y, pencil_red, 3)
            
        elif scp_type == 1:
            # SCP-049 - Чумной доктор
            # Плащ
            sketch_line(cx-100, cy-30, cx-130, cy+250, pencil_dark, 4)
            sketch_line(cx-130, cy+250, cx+130, cy+250, pencil_dark, 4)
            sketch_line(cx+130, cy+250, cx+100, cy-30, pencil_dark, 4)
            # Голова
            sketch_ellipse(cx-60, cy-140, cx+60, cy-10, pencil_dark, 4)
            # Клюв
            sketch_line(cx, cy-120, cx+70, cy-80, pencil_dark, 3)
            sketch_line(cx+70, cy-80, cx, cy-40, pencil_dark, 3)
            # Глаза
            sketch_ellipse(cx-25, cy-100, cx-5, cy-85, pencil_red, 2)
            sketch_ellipse(cx+5, cy-100, cx+25, cy-85, pencil_red, 2)
            
        elif scp_type == 2:
            # SCP-096 - Застенчивый парень
            # Тело
            sketch_line(cx-50, cy-30, cx-45, cy+270, pencil_dark, 3)
            sketch_line(cx-45, cy+270, cx+45, cy+270, pencil_dark, 3)
            sketch_line(cx+45, cy+270, cx+50, cy-30, pencil_dark, 3)
            # Челюсти
            sketch_ellipse(cx-90, cy-100, cx+90, cy+10, pencil_dark, 4)
            # Глаза
            sketch_ellipse(cx-20, cy-60, cx-5, cy-45, pencil_medium, 2)
            sketch_ellipse(cx+5, cy-60, cx+20, cy-45, pencil_medium, 2)
            # Руки
            sketch_line(cx-48, cy+40, cx-120, cy+180, pencil_dark, 3)
            sketch_line(cx+48, cy+40, cx+120, cy+180, pencil_dark, 3)
            
        elif scp_type == 3:
            # SCP-106 - Старый человек
            # Тело
            sketch_line(cx-75, cy-20, cx-70, cy+240, pencil_dark, 4)
            sketch_line(cx-70, cy+240, cx+70, cy+240, pencil_dark, 4)
            sketch_line(cx+70, cy+240, cx+75, cy-20, pencil_dark, 4)
            # Голова
            sketch_ellipse(cx-60, cy-110, cx+60, cy-5, pencil_dark, 4)
            # Глаза
            sketch_ellipse(cx-25, cy-80, cx-10, cy-65, pencil_medium, 2)
            sketch_ellipse(cx+10, cy-80, cx+25, cy-65, pencil_medium, 2)
            
        else:
            # SCP-682 - Ящер
            # Тело
            sketch_line(cx-120, cy+100, cx-60, cy-50, pencil_dark, 5)
            sketch_line(cx-60, cy-50, cx+60, cy-50, pencil_dark, 5)
            sketch_line(cx+60, cy-50, cx+120, cy+100, pencil_dark, 5)
            # Голова
            sketch_ellipse(cx-80, cy-130, cx+80, cy-30, pencil_dark, 4)
            # Глаза
            sketch_ellipse(cx-30, cy-100, cx-10, cy-80, pencil_red, 3)
            sketch_ellipse(cx+10, cy-100, cx+30, cy-80, pencil_red, 3)
            # Пасть
            sketch_line(cx-50, cy-40, cx+50, cy-40, pencil_red, 4)
        
        # 5. Штриховка
        for _ in range(150):
            x = random.randint(100, width-100)
            y = random.randint(100, height-100)
            length = random.randint(5, 15)
            angle = random.randint(0, 360)
            dx = length * np.cos(angle)
            dy = length * np.sin(angle)
            draw.line([x, y, x+dx, y+dy], fill=(60, 60, 65), width=1)
        
        # 6. Пятна
        for _ in range(30):
            x = random.randint(0, width-1)
            y = random.randint(0, height-1)
            size = random.randint(2, 8)
            brightness = random.randint(180, 210)
            draw.ellipse([x-size, y-size, x+size, y+size], 
                        fill=(brightness, brightness-5, brightness-10))
        
        # 7. Лёгкое размытие
        img = img.filter(ImageFilter.GaussianBlur(radius=0.5))
        
        return img

# ==================== ГЕНЕРАТОР СЦЕНАРИЕВ ====================
class ScriptGenerator:
    def generate_script(self, scp_data: dict) -> dict:
        scenes = [
            {"voice_text": f"Я нашёл это в старом архиве. SCP-{scp_data['number']} - {scp_data['name']}.", "duration": 7},
            {"voice_text": f"{scp_data['text']}", "duration": 8},
            {"voice_text": "Оно двигается. Не как человек. Слишком плавно.", "duration": 7},
            {"voice_text": "Я слышал голоса. Они звали меня по имени.", "duration": 7},
            {"voice_text": "Оно знает, что я здесь. Оно смотрит прямо на меня.", "duration": 7},
            {"voice_text": "Я закрыл глаза. Но когда открыл... оно стояло прямо за мной.", "duration": 7}
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
    def generate_frames(self, script: dict) -> list:
        frames = []
        scp_data = script['scp_data']
        total = len(script['scenes'])
        
        for i, scene in enumerate(script['scenes']):
            frame_path = f"{CONFIG['temp_dir']}/images/frame_{i:02d}.png"
            img = VoidSketchGenerator.create_sketch(720, 1280, scp_data, i, total)
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
                
                self._add_status("✏️ Рисование кадров...")
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
    st.set_page_config(
        page_title="SCP Sketch Video Bot",
        page_icon="✏️",
        layout="wide"
    )
    
    st.title("✏️ SCP Sketch Video Generator")
    st.markdown("Создаёт видео в стиле рисованного скетча")
    st.markdown("---")
    
    with st.sidebar:
        st.header("⚙️ Настройки")
        count = st.number_input("Количество видео:", min_value=1, max_value=8, value=1)
        st.markdown("---")
        st.info("✏️ Стиль: рисованный скетч")
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
