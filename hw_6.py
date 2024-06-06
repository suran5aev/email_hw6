import sqlite3
import smtplib
import logging
from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from config import token, smtp_sender, smtp_sender_password
from email.message import EmailMessage

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Соединение с базой данных
try:
    conn = sqlite3.connect('messages.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS emails(
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT,
                        subject TEXT, 
                        message TEXT
                    )''')
    conn.commit()
except Exception as e:
    logging.error(f"Ошибка при соединении с базой данных: {e}")

# Настройка бота
bot = Bot(token=token)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class Form(StatesGroup):
    email = State()
    subject = State()
    message = State()

@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
    await Form.email.set()
    await message.reply("Введите email получателя:")

@dp.message_handler(state=Form.email)
async def process_email(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['email'] = message.text
    await Form.next()
    await message.reply("Введите тему письма:")

@dp.message_handler(state=Form.subject)
async def process_subject(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['subject'] = message.text
    await Form.next()
    await message.reply("Введите сообщение:")

@dp.message_handler(state=Form.message)
async def process_message(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['message'] = message.text

    result = send_email(data['email'], data['subject'], data['message'])
    if result == "200 ok":
        await state.finish()
        await message.reply("Сообщение отправлено!")
    else:
        await message.reply(f"Ошибка при отправке сообщения: {result}")

def send_email(to_email, subject, message):
    sender = smtp_sender
    password = smtp_sender_password
    
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    
    try:
        server.login(sender, password)
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = to_email
        msg.set_content(message)
    
        server.send_message(msg)
        
        cursor.execute("INSERT INTO emails (email, subject, message) VALUES (?, ?, ?)", (to_email, subject, message))
        conn.commit()
        
        return "200 ok"
    except Exception as error:
        logging.error(f"Ошибка при отправке email: {error}")
        return f"Error: {error}"
    finally:
        server.quit()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
