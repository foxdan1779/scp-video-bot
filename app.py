import streamlit as st
import os
import re
import json
import time
import shutil
import asyncio
import requests
import base64
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
    'replicate_token': 'r8_ваш_токен',  # 👈 ВСТАВЬТЕ СВОЙ ТОКЕН
    'replicate_model': 'stability-ai/stable-diffusion:db21e45d3f7023abc2a46ee38a23973f6dce16bb082a930b0c49861f96d1e5bf'
}

for folder in [CONFIG['output_dir'], CONFIG['temp_dir'], f"{CONFIG['temp_dir']}/images", f"{CONFIG['temp_dir']}/audio"]:
    Path(folder).mkdir(parents=True, exist_ok=True)

# ==================== ВСТРОЕННАЯ БАЗА SCP ====================
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

# ==================== ГЕНЕРАТОР СЦЕНАРИЕВ ====================
class ScriptGenerator:
    def generate_script(self, scp_data: dict) -> dict:
        scenes = [
            {"prompt": f"{scp_data['name']}, dark horror atmosphere, sketch style, гротеск, мрачный", "voice_text": f"Я нашёл это в старом архиве. SCP-{scp_data['number']} - {scp_data['name']}.", "duration": 7},
            {"prompt": f"{scp_data['name']}, close up, detailed, horror sketch, угольный рисунок", "voice_text": f"{scp_data['text']}", "duration": 8},
            {"prompt": f"{scp_data['name']}, movement, dynamic, scary, sketch", "voice_text": "Оно двигается. Не как человек. Слишком плавно.", "duration": 7},
            {"prompt": f"{scp_data['name']}, in the dark, shadows, horror art, гротеск", "voice_text": "Я слышал голоса. Они звали меня по имени.", "duration": 7},
            {"prompt": f"{scp_data['name']}, looking at viewer, scary eyes, sketch", "voice_text": "Оно знает, что я здесь. Оно смотрит прямо на меня.", "duration": 7},
            {"prompt": f"{scp_data['name']}, behind the viewer, horror, dark, скетч", "voice_text": "Я закрыл глаза. Но когда открыл... оно стояло прямо за мной.", "duration": 7}
        ]
        return {
            "title": f"SCP-{scp_data['number']} | {scp_data['name']}",
            "scp_number": scp_data['number'],
            "scp_name": scp_data['name'],
            "author": scp_data['author'],
            "scenes": scenes,
            "scp_data": scp_data
        }

# ==================== REPLICATE API ====================
class ReplicateGenerator:
    def __init__(self, token: str, model: str):
        self.token = token
        self.model = model
        self.api_url = "https://api.replicate.com/v1/predictions"
        self.headers = {
            "Authorization": f"Token {token}",
            "Content-Type": "application/json"
        }
    
    def generate_image(self, prompt: str, negative_prompt: str = "") -> Image.Image:
        """Генерирует изображение через Replicate API"""
        
        # Формируем запрос
        payload = {
            "version": self.model,
            "input": {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "num_inference_steps": 25,
                "guidance_scale": 7.5,
                "width": 512,
                "height": 768
            }
        }
        
        try:
            # 1. Запускаем предсказание
            response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=30)
            if response.status_code != 201:
                st.error(f"Ошибка запуска: {response.status_code} - {response.text}")
                return self._fallback_image()
            
            prediction = response.json()
            prediction_id = prediction['id']
            
            # 2. Ждём завершения (polling)
            status_url = f"{self.api_url}/{prediction_id}"
            for _ in range(30):  # ~30 секунд
                time.sleep(2)
                status_response = requests.get(status_url, headers=self.headers)
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    if status_data['status'] == 'succeeded':
                        # Получаем URL изображения
                        image_url = status_data['output'][0]
                        img_response = requests.get(image_url)
                        if img_response.status_code == 200:
                            img = Image.open(io.BytesIO(img_response.content))
                            return img
                        else:
                            break
                    elif status_data['status'] == 'failed':
                        st.error(f"Ошибка генерации: {status_data.get('error', 'неизвестная ошибка')}")
                        break
                else:
                    break
            
            # Если не дождались или ошибка
            return self._fallback_image()
            
        except Exception as e:
            st.error(f"Ошибка API: {e}")
            return self._fallback_image()
    
    def _fallback_image(self) -> Image.Image:
        img = Image.new('RGB', (512, 768), color=(20, 20, 30))
        return img

# ==================== ГЕНЕРАТОР КАДРОВ ====================
class ImageGenerator:
    def __init__(self, api: ReplicateGenerator):
        self.api = api
    
    def generate_frames(self, script: dict) -> list:
        frames = []
        total = len(script['scenes'])
        
        for i, scene in enumerate(script['scenes']):
            st.text(f"   🎨 Генерация кадра {i+1}/{total}...")
            prompt = f"{scene['prompt']}, стиль Доктор Войд, гротескный скетч, угольный рисунок, экспрессионизм, мрачный хоррор, черно-белое с красными акцентами"
            negative_prompt = "фотореализм, фотография, глянец, мультяшность, аниме, цветное, яркое, реализм"
            img = self.api.generate_image(prompt, negative_prompt)
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
                clip = ColorClip(size=(720, 1280), color=(20, 20, 30), duration=frame_data['duration'])
                clips.append(clip)
        
        if not clips:
            clip = ColorClip(size=(720, 1280), color=(20, 20, 30), duration=10)
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
    def __init__(self, api: ReplicateGenerator):
        self.script_gen = ScriptGenerator()
        self.image_gen = ImageGenerator(api)
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
                self._add_status("🎨 Генерация через Replicate API...")
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
    st.set_page_config(page_title="SCP Video Bot (Replicate)", page_icon="🎨", layout="wide")
    st.title("🎨 SCP Video Bot + Replicate API")
    st.markdown("Создаёт видео с рисунками через нейросеть (без установки!)")
    st.markdown("---")
    
    # Проверка токена
    if CONFIG['replicate_token'] == 'r8_ваш_токен':
        st.warning("⚠️ Вставьте свой токен Replicate в файл `app.py` (строка `replicate_token`)")
        st.markdown("1. Зарегистрируйтесь на [replicate.com](https://replicate.com)")
        st.markdown("2. Получите API-токен в настройках")
        st.markdown("3. Замените `r8_ваш_токен` в коде")
        return
    
    api = ReplicateGenerator(CONFIG['replicate_token'], CONFIG['replicate_model'])
    
    with st.sidebar:
        st.header("⚙️ Настройки")
        count = st.number_input("Количество видео:", min_value=1, max_value=3, value=1)
        st.markdown("---")
        st.info("🎨 Модель: Stable Diffusion (Replicate)")
        st.info("⏱️ ~10-20 секунд на кадр")
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
        if st.button("🎨 Сгенерировать видео", type="primary", use_container_width=True):
            with st.spinner("Генерация видео..."):
                bot = SCPBot(api)
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
