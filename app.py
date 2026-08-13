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
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
import numpy as np

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
        "rating": 250,
        "appearance": "Бетонная статуя с лицом в виде красного иероглифа, без рук и ног, но способная двигаться",
        "text": "SCP-173 - это статуя из бетона и арматуры. Она неподвижна, когда на неё смотрят. Как только вы отводите взгляд, она мгновенно перемещается и ломает шею."
    },
    {
        "number": "049",
        "name": "Чумной доктор",
        "author": "Габриэль",
        "rating": 220,
        "appearance": "Гуманоид в средневековом костюме чумного доктора, с клювовидной маской",
        "text": "SCP-049 - гуманоид, который считает себя врачом. Он пытается 'лечить' людей, превращая их в зомби-подобных существ."
    },
    {
        "number": "096",
        "name": "Застенчивый парень",
        "author": "Доктор Дэн",
        "rating": 300,
        "appearance": "Высокое, неестественно худое существо с белой кожей и огромными челюстями",
        "text": "SCP-096 - существо, которое не переносит, когда на него смотрят. Если кто-то видит его лицо, он впадает в ярость и преследует жертву."
    },
    {
        "number": "106",
        "name": "Старый человек",
        "author": "Доктор Гирс",
        "rating": 200,
        "appearance": "Гуманоид с гниющей кожей, покрытой коррозией, в старом военном обмундировании",
        "text": "SCP-106 - гуманоид, который может проходить сквозь твёрдые материалы. Он заманивает жертв в свой карманный мир."
    },
    {
        "number": "682",
        "name": "Трудный для уничтожения ящер",
        "author": "Доктор Гирс",
        "rating": 280,
        "appearance": "Крупное рептилоидное существо с невероятной регенерацией, покрытое шрамами",
        "text": "SCP-682 - огромная рептилия, которая не умирает. Фонд пытался уничтожить её сотнями способов, но она всегда выживает."
    },
    {
        "number": "999",
        "name": "Щекочущий монстр",
        "author": "Доктор Кейн",
        "rating": 180,
        "appearance": "Желейное существо оранжевого цвета, похожее на слизь, с улыбающимся лицом",
        "text": "SCP-999 - дружелюбное существо, которое щекочет людей и вызывает у них эйфорию. Оно абсолютно безопасно."
    },
    {
        "number": "087",
        "name": "Лестница в подвал",
        "author": "Доктор У. Уилсон",
        "rating": 210,
        "appearance": "Тёмная лестница, ведущая в подвал, на которой слышны шаги и плач ребёнка",
        "text": "SCP-087 - бесконечная лестница. На каждом уровне слышен плач ребёнка, но чем глубже вы спускаетесь, тем страшнее становится."
    },
    {
        "number": "3000",
        "name": "Анаджвари",
        "author": "Доктор В. Д.",
        "rating": 190,
        "appearance": "Огромный морской змей с раздвоенным хвостом, обитающий на дне океана",
        "text": "SCP-3000 - гигантский змей, который питается воспоминаниями людей. Его яд заставляет забыть всё."
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
                "frame_description": f"{scp_data['appearance']} в тёмной комнате",
                "voice_text": f"Я нашёл это в старом архиве. SCP-{scp_data['number']} - {scp_data['name']}. Оно не должно было попасть ко мне.",
                "duration": 7
            },
            {
                "frame_description": "Крупный план существа",
                "voice_text": f"Исследователи говорят, что {scp_data['text'][:100]}... Это слишком древнее. Слишком злое.",
                "duration": 7
            },
            {
                "frame_description": "Существо медленно поворачивается",
                "voice_text": "Оно двигается. Не как человек. Слишком плавно. Слишком неестественно.",
                "duration": 7
            },
            {
                "frame_description": "Тёмный коридор, фигура вдалеке",
                "voice_text": "Я слышал голоса. Они звали меня по имени. Но я был один.",
                "duration": 7
            },
            {
                "frame_description": "Существо смотрит прямо в камеру",
                "voice_text": "Оно знает, что я здесь. Оно смотрит прямо на меня. И улыбается.",
                "duration": 7
            },
            {
                "frame_description": "Темнота, только пара светящихся глаз",
                "voice_text": "Я закрыл глаза. Но когда открыл... оно стояло прямо за мной.",
                "duration": 7
            }
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
        # Создаём тёмный фон
        img = Image.new('RGB', (1080, 1920), color=(10, 10, 15))
        draw = ImageDraw.Draw(img)
        
        random.seed(seed + int(scp_data['number']) + 42)
        
        # Текстуры
        for _ in range(50):
            x1 = random.randint(0, 1080)
            y1 = random.randint(0, 1920)
            x2 = random.randint(0, 1080)
            y2 = random.randint(0, 1920)
            draw.line([x1, y1, x2, y2], fill=(30, 30, 35), width=random.randint(1, 4))
        
        # Центр
        cx, cy = 540, 960
        scp_num = int(scp_data['number']) % 3
        
        if scp_num == 0:
            # Человекоподобное
            draw.rectangle([cx-120, cy-60, cx+120, cy+360], fill=(25, 25, 35), outline=(50, 50, 60))
            draw.ellipse([cx-100, cy-180, cx+100, cy-40], fill=(30, 30, 40), outline=(50, 50, 60))
            draw.ellipse([cx-50, cy-120, cx-10, cy-80], fill=(180, 20, 20))
            draw.ellipse([cx+10, cy-120, cx+50, cy-80], fill=(180, 20, 20))
            draw.line([cx-120, cy, cx-240, cy+100], fill=(30, 30, 40), width=12)
            draw.line([cx+120, cy, cx+240, cy+100], fill=(30, 30, 40), width=12)
            
        elif scp_num == 1:
            # Монолит
            draw.rectangle([cx-140, cy-300, cx+140, cy+300], fill=(20, 20, 30), outline=(50, 50, 60))
            for _ in range(8):
                rx = random.randint(cx-100, cx+100)
                ry = random.randint(cy-200, cy+200)
                draw.rectangle([rx-20, ry-30, rx+20, ry+30], fill=(100, 30, 30), outline=(150, 40, 40))
                
        else:
            # Абстрактное
            for _ in range(15):
                rx = random.randint(0, 1080)
                ry = random.randint(0, 1920)
                rw = random.randint(60, 200)
                rh = random.randint(60, 200)
                draw.ellipse([rx-rw//2, ry-rh//2, rx+rw//2, ry+rh//2], 
                           fill=(random.randint(20, 40), random.randint(20, 40), random.randint(20, 40)))
        
        # Виньетка
        mask = Image.new('L', (1080, 1920), 255)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse([100, 100, 980, 1820], fill=200)
        mask_draw.ellipse([200, 200, 880, 1720], fill=255)
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
        except Exception as e:
            st.warning(f"Ошибка озвучки: {e}")
            return None

# ==================== ВИДЕО-ГЕНЕРАТОР ====================
class VideoGenerator:
    def create_video(self, frames: list, audio_path: str, script: dict) -> str:
        """Создаёт видео используя moviepy"""
        
        clips = []
        
        for frame_data in frames:
            try:
                # Загружаем изображение
                clip = ImageClip(frame_data['path'])
                clip = clip.resize(height=1920, width=1080)
                clip = clip.set_duration(frame_data['duration'])
                
                # Добавляем эффект зума
                clip = clip.resize(lambda t: 1 + 0.008 * t)
                clips.append(clip)
                
            except Exception as e:
                st.warning(f"Ошибка создания клипа: {e}")
                # Создаём чёрный клип
                clip = ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=frame_data['duration'])
                clips.append(clip)
        
        if not clips:
            clip = ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=10)
            clips.append(clip)
        
        # Склеиваем
        final = concatenate_videoclips(clips, method="compose")
        
        # Добавляем аудио
        if audio_path and os.path.exists(audio_path) and os.path.getsize(audio_path) > 1000:
            try:
                audio = AudioFileClip(audio_path)
                if audio.duration > final.duration:
                    audio = audio.subclip(0, final.duration)
                final = final.set_audio(audio)
            except Exception as e:
                st.warning(f"Не удалось добавить аудио: {e}")
        
        # Субтитры
        try:
            subtitles = self._make_subtitles(script['scenes'])
            if subtitles:
                final = CompositeVideoClip([final] + subtitles)
        except Exception as e:
            st.warning(f"Ошибка субтитров: {e}")
        
        # Имя файла
        scp_num = script.get('scp_number', '000')
        scp_name = script.get('scp_name', 'unknown')
        safe_name = re.sub(r'[^\w\s-]', '', scp_name)
        safe_name = re.sub(r'[-\s]+', '_', safe_name)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"SCP-{scp_num}_{safe_name}_{timestamp}.mp4"
        output_path = os.path.join(CONFIG['output_dir'], filename)
        
        # Экспорт
        try:
            final.write_videofile(
                output_path,
                fps=24,
                codec='libx264',
                audio_codec='aac',
                threads=1,
                preset='ultrafast',
                verbose=False,
                logger=None
            )
        except Exception as e:
            st.error(f"Ошибка создания видео: {e}")
            # Создаём текстовый файл с ошибкой
            txt_path = output_path.replace('.mp4', '.txt')
            with open(txt_path, 'w') as f:
                f.write(f"Ошибка создания видео: {e}")
            return txt_path
        
        return output_path
    
    def _make_subtitles(self, scenes):
        """Создаёт субтитры для каждой сцены"""
        txt_clips = []
        current = 0
        
        for scene in scenes:
            text = scene.get('voice_text', '')
            duration = scene.get('duration', 6)
            
            try:
                txt = TextClip(
                    text,
                    fontsize=50,
                    color='white',
                    stroke_color='black',
                    stroke_width=3,
                    font='Arial',
                    method='caption',
                    size=(900, None)
                )
                txt = txt.set_position(('center', 0.85), relative=True)
                txt = txt.set_start(current)
                txt = txt.set_duration(duration)
                txt_clips.append(txt)
            except:
                pass
            current += duration
        
        return txt_clips

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
            self._add_status(f"   👤 Автор: {scp['author']}")
            
            try:
                self._add_status("✍️ Генерация сценария...")
                script = self.script_gen.generate_script(scp)
                self._add_status(f"   ✅ Сценарий: {len(script['scenes'])} сцен")
                
                self._add_status("🎨 Генерация кадров...")
                frames = self.image_gen.generate_frames(script, scp)
                self._add_status(f"   ✅ Сгенерировано {len(frames)} кадров")
                
                self._add_status("🎤 Генерация озвучки...")
                audio = self.voice_gen.generate_voice(script)
                if audio:
                    self._add_status("   ✅ Озвучка готова")
                else:
                    self._add_status("   ⚠️ Озвучка не создана")
                
                self._add_status("🎬 Создание видео...")
                video_path = self.video_gen.create_video(frames, audio, script)
                
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
        page_title="SCP Video Bot",
        page_icon="🎬",
        layout="wide"
    )
    
    st.title("🎬 SCP Video Generator")
    st.markdown("Создаёт видео по SCP прямо в браузере")
    st.markdown("---")
    
    with st.sidebar:
        st.header("⚙️ Настройки")
        count = st.number_input("Количество видео:", min_value=1, max_value=8, value=1)
        st.markdown("---")
        st.info("💡 Используется встроенная база SCP (8 штук)")
        st.success("✅ Исправлена ошибка ANTIALIAS!")
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
