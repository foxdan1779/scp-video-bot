import streamlit as st
import os
import re
import json
import time
import shutil
import asyncio
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
import numpy as np

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
    'temp_dir': './temp'
}

for folder in [CONFIG['output_dir'], CONFIG['temp_dir'], f"{CONFIG['temp_dir']}/images", f"{CONFIG['temp_dir']}/audio"]:
    Path(folder).mkdir(parents=True, exist_ok=True)

# ==================== БАЗА SCP ====================
SCP_DATABASE = [
    {"number": "173", "name": "Скульптура", "author": "М. Роджерс", "text": "SCP-173 - статуя из бетона и арматуры."},
    {"number": "049", "name": "Чумной доктор", "author": "Габриэль", "text": "SCP-049 - гуманоид, который считает себя врачом."},
    {"number": "096", "name": "Застенчивый парень", "author": "Доктор Дэн", "text": "SCP-096 - существо, которое не переносит, когда на него смотрят."},
    {"number": "106", "name": "Старый человек", "author": "Доктор Гирс", "text": "SCP-106 - гуманоид, который может проходить сквозь твёрдые материалы."},
    {"number": "682", "name": "Трудный для уничтожения ящер", "author": "Доктор Гирс", "text": "SCP-682 - огромная рептилия, которая не умирает."},
    {"number": "999", "name": "Щекочущий монстр", "author": "Доктор Кейн", "text": "SCP-999 - дружелюбное существо, которое щекочет людей."},
    {"number": "087", "name": "Лестница в подвал", "author": "Доктор У. Уилсон", "text": "SCP-087 - бесконечная лестница."},
    {"number": "3000", "name": "Анаджвари", "author": "Доктор В. Д.", "text": "SCP-3000 - гигантский змей."}
]

# ==================== УЛУЧШЕННЫЙ ГЕНЕРАТОР СКЕТЧЕЙ ====================
class AdvancedSketchGenerator:
    @staticmethod
    def create_scene(seed: int, scp_data: dict, scene_index: int, total_scenes: int) -> Image.Image:
        """Создаёт атмосферный кадр с вариациями"""
        width, height = 720, 1280
        random.seed(seed + scene_index * 100)
        
        # 1. Фон (бумага/холст с текстурой)
        bg_color = random.choice([
            (240, 235, 225),  # светлая бумага
            (220, 215, 205),  # серая бумага
            (200, 195, 185),  # тёмная бумага
            (250, 245, 235)   # почти белая
        ])
        img = Image.new('RGB', (width, height), color=bg_color)
        draw = ImageDraw.Draw(img)
        
        # 2. Текстура
        for _ in range(2000):
            x = random.randint(0, width-1)
            y = random.randint(0, height-1)
            br = random.randint(180, 240)
            draw.point((x, y), fill=(br, br-5, br-10))
        
        # 3. Случайные линии (эффект эскиза)
        for _ in range(50):
            x1 = random.randint(0, width)
            y1 = random.randint(0, height)
            x2 = random.randint(0, width)
            y2 = random.randint(0, height)
            draw.line([x1, y1, x2, y2], fill=(100, 100, 110), width=random.randint(1, 2))
        
        # 4. Рисуем персонажа/объект
        cx, cy = width//2, height//2 - 50
        scp_type = int(scp_data['number']) % 5
        
        # Выбираем стиль рисования
        style = random.choice(['sketch', 'doodle', 'rough'])
        
        def sketch_line(x1, y1, x2, y2, color, w):
            steps = max(10, int(((x2-x1)**2 + (y2-y1)**2)**0.5) // 3)
            for i in range(steps):
                t = i / steps
                x = x1 + (x2 - x1) * t + random.randint(-2, 2)
                y = y1 + (y2 - y1) * t + random.randint(-2, 2)
                if random.random() > (0.15 if style == 'sketch' else 0.3):
                    draw.ellipse([x-w//2, y-w//2, x+w//2, y+w//2], fill=color, outline=color)
        
        def sketch_ellipse(x1, y1, x2, y2, color, w):
            steps = 50
            for i in range(steps):
                angle = 2 * 3.14159 * i / steps
                cx_el = (x1 + x2) / 2 + random.randint(-3, 3)
                cy_el = (y1 + y2) / 2 + random.randint(-3, 3)
                rx = (x2 - x1) / 2 + random.randint(-2, 2)
                ry = (y2 - y1) / 2 + random.randint(-2, 2)
                x = cx_el + rx * np.cos(angle)
                y = cy_el + ry * np.sin(angle)
                if random.random() > (0.2 if style == 'sketch' else 0.35):
                    draw.ellipse([x-w//2, y-w//2, x+w//2, y+w//2], fill=color, outline=color)
        
        # Цвета карандаша
        dark = (20, 20, 25)
        medium = (60, 60, 70)
        red = (160, 40, 40)
        accent = random.choice([red, (200, 150, 50), (80, 80, 180)])
        
        # Рисуем фигуру в зависимости от типа SCP
        if scp_type == 0:
            # SCP-173
            sketch_ellipse(cx-60, cy-100, cx+60, cy-20, dark, 4)
            sketch_line(cx-70, cy-30, cx-70, cy+200, dark, 4)
            sketch_line(cx-70, cy+200, cx+70, cy+200, dark, 4)
            sketch_line(cx+70, cy+200, cx+70, cy-30, dark, 4)
            sketch_line(cx-30, cy-70, cx+30, cy-70, accent, 3)
            sketch_line(cx-30, cy-50, cx+30, cy-50, accent, 3)
            sketch_line(cx, cy-80, cx, cy-40, accent, 3)
            
        elif scp_type == 1:
            # SCP-049
            sketch_line(cx-100, cy-20, cx-130, cy+250, dark, 4)
            sketch_line(cx-130, cy+250, cx+130, cy+250, dark, 4)
            sketch_line(cx+130, cy+250, cx+100, cy-20, dark, 4)
            sketch_ellipse(cx-60, cy-130, cx+60, cy-10, dark, 4)
            sketch_line(cx, cy-110, cx+70, cy-70, dark, 3)
            sketch_line(cx+70, cy-70, cx, cy-30, dark, 3)
            sketch_ellipse(cx-25, cy-95, cx-5, cy-80, accent, 2)
            sketch_ellipse(cx+5, cy-95, cx+25, cy-80, accent, 2)
            
        elif scp_type == 2:
            # SCP-096
            sketch_line(cx-45, cy-20, cx-45, cy+270, dark, 3)
            sketch_line(cx-45, cy+270, cx+45, cy+270, dark, 3)
            sketch_line(cx+45, cy+270, cx+45, cy-20, dark, 3)
            sketch_ellipse(cx-80, cy-90, cx+80, cy+10, dark, 4)
            sketch_ellipse(cx-20, cy-55, cx-5, cy-40, medium, 2)
            sketch_ellipse(cx+5, cy-55, cx+20, cy-40, medium, 2)
            sketch_line(cx-45, cy+40, cx-110, cy+170, dark, 3)
            sketch_line(cx+45, cy+40, cx+110, cy+170, dark, 3)
            
        elif scp_type == 3:
            # SCP-106
            sketch_line(cx-70, cy-10, cx-70, cy+240, dark, 4)
            sketch_line(cx-70, cy+240, cx+70, cy+240, dark, 4)
            sketch_line(cx+70, cy+240, cx+70, cy-10, dark, 4)
            sketch_ellipse(cx-55, cy-100, cx+55, cy-5, dark, 4)
            sketch_ellipse(cx-25, cy-75, cx-10, cy-60, accent, 2)
            sketch_ellipse(cx+10, cy-75, cx+25, cy-60, accent, 2)
            
        else:
            # SCP-682
            sketch_line(cx-120, cy+100, cx-60, cy-50, dark, 5)
            sketch_line(cx-60, cy-50, cx+60, cy-50, dark, 5)
            sketch_line(cx+60, cy-50, cx+120, cy+100, dark, 5)
            sketch_ellipse(cx-80, cy-130, cx+80, cy-30, dark, 4)
            sketch_ellipse(cx-30, cy-100, cx-10, cy-80, accent, 3)
            sketch_ellipse(cx+10, cy-100, cx+30, cy-80, accent, 3)
            sketch_line(cx-50, cy-40, cx+50, cy-40, accent, 4)
        
        # 5. Добавляем тени и штриховку
        for _ in range(100):
            x = random.randint(50, width-50)
            y = random.randint(50, height-50)
            length = random.randint(5, 20)
            angle = random.randint(0, 360)
            dx = length * np.cos(angle)
            dy = length * np.sin(angle)
            draw.line([x, y, x+dx, y+dy], fill=(80, 80, 90), width=1)
        
        # 6. Виньетка
        mask = Image.new('L', (width, height), 255)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse([80, 80, width-80, height-80], fill=200)
        mask_draw.ellipse([180, 180, width-180, height-180], fill=255)
        enhancer = ImageEnhance.Brightness(img)
        img.paste(enhancer.enhance(0.5), mask=mask)
        
        # 7. Лёгкое размытие (эффект мягкого карандаша)
        img = img.filter(ImageFilter.GaussianBlur(radius=0.4))
        
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
        total = len(script['scenes'])
        scp = script['scp_data']
        for i, scene in enumerate(script['scenes']):
            st.text(f"   ✏️ Рисование кадра {i+1}/{total}...")
            img = AdvancedSketchGenerator.create_scene(
                seed=i + int(scp['number']),
                scp_data=scp,
                scene_index=i,
                total_scenes=total
            )
            frame_path = f"{CONFIG['temp_dir']}/images/frame_{i:02d}.png"
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
    st.set_page_config(page_title="SCP Sketch Video Bot", page_icon="✏️", layout="wide")
    st.title("✏️ SCP Sketch Video Bot (автономный)")
    st.markdown("Создаёт видео из рисованных кадров (без внешних API)")
    st.markdown("---")
    
    with st.sidebar:
        st.header("⚙️ Настройки")
        count = st.number_input("Количество видео:", min_value=1, max_value=3, value=1)
        st.markdown("---")
        st.info("✏️ Используются рисованные скетчи")
        st.info("🎨 Каждый кадр уникален (рандомные вариации)")
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
        if st.button("✏️ Сгенерировать видео", type="primary", use_container_width=True):
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
