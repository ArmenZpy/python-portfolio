import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram import F
import asyncio

TOKEN = "ВСТАВЬТЕ_ТОКЕН_СЮДА"

bot = Bot(token=TOKEN)
dp = Dispatcher()

conn = sqlite3.connect("clients.db")
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        name TEXT,
        service TEXT,
        date TEXT
    )
""")
conn.commit()

menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Записаться")],
        [KeyboardButton(text="Мои записи")],
        [KeyboardButton(text="Контакты")]
    ],
    resize_keyboard=True
)

services_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💇 Стрижка")],
        [KeyboardButton(text="💅 Маникюр")],
        [KeyboardButton(text="💆 Массаж")],
        [KeyboardButton(text="⬅ Назад")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Добро пожаловать! Я бот для записи.\nВыберите действие:", reply_markup=menu)

@dp.message(F.text == "Записаться")
async def book(message: types.Message):
    await message.answer("Выберите услугу:", reply_markup=services_kb)

@dp.message(F.text.in_({"💇 Стрижка", "💅 Маникюр", "💆 Массаж"}))
async def choose_service(message: types.Message):
    service = message.text
    user_id = message.from_user.id
    name = message.from_user.full_name
    cursor.execute(
        "INSERT INTO appointments (user_id, name, service, date) VALUES (?, ?, ?, datetime('now'))",
        (user_id, name, service)
    )
    conn.commit()
    await message.answer(f"Вы записаны на услугу: {service}\nС вами свяжутся для подтверждения.", reply_markup=menu)

@dp.message(F.text == "Мои записи")
async def my_appointments(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT service, date FROM appointments WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    if rows:
        text = "Ваши записи:\n\n" + "\n".join([f"{r[0]} — {r[1]}" for r in rows])
    else:
        text = "У вас нет записей."
    await message.answer(text)

@dp.message(F.text == "Контакты")
async def contacts(message: types.Message):
    await message.answer("Телефон: +7 (XXX) XXX-XX-XX\nАдрес: ул. Примерная, д. 1")

@dp.message(F.text == "⬅ Назад")
async def back(message: types.Message):
    await message.answer("Главное меню:", reply_markup=menu)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    print("Бот запущен!")
    asyncio.run(main())