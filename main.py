from telebot import TeleBot, types
import sqlite3
import random
import time

bot = TeleBot("7505424553:AAH-gnl9ZaxiISnOE2OukqAKePcWWy4GZL8")
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
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
    exp_to_next_level INTEGER DEFAULT 500,
    gold INTEGER DEFAULT 100
)""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    item_name TEXT,
    item_type TEXT,
    effect TEXT,
    quantity INTEGER DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
)""")
conn.commit()

state = {}
BATTLE_STATES = {}

cursor.execute("""
CREATE TABLE IF NOT EXISTS deaths (
    user_id INTEGER PRIMARY KEY,
    death_time INTEGER
)""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS loot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_name TEXT,
    min_level INTEGER,
    chance REAL
)""")


loot_items = [
    ("Золотая монета", 1, 0.7),
    ("Редкий меч", 3, 0.3),
    ("Щит героя", 5, 0.2),
    ("Кольцо удачи", 2, 0.4),
    ("Зелье удачи", 1, 0.25),
    ("Зелье силы", 1, 0.3),
    ("Зелье восстановления", 1, 0.2),
    ("Эликсир здоровья", 1, 0.5)
]
for item in loot_items:
    cursor.execute("INSERT OR IGNORE INTO loot (item_name, min_level, chance) VALUES (?, ?, ?)", item)
conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS effects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    effect_type TEXT,
    power REAL,
    expires INTEGER,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
)""")
conn.commit()


def get_enemy(level):
    base_hp = 50 + (level-1)*20
    base_attack = 10 + (level-1)*3
    
    # Базовые враги для низких уровней
    enemies = [
        {"name": "Гоблин", "hp": base_hp, "attack": base_attack, "min_level": 1},
        {"name": "Тролль", "hp": base_hp*1.5, "attack": base_attack*1.2, "min_level": 1},
        {"name": "Скелет", "hp": base_hp*0.8, "attack": base_attack*1.1, "min_level": 1},
        {"name": "Волк", "hp": base_hp*0.7, "attack": base_attack*0.9, "min_level": 1},
        {"name": "Бандит", "hp": base_hp, "attack": base_attack, "min_level": 2},
    ]
    
    # Враги средних уровней (3-7)
    if level >= 3:
        enemies.extend([
            {"name": "Орк", "hp": base_hp*1.8, "attack": base_attack*1.5, "min_level": 3},
            {"name": "Призрак", "hp": base_hp*0.5, "attack": base_attack*1.8, "min_level": 3},
            {"name": "Грифон", "hp": base_hp*2, "attack": base_attack*1.7, "min_level": 4},
            {"name": "Рыцарь Тьмы", "hp": base_hp*2.5, "attack": base_attack*2, "min_level": 5},
            {"name": "Элементаль", "hp": base_hp*3, "attack": base_attack*1.5, "min_level": 5},
        ])
    
    # Сильные враги (8-12)
    if level >= 8:
        enemies.extend([
            {"name": "Демон", "hp": base_hp*3.5, "attack": base_attack*2.5, "min_level": 8},
            {"name": "Ледяной дракон", "hp": base_hp*4, "attack": base_attack*2.8, "min_level": 9},
            {"name": "Некромант", "hp": base_hp*2, "attack": base_attack*3.5, "min_level": 10},
            {"name": "Титан", "hp": base_hp*5, "attack": base_attack*3, "min_level": 11},
            {"name": "Архимаг", "hp": base_hp*3, "attack": base_attack*4, "min_level": 12},
        ])
    
    # Боссы (13+)
    if level >= 13:
        enemies.extend([
            {"name": "Король демонов", "hp": base_hp*6, "attack": base_attack*4, "min_level": 13},
            {"name": "Древний дракон", "hp": base_hp*8, "attack": base_attack*5, "min_level": 15},
            {"name": "Бог хаоса", "hp": base_hp*10, "attack": base_attack*6, "min_level": 18},
            {"name": "Повелитель бездны", "hp": base_hp*12, "attack": base_attack*7, "min_level": 20},
        ])
    
    # Фильтруем врагов по уровню
    available_enemies = [e for e in enemies if e["min_level"] <= level]
    
    # Взвешенный выбор - более сильные враги имеют меньший шанс появления
    weights = [1.0 / (e["hp"] * e["attack"] * 0.01) for e in available_enemies]
    total_weight = sum(weights)
    weights = [w / total_weight for w in weights]
    
    return random.choices(available_enemies, weights=weights, k=1)[0]

def calculate_escape_chance(user_id):
    cursor.execute("SELECT * FROM inventory WHERE user_id = ? AND item_name = 'Зелье удачи'", (user_id,))
    has_luck_potion = cursor.fetchone() is not None
    return 45 if has_luck_potion else 70

def get_revive_options(user_id):
    user = get_user(user_id)
    max_hp = user[10] * 10  # Выносливость * 10 = максимальное HP
    
    markup = types.InlineKeyboardMarkup()
    cursor.execute("SELECT death_time FROM deaths WHERE user_id = ?", (user_id,))
    death_time = cursor.fetchone()
    
    if death_time and (time.time() - death_time[0]) >= 300:  
        markup.add(types.InlineKeyboardButton("Возродиться бесплатно (полное HP)", callback_data="revive_free"))
    else:
        wait_time = 300 - (time.time() - death_time[0]) if death_time else 300
        markup.add(types.InlineKeyboardButton(
            f"Подождать {int(wait_time)} сек", 
            callback_data="revive_wait"
        ))  
    
    # Отнимаем 10% от максимального HP при возрождении через сон
    sleep_hp_loss = int(max_hp * 0.1)
    new_hp = max_hp - sleep_hp_loss
    markup.add(types.InlineKeyboardButton(
        f"Поспать (-10% HP, останется {new_hp}/{max_hp})", 
        callback_data="revive_sleep"
    ))  
    
    return markup


def give_loot(user_id, level):
    # Проверяем эффект удачи
    luck_multiplier = 1.0
    cursor.execute("SELECT power FROM effects WHERE user_id = ? AND effect_type = 'luck' AND expires > ?", 
                 (user_id, time.time()))
    if luck_effect := cursor.fetchone():
        luck_multiplier = luck_effect[0]
    
    # Увеличиваем шансы с учетом удачи
    cursor.execute("SELECT * FROM loot WHERE min_level <= ?", (level,))
    possible_loot = cursor.fetchall()
    
    weighted_loot = []
    for item in possible_loot:
        adjusted_chance = item[3] * luck_multiplier
        weighted_loot.append((item[0], item[1], item[2], adjusted_chance))
    

    total_chance = sum(item[3] for item in weighted_loot)
    rand = random.uniform(0, total_chance)
    current = 0
    
    for item in weighted_loot:
        current += item[3]
        if rand <= current:
            # Проверяем, есть ли уже такой предмет
            cursor.execute("SELECT * FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item[1]))
            existing = cursor.fetchone()
            
            if existing:
                # Увеличиваем количество
                cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE id = ?", (existing[0],))
            else:
                # Добавляем новый предмет
                cursor.execute("INSERT INTO inventory (user_id, item_name, item_type, effect) VALUES (?, ?, ?, ?)", 
                              (user_id, item[1], "loot", "обычный предмет"))
            
            conn.commit()
            return item[1]
    
    return None

@bot.callback_query_handler(lambda call: call.data.startswith("revive_"))
def handle_revive(call: types.CallbackQuery):
    user_id = call.from_user.id
    user = get_user(user_id)
    max_hp = user[10] * 10  # Максимальное HP
    
    try:
        if call.data == "revive_sleep":
            # Отнимаем 10% от максимального HP
            new_hp = max(1, int(max_hp * 0.9))  # Не менее 1 HP
            
            # Обновляем HP (выносливость = HP / 10)
            new_stamina = max(1, new_hp // 10)
            cursor.execute("UPDATE users SET stamina = ? WHERE user_id = ?", (new_stamina, user_id))
            
            cursor.execute("DELETE FROM deaths WHERE user_id = ?", (user_id,))
            conn.commit()
            
            msg = (f"💤 Вы поспали и потеряли 10% HP!\n"
                  f"❤️ Текущее HP: {new_hp}/{max_hp}\n"
                  f"Вы восстановили силы и готовы к новым приключениям!")
        
        elif call.data == "revive_free":
            # Полное восстановление HP
            cursor.execute("DELETE FROM deaths WHERE user_id = ?", (user_id,))
            conn.commit()
            msg = "🆓 Бесплатное возрождение! Ваше HP полностью восстановлено!"
        
        elif call.data == "revive_wait":
            cursor.execute("SELECT death_time FROM deaths WHERE user_id = ?", (user_id,))
            death_time = cursor.fetchone()[0]
            time_left = 300 - (time.time() - death_time)
            
            if time_left > 0:
                msg = f"⏳ До бесплатного возрождения осталось {int(time_left)} секунд"
            else:
                cursor.execute("DELETE FROM deaths WHERE user_id = ?", (user_id,))
                conn.commit()
                msg = "🆓 Время ожидания истекло! Вы возрождены бесплатно!"
        
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id)
        
        # Обновляем главное меню
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Профиль", callback_data="Профиль"),
                   types.InlineKeyboardButton("Магазин", callback_data="Магазин"),
                   types.InlineKeyboardButton("Бой", callback_data="start_battle"))
        bot.send_message(call.message.chat.id, "🏠 Главное меню", reply_markup=markup)
        
    except Exception as e:
        print(f"Ошибка в handle_revive: {str(e)}")
        bot.answer_callback_query(call.id, "Произошла ошибка при обработке запроса")


@bot.callback_query_handler(lambda call: call.data.startswith("battle_"))
def handle_battle_actions(call: types.CallbackQuery):
    user_id = call.from_user.id
    battle = BATTLE_STATES.get(user_id)
    if not battle:
        bot.answer_callback_query(call.id, "Бой завершен!")
        return

    user = get_user(user_id)
    enemy = battle['enemy']
    
    if call.data == "battle_attack":
        
        player_damage = user[7] + random.randint(1, 5)
        battle['enemy_hp'] -= player_damage
        
        
        enemy_damage = enemy['attack'] + random.randint(1, 3) - user[10]//2
        battle['user_hp'] -= max(enemy_damage, 0)
        
        
        if battle['enemy_hp'] <= 0:
            exp_gain = random.choices(
            [50, 100, 150],
            weights=[50, 40, 10]
        )[0]
            # Победа
            exp_gain = enemy['attack'] * 10
            gold_gain = random.randint(10, 50)
            loot = give_loot(user_id, user[13])
            
            # Обновляем опыт и золото
            cursor.execute("UPDATE users SET exp = exp + ?, gold = gold + ? WHERE user_id = ?",
                        (exp_gain, gold_gain, user_id))
            conn.commit()
            
            # Проверка повышения уровня
            new_level = check_level_up(user_id)
            level_up_msg = f"\n🎉 Поздравляем! Вы достигли уровня {new_level}!" if new_level else ""
            
            msg = (f"🏆 Победа!\n"
                f"Получено: {exp_gain} опыта и {gold_gain} золота\n"
                f"Добыча: {loot if loot else 'нет'}"
                f"{level_up_msg}")
            bot.edit_message_text(msg, call.message.chat.id, call.message.message_id)
            del BATTLE_STATES[user_id]
            return
            
        elif battle['user_hp'] <= 0:
            
            cursor.execute("INSERT OR REPLACE INTO deaths (user_id, death_time) VALUES (?, ?)",
                         (user_id, int(time.time())))
            conn.commit()
            
            markup = get_revive_options(user_id)
            bot.edit_message_text("☠️ Вы пали в бою!", call.message.chat.id, call.message.message_id, reply_markup=markup)
            del BATTLE_STATES[user_id]
            return
            
        show_battle_interface(call.message, user_id)
    
    elif call.data == "battle_flee":
        escape_chance = calculate_escape_chance(user_id)
        if random.randint(1, 100) <= escape_chance:
            bot.edit_message_text("🏃♂️ Вы успешно сбежали!", call.message.chat.id, call.message.message_id)
            del BATTLE_STATES[user_id]
        else:
            enemy_damage = enemy['attack'] + random.randint(1, 3)
            battle['user_hp'] -= enemy_damage
            bot.answer_callback_query(call.id, f"Не удалось сбежать! Получено урона: {enemy_damage}")
            show_battle_interface(call.message, user_id)

@bot.callback_query_handler(lambda call: call.data.startswith("revive_"))
def handle_revive(call: types.CallbackQuery):
    user_id = call.from_user.id
    user = get_user(user_id)
    msg = "Действие выполнено"  # Значение по умолчанию
    
    try:
        if call.data == "revive_sleep":
            cursor.execute("SELECT death_time FROM deaths WHERE user_id = ?", (user_id,))
            death_time = cursor.fetchone()[0]
            time_diff = time.time() - death_time
            
            if time_diff < 300:  # 5 минут
                new_hp = int(user[10] * 0.85)
                cursor.execute("UPDATE users SET stamina = ? WHERE user_id = ?", (new_hp//10, user_id))
                msg = f"💤 Вы поспали и потеряли 15% HP! Текущее HP: {new_hp}"
            else:
                msg = "💤 Вы полноценно отдохнули и не потеряли HP!"
            
            cursor.execute("DELETE FROM deaths WHERE user_id = ?", (user_id,))
            conn.commit()

        elif call.data == "revive_potion":
            # Логика для возрождения зельем
            cursor.execute("DELETE FROM deaths WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM inventory WHERE user_id = ? AND item_name = 'Зелье воскрешения'", (user_id,))
            conn.commit()
            msg = "⚗️ Вы использовали зелье воскрешения!"
            
        elif call.data == "revive_free":
            cursor.execute("DELETE FROM deaths WHERE user_id = ?", (user_id,))
            conn.commit()
            msg = "🆓 Бесплатное возрождение!"
            
        elif call.data == "revive_wait":
            msg = "⏳ Вам нужно подождать 5 минут для бесплатного возрождения"
            
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id)
        
    except Exception as e:
        print(f"Ошибка в handle_revive: {str(e)}")
        bot.answer_callback_query(call.id, "Произошла ошибка при обработке запроса")

    # Обновляем главное меню
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Профиль", callback_data="Профиль"),
               types.InlineKeyboardButton("Магазин", callback_data="Магазин"),
               types.InlineKeyboardButton("Бой", callback_data="start_battle"))
    bot.send_message(call.message.chat.id, "🏠 Главное меню", reply_markup=markup)



def get_exp_to_next_level(current_level):
    # Новая формула: 500 * level^1.5 (более плавный рост)
    return int(500 * (current_level ** 1.5))

def check_level_up(user_id):
    # Получаем множитель опыта
    exp_multiplier = 1.0
    cursor.execute("SELECT power FROM effects WHERE user_id = ? AND effect_type = 'luck' AND expires > ?", 
                 (user_id, time.time()))
    if luck_effect := cursor.fetchone():
        exp_multiplier = luck_effect[0]
    
    user = get_user(user_id)
    current_exp = user[14] * exp_multiplier  # Учитываем множитель
    
    if current_exp >= user[15]:
        new_level = user[13] + 1
        new_exp = current_exp - user[15]
        new_exp_needed = get_exp_to_next_level(new_level)
        
        # Бонусы за класс при повышении уровня
        class_bonus = {
            "Воин": {"strength": 2, "stamina": 1},
            "Лучник": {"agility": 2, "luck": 1},
            "Маг": {"intellect": 3, "agility": -1},
            "Вор": {"luck": 2, "agility": 1}
        }
        bonuses = class_bonus.get(user[6], {})
        
        # Обновляем характеристики
        update_query = """
            UPDATE users SET 
            level = ?,
            exp = ?,
            exp_to_next_level = ?,
            strength = strength + ?,
            agility = agility + ?,
            intellect = intellect + ?,
            stamina = stamina + ?,
            luck = luck + ?
            WHERE user_id = ?
        """
        cursor.execute(update_query, (
            new_level,
            new_exp,
            new_exp_needed,
            1 + bonuses.get('strength', 0),  # Базовое +1 и бонус класса
            1 + bonuses.get('agility', 0),
            1 + bonuses.get('intellect', 0),
            1 + bonuses.get('stamina', 0),
            1 + bonuses.get('luck', 0),
            user_id
        ))
        conn.commit()
        
        return new_level
    return None


def show_battle_interface(message, user_id):
    battle = BATTLE_STATES[user_id]
    enemy = battle["enemy"]
    user = get_user(user_id)
    
    # Проверяем активные эффекты
    cursor.execute("SELECT effect_type, power FROM effects WHERE user_id = ? AND expires > ?", 
                 (user_id, time.time()))
    effects = cursor.fetchall()
    effect_text = "\n".join([f"✨ {eff[0].capitalice()} +{int((eff[1]-1)*100)}%" for eff in effects])
    
    msg_text = (f"⚔️ Бой с {enemy['name']} (Ур. {user[13]})\n"
               f"❤️ Ваше здоровье: {battle['user_hp']}\n"
               f"💀 Здоровье врага: {battle['enemy_hp']}")
    
    if effect_text:
        msg_text += f"\n\nАктивные эффекты:\n{effect_text}"
        
   
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Атаковать", callback_data="battle_attack"),
               types.InlineKeyboardButton(f"Сбежать ({calculate_escape_chance(user_id)}%)", callback_data="battle_flee"))
    
    inventory = get_user_inventory(user_id)
    for item in inventory:
        if "Зелье" in item[2]:
            markup.add(types.InlineKeyboardButton(f"Использовать {item[2]}", callback_data=f"use_{item[0]}"))
    
    msg_text = (f"⚔️ Бой с {enemy['name']} (Ур. {user[13]})\n"
               f"❤️ Ваше здоровье: {battle['user_hp']}\n"
               f"💀 Здоровье врага: {battle['enemy_hp']}")
    bot.edit_message_text(msg_text, message.chat.id, message.message_id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "start_battle")
def start_battle(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    enemy = get_enemy(user[13])
    BATTLE_STATES[call.from_user.id] = {
        "enemy": enemy,
        "user_hp": user[10] * 10,
        "enemy_hp": enemy["hp"],
        "temp_buffs": {}
    }
    show_battle_interface(call.message, call.from_user.id)


def get_exp_to_next_level(current_level):
    # Новая формула: 500 * level^1.5 (более плавный рост)
    return int(500 * (current_level ** 1.5))

def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone()

def get_user_inventory(user_id):
    cursor.execute("SELECT * FROM inventory WHERE user_id = ?", (user_id,))
    return cursor.fetchall()

def progress_bar(current, total, length=10):
    percent = min(current / total, 1.0)
    return "🟩" * int(percent * length) + "⬜" * (length - int(percent * length))

@bot.message_handler(commands=["start"])
def start(message: types.Message):
    user = get_user(message.from_user.id)
    
    if user:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Магазин", callback_data="Магазин"),
                   types.InlineKeyboardButton("Профиль", callback_data="Профиль"),
                   types.InlineKeyboardButton("Главная", callback_data="Главная"))
        
        welcome_msg = (f"✨ <b>Добро пожаловать обратно, {user[4]}!</b> ✨\n\n"
                      f"🏆 Уровень: {user[13]} ({user[14]}/{user[15]})\n"
                      f"💰 Золото: {user[16]}\n\n"
                      f"🧬 Раса: {user[5]}\n🎯 Класс: {user[6]}\n\n"
                      f"💪 Сила: {user[7]}\n🏹 Ловкость: {user[8]}\n"
                      f"📚 Интеллект: {user[9]}\n🛡️ Выносливость: {user[10]}\n"
                      f"🍀 Удача: {user[11]}\n\n✨ Способности: {user[12]}")
        bot.send_message(message.chat.id, welcome_msg, parse_mode="HTML", reply_markup=markup)
    else:
        state[message.from_user.id] = {
            "name": None, "race": None, "class": None,
            "strength": 5, "agility": 5, "intellect": 5,
            "stamina": 5, "luck": 5, "abilities": [],
            "level": 1, "exp": 0, "exp_to_next_level": 500, "gold": 100
        }
        bot.send_message(message.chat.id, "🎮 <b>Добро пожаловать в игру!</b>\n\nВведите имя персонажа:", parse_mode="HTML")
        bot.register_next_step_handler(message, process_name_step)

def process_name_step(message: types.Message):
    state[message.from_user.id]["name"] = message.text
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Человек", callback_data="race:Человек"),
               types.InlineKeyboardButton("Эльф", callback_data="race:Эльф"),
               types.InlineKeyboardButton("Орк", callback_data="race:Орк"),
               types.InlineKeyboardButton("Гном", callback_data="race:Гном"))
    bot.send_message(message.chat.id, "Выберите расу:", reply_markup=markup)

@bot.callback_query_handler(lambda call: call.data.startswith("race:"))
def process_race(call: types.CallbackQuery):
    race = call.data.split(":")[1]
    state[call.from_user.id]["race"] = race
    stats = state[call.from_user.id]
    
    race_bonuses = {
        "Человек": "Все характеристики +1",
        "Эльф": "Ловкость +2, Интеллект +1",
        "Орк": "Сила +2, Выносливость +1",
        "Гном": "Интеллект +2, Удача +1"
    }
    
    bot.edit_message_text(
        f"🧬 Вы выбрали расу: <b>{race}</b>\n"
        f"✨ Бонусы: {race_bonuses[race]}\n\n"
        "Теперь выберите класс:",
        call.message.chat.id, 
        call.message.message_id,
        parse_mode="HTML"
    )
    
    markup = types.InlineKeyboardMarkup()
    classes = [
        ("Воин", "💪 Сила +2, Удар щитом"),
        ("Лучник", "🏹 Ловкость +2, Меткий выстрел"),
        ("Маг", "🔮 Интеллект +3, Огненный шар"),
        ("Вор", "🎲 Удача +2, Критический удар")
    ]
    for class_name, bonus in classes:
        markup.add(types.InlineKeyboardButton(
            f"{class_name} - {bonus}", 
            callback_data=f"class:{class_name}"
        ))
        
    bot.send_message(call.message.chat.id, 
        "🎯 <b>Выберите класс:</b>\n\n"
        "1. Воин - Сила +2, Удар щитом\n"
        "2. Лучник - Ловкость +2, Меткий выстрел\n"
        "3. Маг - Интеллект +3, Огненный шар\n"
        "4. Вор - Удача +2, Критический удар",
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.callback_query_handler(lambda call: call.data.startswith("class:"))
def process_class(call: types.CallbackQuery):
    class_ = call.data.split(":")[1]
    state[call.from_user.id]["class"] = class_
    stats = state[call.from_user.id]
    
    class_bonuses = {
        "Воин": {"strength": 2, "abilities": ["🛡 Удар щитом"]},
        "Лучник": {"agility": 2, "abilities": ["🎯 Меткий выстрел"]},
        "Маг": {"intellect": 3, "abilities": ["🔥 Огненный шар"]},
        "Вор": {"luck": 2, "abilities": ["💥 Критический удар"]}
    }
    
    bonuses = class_bonuses[class_]
    for stat, value in bonuses.items():
        if stat in stats:
            stats[stat] += value
        else:
            stats["abilities"] = value
    
    final_stats = (
        f"🧬 Раса: {stats['race']}\n"
        f"🎯 Класс: {class_}\n\n"
        f"💪 Сила: {stats['strength']}\n"
        f"🏹 Ловкость: {stats['agility']}\n"
        f"📚 Интеллект: {stats['intellect']}\n"
        f"🛡 Выносливость: {stats['stamina']}\n"
        f"🍀 Удача: {stats['luck']}\n\n"
        f"✨ Способности: {', '.join(stats['abilities'])}"
    )
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Подтвердить", callback_data="confirm"))
    
    bot.edit_message_text(
        f"🎉 Персонаж готов! Проверьте параметры:\n\n{final_stats}",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode="HTML"
    )
    
    user_data = state[call.from_user.id]
    cursor.execute("""INSERT INTO users 
        (user_id, username, first_name, last_name, name, race, class, strength, agility, intellect, stamina, luck, abilities, gold) 
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", 
        (
            call.from_user.id,
            call.from_user.username,
            call.from_user.first_name,
            call.from_user.last_name,
            user_data["name"],
            user_data["race"],
            class_,
            user_data["strength"],
            user_data["agility"],
            user_data["intellect"],
            user_data["stamina"],
            user_data["luck"],
            ", ".join(user_data["abilities"]),
            user_data["gold"]
        ))
    conn.commit()
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Магазин", callback_data="Магазин"),
               types.InlineKeyboardButton("Профиль", callback_data="Профиль"),
               types.InlineKeyboardButton("Главная", callback_data="Главная"))
    
    profile_msg = (f"🎉 Персонаж создан!\n\n📝 Имя: {user_data['name']}\n"
                  f"🧬 Раса: {user_data['race']}\n🎯 Класс: {class_}\n\n"
                  f"💪 Сила: {user_data['strength']}\n🏹 Ловкость: {user_data['agility']}\n"
                  f"📚 Интеллект: {user_data['intellect']}\n🛡️ Выносливость: {user_data['stamina']}\n"
                  f"🍀 Удача: {user_data['luck']}\n\n✨ Способности: {', '.join(user_data['abilities'])}")
    bot.edit_message_text(profile_msg, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call: types.CallbackQuery):
    user = get_user(call.from_user.id)
    if not user:
        bot.answer_callback_query(call.id, "Сначала зарегистрируйтесь через /start")
        return

    if call.data == "Главная":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Профиль", callback_data="Профиль"),
                   types.InlineKeyboardButton("Магазин", callback_data="Магазин"),
                   types.InlineKeyboardButton("Бой", callback_data="start_battle"))
        bot.edit_message_text(f"🏠 Главное меню\n\nПривет, {user[4]}!", call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    elif call.data == "Профиль":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Инвентарь", callback_data="Инвентарь"),
                   types.InlineKeyboardButton("Назад", callback_data="Главная"))
        
        profile_msg = (f"📊 Профиль {user[4]}\n\n"
                      f"🏆 Уровень: {user[13]}\n"
                      f"📈 Опыт: {user[14]}/{user[15]}\n"
                      f"💰 Золото: {user[16]}\n\n"
                      f"💪 Сила: {user[7]}\n🏹 Ловкость: {user[8]}\n"
                      f"📚 Интеллект: {user[9]}\n🛡️ Выносливость: {user[10]}\n"
                      f"🍀 Удача: {user[11]}\n\n"
                      f"{progress_bar(user[14], user[15])}")
        bot.edit_message_text(profile_msg, call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    elif call.data == "Магазин":
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("Зелье силы (100g)", callback_data="buy:strength_potion"),
            types.InlineKeyboardButton("Зелье ловкости (100g)", callback_data="buy:agility_potion")
        )
        markup.row(
            types.InlineKeyboardButton("Зелье удачи (150g)", callback_data="buy:luck_potion"),
            types.InlineKeyboardButton("Эликсир здоровья (200g)", callback_data="buy:heal_potion")
        )
        markup.add(types.InlineKeyboardButton("Назад", callback_data="Главная"))
        bot.edit_message_text(f"🛒 Магазин\n💰 Золото: {user[16]}", call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    elif call.data.startswith("buy:"):
        item_type = call.data.split(":")[1]
        prices = {
            "strength_potion": 100,
            "agility_potion": 100,
            "luck_potion": 150,
            "heal_potion": 200
        }
        
        if user[16] < prices[item_type]:
            bot.answer_callback_query(call.id, "Недостаточно золота!")
            return
        
        items = {
            "strength_potion": {"name": "Зелье силы", "effect": "💪 +50% силы на 30 минут"},
            "agility_potion": {"name": "Зелье ловкости", "effect": "🏃♂️ +50% ловкости на 30 минут"},
            "luck_potion": {"name": "Зелье удачи", "effect": "🍀 +100% удачи на 1 час"},
            "heal_potion": {"name": "Эликсир здоровья", "effect": "❤️ Полное восстановление здоровья"}
        }
        
        item = items[item_type]
        
        # Списание денег
        cursor.execute("UPDATE users SET gold = gold - ? WHERE user_id = ?", 
                    (prices[item_type], call.from_user.id))
        
        # Добавление в инвентарь
        cursor.execute("SELECT * FROM inventory WHERE user_id = ? AND item_name = ?", 
                    (call.from_user.id, item['name']))
        if existing := cursor.fetchone():
            cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE id = ?", (existing[0],))
        else:
            cursor.execute("INSERT INTO inventory (user_id, item_name, item_type, effect) VALUES (?,?,?,?)",
                        (call.from_user.id, item['name'], item_type, item['effect']))
        
        conn.commit()
        bot.answer_callback_query(call.id, f"Куплено {item['name']}!")
        handle_callbacks(call)
    
    elif call.data == "Инвентарь":
        inventory = get_user_inventory(call.from_user.id)
        markup = types.InlineKeyboardMarkup()
        for item in inventory:
            markup.add(types.InlineKeyboardButton(f"{item[2]} x{item[5]}", callback_data=f"item_{item[0]}"))
        markup.add(types.InlineKeyboardButton("Назад", callback_data="Профиль"))
        bot.edit_message_text("🎒 Инвентарь", call.message.chat.id, call.message.message_id, reply_markup=markup)
    
    elif call.data == "start_battle":
        enemy = random.choice([{"name": "Гоблин", "hp": 50, "attack": 8}, 
                             {"name": "Тролль", "hp": 100, "attack": 15}])
        BATTLE_STATES[call.from_user.id] = {
            "enemy": enemy,
            "user_hp": user[10] * 10,
            "enemy_hp": enemy["hp"],
            "temp_buffs": {}
        }
        show_battle_interface(call.message, call.from_user.id)

def show_battle_interface(message, user_id):
    battle = BATTLE_STATES[user_id]
    enemy = battle["enemy"]
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Атаковать", callback_data="battle_attack"),
               types.InlineKeyboardButton("Сбежать", callback_data="battle_flee"))
    
    for item in get_user_inventory(user_id):
        if "Зелье" in item[2]:
            markup.add(types.InlineKeyboardButton(f"Использовать {item[2]}", callback_data=f"use_{item[0]}"))
    
    msg_text = (f"⚔️ Бой с {enemy['name']}!\n"
               f"❤️ Ваше здоровье: {battle['user_hp']}\n"
               f"💀 Здоровье врага: {battle['enemy_hp']}")
    bot.edit_message_text(msg_text, message.chat.id, message.message_id, reply_markup=markup)

@bot.callback_query_handler(lambda call: call.data.startswith("use_"))
def use_item(call: types.CallbackQuery):
    item_id = int(call.data.split("_")[1])
    user_id = call.from_user.id
    inventory = get_user_inventory(user_id)
    item = next((i for i in inventory if i[0] == item_id), None)
    
    if not item:
        bot.answer_callback_query(call.id, "Предмет не найден!")
        return
    
    try:
        effect_msg = ""
        if "Зелье силы" in item[2]:
            expires = int(time.time()) + 300  # 5 минут
            cursor.execute("INSERT INTO effects (user_id, effect_type, power, expires) VALUES (?, ?, ?, ?)",
                         (user_id, "strength", 1.5, expires))
            effect_msg = "💪 Сила увеличена на 50% на 5 минут!"
            
        elif "Зелье ловкости" in item[2]:
            expires = int(time.time()) + 300  # 5 минут
            cursor.execute("INSERT INTO effects (user_id, effect_type, power, expires) VALUES (?, ?, ?, ?)",
                         (user_id, "agility", 1.5, expires))
            effect_msg = "🏃♂️ Ловкость увеличена на 50% на 5 минут!"
            
        elif "Зелье удачи" in item[2]:
            expires = int(time.time()) + 300  # 5 минут
            cursor.execute("INSERT INTO effects (user_id, effect_type, power, expires) VALUES (?, ?, ?, ?)",
                         (user_id, "luck", 2.0, expires))
            effect_msg = "🍀 Удача увеличена! Шанс лута и опыт +100% на 5 минут!"
            
        elif "Эликсир здоровья" in item[2]:
            cursor.execute("UPDATE users SET stamina = 5 + (level-1) WHERE user_id = ?", (user_id,))
            effect_msg = "❤️ Здоровье полностью восстановлено!"
        
        # Удаляем предмет
        if item[5] > 1:
            cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE id = ?", (item_id,))
        else:
            cursor.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
        conn.commit()
        
        bot.answer_callback_query(call.id, effect_msg)
        bot.send_message(call.message.chat.id, effect_msg)
        
    except Exception as e:
        print(f"Ошибка: {str(e)}")
        bot.answer_callback_query(call.id, "Ошибка использования предмета!")
        
        
        
        
if __name__ == "__main__":
    print("Бот запущен...")
    bot.polling(none_stop=True)
