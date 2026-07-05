import speech_recognition as sr
import random
import os
import tempfile
import asyncio
import edge_tts
import pyglet

ASSISTANT_NAME = "Умняша"
USER_NAME = "ученик"
VOICE = "ru-RU-DariyaNeural"

def speak(text):
    print(f"🤖 {ASSISTANT_NAME}: {text}")
    temp_dir = tempfile.gettempdir()
    mp3_path = os.path.join(temp_dir, "math_tts.mp3")
    if os.path.exists(mp3_path):
        try:
            os.remove(mp3_path)
        except:
            pass
    try:
        async def gen():
            communicate = edge_tts.Communicate(text, VOICE)
            await communicate.save(mp3_path)
        asyncio.run(gen())
        sound = pyglet.media.load(mp3_path)
        sound.play()
        pyglet.app.run()
    except Exception as e:
        print(f"Ошибка синтеза речи: {e}")

def listen():
    recognizer = sr.Recognizer()
    try:
        import sounddevice as sd
        import numpy as np
        print("🎤 Слушаю ответ...")
        duration = 3
        sample_rate = 44100
        audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
        sd.wait()
        audio_bytes = audio_data.tobytes()
        audio = sr.AudioData(audio_bytes, sample_rate, 2)
        text = recognizer.recognize_google(audio, language="ru-RU")
        print(f"👤 {USER_NAME}: {text}")
        return text.lower()
    except sr.UnknownValueError:
        return ""
    except sr.RequestError:
        speak("Интернет не работает.")
        return ""
    except Exception as e:
        print(f"Ошибка микрофона: {e}")
        return ""

def generate_arithmetic(difficulty=1):
    if difficulty == 1:
        a, b = random.randint(1, 20), random.randint(1, 20)
        op = random.choice(['+', '-'])
    elif difficulty == 2:
        a, b = random.randint(10, 99), random.randint(1, 50)
        op = random.choice(['+', '-', '*'])
    else:
        a, b = random.randint(10, 99), random.randint(2, 10)
        op = random.choice(['*', '/'])
        if op == '/': a = b * random.randint(1, 10)
    if op == '+': return f"{a} + {b}", a + b
    elif op == '-':
        if b > a: a, b = b, a
        return f"{a} - {b}", a - b
    elif op == '*': return f"{a} умножить на {b}", a * b
    else: return f"{a} разделить на {b}", a // b

def parse_number(text):
    words = text.split()
    for w in words:
        w = w.strip('.,!?')
        if w.isdigit(): return int(w)
    word_to_num = {
        'ноль':0,'один':1,'два':2,'три':3,'четыре':4,'пять':5,
        'шесть':6,'семь':7,'восемь':8,'девять':9,'десять':10,
        'одиннадцать':11,'двенадцать':12,'тринадцать':13,'четырнадцать':14,
        'пятнадцать':15,'шестнадцать':16,'семнадцать':17,'восемнадцать':18,
        'девятнадцать':19,'двадцать':20
    }
    if text.strip() in word_to_num: return word_to_num[text.strip()]
    return None

def arithmetic_mode(difficulty=1):
    speak("Решаем примеры. Скажи 'стоп' чтобы закончить.")
    correct, total = 0, 0
    while True:
        question, answer = generate_arithmetic(difficulty)
        speak(f"Сколько будет {question}?")
        user_input = listen()
        if not user_input: continue
        if any(w in user_input for w in ["стоп", "выход", "хватит"]): break
        user_number = parse_number(user_input)
        if user_number == answer:
            speak(random.choice(["Правильно!", "Молодец!", "Верно!"]))
            correct += 1
        else:
            speak(f"Ответ: {answer}. Попробуем ещё.")
        total += 1
    if total > 0: speak(f"Итог: {correct} из {total}.")

def main():
    speak(f"Привет, {USER_NAME}! Я {ASSISTANT_NAME}. Занимаемся математикой.")
    while True:
        print("\n1. Лёгкие примеры\n2. Средние\n3. Сложные\n4. Выход")
        speak("Выбери режим: скажи цифру или название.")
        choice = listen()
        if not choice: continue
        if "1" in choice or "лёгк" in choice: arithmetic_mode(1)
        elif "2" in choice or "средн" in choice: arithmetic_mode(2)
        elif "3" in choice or "сложн" in choice: arithmetic_mode(3)
        elif "4" in choice or "выход" in choice or "стоп" in choice:
            speak("Пока!")
            break

if __name__ == "__main__":
    main()