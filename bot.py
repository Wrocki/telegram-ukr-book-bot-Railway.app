import os
import telebot
import sqlite3
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage

# Ініціалізація бота
state_storage = StateMemoryStorage()
bot = telebot.TeleBot(os.getenv('BOT_TOKEN'), state_storage=state_storage)

# Створення БД для зберігання інформації про книги
conn = sqlite3.connect('books.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS books
                (file_id TEXT, file_name TEXT, description TEXT)''')
conn.commit()

# Клас для станів бота
class BookStates(StatesGroup):
    waiting_for_description = State()

# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Привіт! Я бот для зберігання та пошуку книг.\n"
                         "Відправте мені файл книги, і я збережу його.\n"
                         "Для пошуку книги використовуйте команду /search")

# Обробка файлів
@bot.message_handler(content_types=['document'])
def handle_docs(message):
    try:
        file_info = bot.get_file(message.document.file_id)
        file_name = message.document.file_name
        file_id = message.document.file_id
        
        bot.reply_to(message, "Будь ласка, напишіть короткий опис книги (назва, автор):")
        bot.set_state(message.from_user.id, BookStates.waiting_for_description, message.chat.id)
        
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['file_id'] = file_id
            data['file_name'] = file_name
            
    except Exception as e:
        bot.reply_to(message, "Сталася помилка при завантаженні файлу.")

# Обробка опису книги
@bot.message_handler(state=BookStates.waiting_for_description)
def handle_description(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        file_id = data['file_id']
        file_name = data['file_name']
        description = message.text
        
        cursor.execute("INSERT INTO books (file_id, file_name, description) VALUES (?, ?, ?)",
                      (file_id, file_name, description))
        conn.commit()
        
        bot.reply_to(message, "Книгу успішно збережено!")
        bot.delete_state(message.from_user.id, message.chat.id)

# Команда пошуку
@bot.message_handler(commands=['search'])
def search_command(message):
    bot.reply_to(message, "Введіть назву книги або автора для пошуку:")
    bot.register_next_step_handler(message, search_books)

# Функція пошуку книг
def search_books(message):
    search_query = message.text.lower()
    cursor.execute("SELECT * FROM books WHERE LOWER(description) LIKE ?", ('%' + search_query + '%',))
    books = cursor.fetchall()
    
    if books:
        for book in books:
            file_id, file_name, description = book
            bot.send_message(message.chat.id, f"Знайдено книгу:\n{description}")
            bot.send_document(message.chat.id, file_id)
    else:
        bot.reply_to(message, "Книг за вашим запитом не знайдено.")

# Запуск бота
bot.infinity_polling()
