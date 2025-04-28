from telebot import TeleBot
from telebot import types
import sqlite3

bot = TeleBot("7505424553:AAH-gnl9ZaxiISnOE2OukqAKePcWWy4GZL8")
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

# Создаем таблицу с новыми полями
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    name TEXT,
    race TEXT,
    class TEXT,
    strength INTEGER DEFAULT 5,
    agility INTEGER DEFAULT 5,
    intellect INTEGER DEFAULT 5,
    stamina INTEGER DEFAULT 5,
    luck INTEGER DEFAULT 5,
    abilities TEXT DEFAULT '',
    level INTEGER DEFAULT 1,
    exp INTEGER DEFAULT 0,
    exp_to_next_level INTEGER DEFAULT 500
)
"""
)
conn.commit()

state = {}

# Функция для определения опыта до следующего уровня
def get_exp_to_next_level(current_level):
    if current_level < 10:
        return 500
    elif current_level < 15:
        return 1000
    elif current_level < 30:
        return 5000
    else:
        return 10000

# Функция для создания прогресс-бара
def progress_bar(current, total, length=10):
    percent = min(current / total, 1.0)
    filled = int(percent * length)
    return "🟩" * filled + "⬜" * (length - filled)

@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if user:
        # Проверяем, есть ли новые поля в записи пользователя
        if len(user) <= 12:  # Если запись старая (без новых полей)
            # Обновляем запись пользователя, добавляя недостающие поля
            cursor.execute(
                """
                UPDATE users SET 
                strength = 5,
                agility = 5,
                intellect = 5,
                stamina = 5,
                luck = 5,
                abilities = '',
                level = 1,
                exp = 0,
                exp_to_next_level = 500
                WHERE user_id = ?
                """,
                (user_id,)
            )
            conn.commit()
            
            # Снова получаем обновленную запись
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()

        # Формируем красивое сообщение с характеристиками
        welcome_message = (
            f"✨ <b>Добро пожаловать обратно, {user[4]}!</b> ✨\n\n"
            f"🏆 <b>Уровень:</b> {user[13]} ({user[14]}/{user[15]})\n\n"
            f"🧬 <b>Раса:</b> {user[5]}\n"
            f"🎯 <b>Класс:</b> {user[6]}\n\n"
            f"<b>Характеристики:</b>\n"
            f"💪 Сила: {user[7]}\n"
            f"🏹 Ловкость: {user[8]}\n"
            f"📚 Интеллект: {user[9]}\n"
            f"🛡️ Выносливость: {user[10]}\n"
            f"🍀 Удача: {user[11]}\n\n"
            f"✨ <b>Способности:</b> {user[12]}"
        )
        bot.send_message(message.chat.id, welcome_message, parse_mode="HTML")
    else:
        state[user_id] = {
            "name": None, 
            "race": None, 
            "class": None,
            "strength": 5,
            "agility": 5,
            "intellect": 5,
            "stamina": 5,
            "luck": 5,
            "abilities": [],
            "level": 1,
            "exp": 0,
            "exp_to_next_level": 500
        }
        msg = bot.send_message(
            message.chat.id,
            "🎮 <b>Добро пожаловать в игру!</b> 🎮\n\n"
            "Давайте создадим вашего персонажа!\n\n"
            "📝 Введите имя вашего персонажа:",
            parse_mode="HTML"
        )
        bot.register_next_step_handler(msg, process_name_step)

def process_name_step(message: types.Message):
    name = message.text
    state[message.from_user.id]["name"] = name

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Человек", callback_data="race:Человек"))
    markup.add(types.InlineKeyboardButton("Эльф", callback_data="race:Эльф"))
    markup.add(types.InlineKeyboardButton("Орк", callback_data="race:Орк"))
    markup.add(types.InlineKeyboardButton("Гном", callback_data="race:Гном"))

    msg = bot.send_message(
        message.chat.id, 
        "Выберите расу:\n"
        "1. Человек (+1 ко всем статам)\n"
        "2. Эльф (+2 ловкость, +1 интеллект)\n"
        "3. Орк (+2 сила, +1 выносливость)\n"
        "4. Гном (+2 интеллект, +1 удача)", 
        reply_markup=markup
    )


@bot.callback_query_handler(lambda call: "race" in call.data)
def process_race_step(call: types.CallbackQuery):
    _, race = call.data.split(":")
    state[call.from_user.id]["race"] = race
    
    # Применяем бонусы расы
    user_stats = state[call.from_user.id]
    if race == "Человек":
        user_stats["strength"] += 1
        user_stats["agility"] += 1
        user_stats["intellect"] += 1
        user_stats["stamina"] += 1
        user_stats["luck"] += 1
    elif race == "Эльф":
        user_stats["agility"] += 2
        user_stats["intellect"] += 1
    elif race == "Орк":
        user_stats["strength"] += 2
        user_stats["stamina"] += 1
    elif race == "Гном":
        user_stats["intellect"] += 2
        user_stats["luck"] += 1

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Воин", callback_data="class:Воин"))
    markup.add(types.InlineKeyboardButton("Лучник", callback_data="class:Лучник"))
    markup.add(types.InlineKeyboardButton("Маг", callback_data="class:Маг"))  # Исправлено здесь
    markup.add(types.InlineKeyboardButton("Вор", callback_data="class:Вор"))

    bot.send_message(
        call.message.chat.id,
        "Выберите класс:\n"
        "1. Воин (Сила +2, Удар щитом)\n"
        "2. Лучник (Ловкость +2, Меткий выстрел)\n"
        "3. Маг (Интеллект +3, Огненный шар)\n"
        "4. Вор (Удача +2, Критический удар)",
        reply_markup=markup
    )


@bot.callback_query_handler(lambda call: "class" in call.data)
def process_class_step(call: types.CallbackQuery):
    _, class_ = call.data.split(":")
    state[call.from_user.id]["class"] = class_
    
    # Применяем бонусы класса
    user_stats = state[call.from_user.id]
    abilities = []
    
    if class_ == "Воин":
        user_stats["strength"] += 2
        abilities.append("Удар щитом")
    elif class_ == "Лучник":
        user_stats["agility"] += 2
        abilities.append("Меткий выстрел")
    elif class_ == "Маг":
        user_stats["intellect"] += 3
        abilities.append("Огненный шар")
    elif class_ == "Вор":
        user_stats["luck"] += 2
        abilities.append("Критический удар")
    
    state[call.from_user.id]["abilities"] = ", ".join(abilities)
    
    # Сохраняем в базу данных
    cursor.execute(
        "INSERT INTO users (user_id, username, name, race, class, strength, agility, intellect, stamina, luck, abilities) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            call.from_user.id,
            call.from_user.username,
            state[call.from_user.id]["name"],
            state[call.from_user.id]["race"],
            state[call.from_user.id]["class"],
            state[call.from_user.id]["strength"],
            state[call.from_user.id]["agility"],
            state[call.from_user.id]["intellect"],
            state[call.from_user.id]["stamina"],
            state[call.from_user.id]["luck"],
            state[call.from_user.id]["abilities"],
        ),
    )
    conn.commit()

    # Формируем сообщение с характеристиками
    stats = state[call.from_user.id]
    message_text = (
        f"Регистрация завершена!\n\n"
        f"Имя: {stats['name']}\n"
        f"Раса: {stats['race']}\n"
        f"Класс: {class_}\n\n"
        f"Характеристики:\n"
        f"Сила: {stats['strength']}\n"
        f"Ловкость: {stats['agility']}\n"
        f"Интеллект: {stats['intellect']}\n"
        f"Выносливость: {stats['stamina']}\n"
        f"Удача: {stats['luck']}\n\n"
        f"Способности: {', '.join(abilities)}"
    )

    bot.send_message(call.message.chat.id, message_text)


if __name__ == "__main__":
    print("Бот запущен...")
    bot.polling(none_stop=True)