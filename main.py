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

cursor.execute("""
CREATE TABLE IF NOT EXISTS guild_quests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    description TEXT,
    target TEXT,
    required_count INTEGER,
    reward_reputation INTEGER,
    reward_gold INTEGER,
    reward_exp INTEGER,
    required_level INTEGER
)""")
conn.commit()

cursor.execute("""
CREATE TABLE IF NOT EXISTS guild (
    user_id INTEGER PRIMARY KEY,
    reputation INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    current_quest INTEGER,
    quest_progress INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
)""")


@bot.callback_query_handler(func=lambda call: call.data == "guild_quests")
def show_quests(call):
    user_id = call.from_user.id
    
    
    cursor.execute("INSERT OR IGNORE INTO guild (user_id) VALUES (?)", (user_id,))
    conn.commit()
    
    cursor.execute("SELECT level FROM guild WHERE user_id = ?", (user_id,))
    guild_level_row = cursor.fetchone()
    guild_level = guild_level_row[0] if guild_level_row else 1
    
    cursor.execute("SELECT * FROM guild_quests WHERE required_level <= ?", (guild_level,))
    quests = cursor.fetchall()
    
    quest_list = "\n".join([f"{idx}. {q[1]} (+{q[5]} репутации)" for idx, q in enumerate(quests, 1)])
    
    msg = f"📜 *Доступные задания*\n{quest_list}\n\nВыберите номер задания:"
    
    markup = types.InlineKeyboardMarkup()
    buttons = [types.InlineKeyboardButton(str(i), callback_data=f"quest_{q[0]}") for i, q in enumerate(quests, 1)]
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("Назад", callback_data="Гильдия"))
    
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)

try:
    cursor.execute("SELECT current_quest FROM guild LIMIT 1")
except sqlite3.OperationalError:
    
    cursor.execute("ALTER TABLE guild ADD COLUMN current_quest INTEGER")
    conn.commit()

@bot.callback_query_handler(func=lambda call: call.data == "Гильдия")
def guild_menu(call):
    user_id = call.from_user.id
    cursor.execute("SELECT reputation, level, current_quest, quest_progress FROM guild WHERE user_id = ?", (user_id,))
    guild_data = cursor.fetchone() or (0, 1, None, 0)
    
    msg = f"""🏰 *Гильдия приключений*
    
📊 Ваша репутация: {guild_data[0]}/150
⭐ Уровень гильдии: {guild_data[1]}"""
    
    if guild_data[2]:
        cursor.execute("SELECT title, target, required_count FROM guild_quests WHERE id = ?", (guild_data[2],))
        quest = cursor.fetchone()
        msg += f"\n\n📌 Активное задание: {quest[0]}\n➤ Прогресс: {guild_data[3]}/{quest[2]} {quest[1]}"
    
    markup = types.InlineKeyboardMarkup()
    if guild_data[2]:
        markup.add(types.InlineKeyboardButton("Отменить задание ❌", callback_data="cancel_quest"))
        markup.add(types.InlineKeyboardButton("Проверить прогресс 🔄", callback_data="check_progress"))
    else:
        markup.add(types.InlineKeyboardButton("Выбрать задание 📜", callback_data="guild_quests"))
    markup.add(types.InlineKeyboardButton("Назад ↩️", callback_data="Главная"))
    
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_progress")
def check_progress(call):
    user_id = call.from_user.id
    cursor.execute("SELECT current_quest, quest_progress FROM guild WHERE user_id = ?", (user_id,))
    current_quest, progress = cursor.fetchone()
    
    if current_quest is None:
        bot.answer_callback_query(call.id, "У вас нет активного задания!")
        return
    
    cursor.execute("SELECT title, required_count FROM guild_quests WHERE id = ?", (current_quest,))
    quest = cursor.fetchone()
    
    if quest is None:
        bot.answer_callback_query(call.id, "Задание не найдено!")
        return
    
    msg = f"📌 Активное задание: {quest[0]}\n➤ Прогресс: {progress}/{quest[1]}"
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "cancel_quest")
def cancel_quest(call):
    user_id = call.from_user.id
    cursor.execute("UPDATE guild SET current_quest = NULL, quest_progress = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    bot.answer_callback_query(call.id, "🗑 Задание отменено!")
    guild_menu(call)

@bot.callback_query_handler(func=lambda call: call.data == "guild_quests")
def show_quests(call):
    user_id = call.from_user.id
    
    
    cursor.execute("INSERT OR IGNORE INTO guild (user_id) VALUES (?)", (user_id,))
    conn.commit()
    
    cursor.execute("SELECT level FROM guild WHERE user_id = ?", (user_id,))
    guild_level_row = cursor.fetchone()
    
    
    guild_level = guild_level_row[0] if guild_level_row else 1
    
    cursor.execute("SELECT * FROM guild_quests WHERE required_level <= ?", (guild_level,))
    quests = cursor.fetchall()
    
    quest_list = "\n".join([f"{idx}. {q[2]} (+{q[4]} репутации)" for idx, q in enumerate(quests, 1)])
    
    msg = f"""📜 *Доступные задания*
{quest_list}
    
Выберите номер задания:"""
    
    markup = types.InlineKeyboardMarkup()
    buttons = [types.InlineKeyboardButton(str(i), callback_data=f"quest_{q[0]}") for i, q in enumerate(quests, 1)]
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("Назад", callback_data="Гильдия"))
    
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, 
                        parse_mode="Markdown", reply_markup=markup)


def check_quests(user_id, enemy_name):
    cursor.execute("SELECT completed_quests FROM guild WHERE user_id = ?", (user_id,))
    quests = cursor.fetchone()[0].split(",") if cursor.fetchone() else []
    
    for quest_id in quests:
        cursor.execute("SELECT * FROM guild_quests WHERE id = ?", (quest_id,))
        quest = cursor.fetchone()
        if "гоблин" in quest[3].lower() and "гоблин" in enemy_name.lower():
            cursor.execute("UPDATE guild SET reputation = reputation + ? WHERE user_id = ?", 
                           (quest[5], user_id))
            conn.commit()
            return f"✅ Выполнено задание: {quest[2]}!"
    return ""
try:
    cursor.execute("ALTER TABLE guild ADD COLUMN completed_quests TEXT DEFAULT ''")
    conn.commit()
    print("Столбец completed_quests успешно добавлен.")
except sqlite3.OperationalError as e:
    print(f"Ошибка при добавлении столбца: {e}")
def check_guild_level(user_id):
    cursor.execute("SELECT reputation, level FROM guild WHERE user_id = ?", (user_id,))
    rep, level = cursor.fetchone()
    
    required = 150 * level
    if rep >= required:
        new_level = level + 1
        cursor.execute("UPDATE guild SET level = ?, reputation = ? WHERE user_id = ?", 
                     (new_level, rep - required, user_id))
        conn.commit()
        return f"🎉 Поздравляем! Вы достигли {new_level} уровня гильдии!"
    return ""





@bot.callback_query_handler(lambda call: call.data.startswith("quest_"))
def show_quest_details(call):
    quest_id = int(call.data.split("_")[1])
    cursor.execute("SELECT * FROM guild_quests WHERE id = ?", (quest_id,))
    quest = cursor.fetchone()
    
    if quest is None:
        bot.answer_callback_query(call.id, "Задание не найдено!")
        return
    
    
    if len(quest) < 8:
        bot.answer_callback_query(call.id, "Ошибка: данные задания некорректны.")
        return
    
    msg = f"""📖 *{quest[2]}*
🔹 *Описание:* {quest[3]}
🔹 *Награда:*
   - Репутация: +{quest[5]}
   - Золото: {quest[6]}
   - Опыт: {quest[7]}
    
Принять задание?"""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Принять", callback_data=f"accept_quest_{quest_id}"),
               types.InlineKeyboardButton("Отмена", callback_data="guild_quests"))
    
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, 
                        parse_mode="Markdown", reply_markup=markup)

def update_quest_progress(user_id, enemy_type):
    cursor.execute("SELECT current_quest, quest_progress FROM guild WHERE user_id = ?", (user_id,))
    quest_id, progress = cursor.fetchone()
    
    if quest_id:
        cursor.execute("SELECT target, required_count FROM guild_quests WHERE id = ?", (quest_id,))
        target, required = cursor.fetchone()
        
        if target in enemy_type:
            progress += 1
            cursor.execute("UPDATE guild SET quest_progress = ? WHERE user_id = ?", (progress, user_id))
            conn.commit()
            
            if progress >= required:
                cursor.execute("SELECT reward_reputation, reward_gold, reward_exp FROM guild_quests WHERE id = ?", (quest_id,))
                rep, gold, exp = cursor.fetchone()
                cursor.execute("UPDATE guild SET current_quest = NULL, quest_progress = 0, reputation = reputation + ? WHERE user_id = ?", (rep, user_id))
                cursor.execute("UPDATE users SET gold = gold + ?, exp = exp + ? WHERE user_id = ?", (gold, exp, user_id))
                conn.commit()
                return f"🏆 Задание выполнено! +{rep} репутации, +{gold} золота, +{exp} опыта"
    return ""




@bot.callback_query_handler(lambda call: call.data.startswith("quest_"))
def accept_quest(call):
    quest_id = int(call.data.split("_")[1])  # Получаем ID задания
    user_id = call.from_user.id
    
    cursor.execute("SELECT * FROM guild_quests WHERE id = ?", (quest_id,))
    quest = cursor.fetchone()
    
    if quest is None:
        bot.answer_callback_query(call.id, "Задание не найдено!")
        return
    
    # Убедитесь, что у пользователя нет активного задания
    cursor.execute("SELECT current_quest FROM guild WHERE user_id = ?", (user_id,))
    if cursor.fetchone()[0]:
        bot.answer_callback_query(call.id, "⚠️ У вас уже есть активное задание!")
        return
    
    # Устанавливаем задание как текущее
    cursor.execute("UPDATE guild SET current_quest = ?, quest_progress = 0 WHERE user_id = ?", (quest_id, user_id))
    conn.commit()
    bot.answer_callback_query(call.id, "✅ Задание принято!")
    guild_menu(call)
    
    
    cursor.execute("UPDATE guild SET current_quest = ?, quest_progress = 0 WHERE user_id = ?", (quest_id, user_id))
    conn.commit()
    bot.answer_callback_query(call.id, "✅ Задание принято!")
    guild_menu(call)
    
    
    cursor.execute("UPDATE guild SET current_quest = ?, quest_progress = 0 WHERE user_id = ?", (quest_id, user_id))
    conn.commit()
    bot.answer_callback_query(call.id, "✅ Задание принято!")
    guild_menu(call)

    


def check_quests(user_id, enemy_name):
    
    cursor.execute("SELECT completed_quests FROM guild WHERE user_id = ?", (user_id,))
    quests = [q for q in (cursor.fetchone()[0] or "").split(",") if q]
    
    for quest_id in quests:
        cursor.execute("SELECT * FROM guild_quests WHERE id = ?", (quest_id,))
        quest = cursor.fetchone()
        
        if "гоблин" in quest[3].lower() and "гоблин" in enemy_name.lower():
            cursor.execute("UPDATE guild SET reputation = reputation + ? WHERE user_id = ?", 
                         (quest[5], user_id))
            conn.commit()
            return f"✅ Выполнено задание: {quest[2]}!"
    return ""

@bot.callback_query_handler(func=lambda call: call.data == "Гильдия")
def guild_menu(call):
    user_id = call.from_user.id
    
    

    cursor.execute("INSERT OR IGNORE INTO guild (user_id) VALUES (?)", (user_id,))
    conn.commit()
    
    cursor.execute("SELECT reputation, level FROM guild WHERE user_id = ?", (user_id,))
    guild_data = cursor.fetchone()
    
    msg = f"""🏰 *Гильдия приключений*
📊 Ваша репутация: {guild_data[0]}/150
⭐ Уровень гильдии: {guild_data[1]}
    
Выберите действие:"""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Выбрать задание", callback_data="guild_quests"))
    markup.add(types.InlineKeyboardButton("Назад", callback_data="Главная"))
    
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, 
                        parse_mode="Markdown", reply_markup=markup)

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
    
    
    enemies = [
        {"name": "Гоблин", "hp": base_hp, "attack": base_attack, "min_level": 1},
        {"name": "Тролль", "hp": base_hp*1.5, "attack": base_attack*1.2, "min_level": 1},
        {"name": "Скелет", "hp": base_hp*0.8, "attack": base_attack*1.1, "min_level": 1},
        {"name": "Волк", "hp": base_hp*0.7, "attack": base_attack*0.9, "min_level": 1},
        {"name": "Бандит", "hp": base_hp, "attack": base_attack, "min_level": 2},
    ]
    
    
    if level >= 3:
        enemies.extend([
            {"name": "Орк", "hp": base_hp*1.8, "attack": base_attack*1.5, "min_level": 3},
            {"name": "Призрак", "hp": base_hp*0.5, "attack": base_attack*1.8, "min_level": 3},
            {"name": "Грифон", "hp": base_hp*2, "attack": base_attack*1.7, "min_level": 4},
            {"name": "Рыцарь Тьмы", "hp": base_hp*2.5, "attack": base_attack*2, "min_level": 5},
            {"name": "Элементаль", "hp": base_hp*3, "attack": base_attack*1.5, "min_level": 5},
        ])
    
    
    if level >= 8:
        enemies.extend([
            {"name": "Демон", "hp": base_hp*3.5, "attack": base_attack*2.5, "min_level": 8},
            {"name": "Ледяной дракон", "hp": base_hp*4, "attack": base_attack*2.8, "min_level": 9},
            {"name": "Некромант", "hp": base_hp*2, "attack": base_attack*3.5, "min_level": 10},
            {"name": "Титан", "hp": base_hp*5, "attack": base_attack*3, "min_level": 11},
            {"name": "Архимаг", "hp": base_hp*3, "attack": base_attack*4, "min_level": 12},
        ])
    
   
    if level >= 13:
        enemies.extend([
            {"name": "Король демонов", "hp": base_hp*6, "attack": base_attack*4, "min_level": 13},
            {"name": "Древний дракон", "hp": base_hp*8, "attack": base_attack*5, "min_level": 15},
            {"name": "Бог хаоса", "hp": base_hp*10, "attack": base_attack*6, "min_level": 18},
            {"name": "Повелитель бездны", "hp": base_hp*12, "attack": base_attack*7, "min_level": 20},
        ])
    
    
    available_enemies = [e for e in enemies if e["min_level"] <= level]
    
    
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
    max_hp = user[10] * 10  
    
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
    
    
    sleep_hp_loss = int(max_hp * 0.1)
    new_hp = max_hp - sleep_hp_loss
    markup.add(types.InlineKeyboardButton(
        f"Поспать (-10% HP, останется {new_hp}/{max_hp})", 
        callback_data="revive_sleep"
    ))  
    
    return markup


def give_loot(user_id, level):
    
    luck_multiplier = 1.0
    cursor.execute("SELECT power FROM effects WHERE user_id = ? AND effect_type = 'luck' AND expires > ?", 
                 (user_id, time.time()))
    if luck_effect := cursor.fetchone():
        luck_multiplier = luck_effect[0]
    
    
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
            
            cursor.execute("SELECT * FROM inventory WHERE user_id = ? AND item_name = ?", (user_id, item[1]))
            existing = cursor.fetchone()
            
            if existing:
                
                cursor.execute("UPDATE inventory SET quantity = quantity + 1 WHERE id = ?", (existing[0],))
            else:
                
                cursor.execute("INSERT INTO inventory (user_id, item_name, item_type, effect) VALUES (?, ?, ?, ?)", 
                              (user_id, item[1], "loot", "обычный предмет"))
            
            conn.commit()
            return item[1]
    
    return None

@bot.callback_query_handler(lambda call: call.data.startswith("revive_"))
def handle_revive(call: types.CallbackQuery):
    user_id = call.from_user.id
    user = get_user(user_id)
    max_hp = user[10] * 10  
    
    try:
        if call.data == "revive_sleep":
            
            new_hp = max(1, int(max_hp * 0.9))  
            
            
            new_stamina = max(1, new_hp // 10)
            cursor.execute("UPDATE users SET stamina = ? WHERE user_id = ?", (new_stamina, user_id))
            
            cursor.execute("DELETE FROM deaths WHERE user_id = ?", (user_id,))
            conn.commit()
            
            msg = (f"💤 Вы поспали и потеряли 10% HP!\n"
                  f"❤️ Текущее HP: {new_hp}/{max_hp}\n"
                  f"Вы восстановили силы и готовы к новым приключениям!")
        
        elif call.data == "revive_free":
           
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
        
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Гильдия", callback_data="Гильдия"),
                types.InlineKeyboardButton("Профиль", callback_data="Профиль"),
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
            
            exp_gain = enemy['attack'] * 10
            gold_gain = random.randint(10, 50)
            loot = give_loot(user_id, user[13])
            quest_result = check_quests(user_id, enemy['name'])
            level_up_msg = check_guild_level(user_id)

            msg = (f"🏆 Победа!\n"
                f"{quest_result}\n"
                f"{level_up_msg}\n"
                f"Получено: {exp_gain} опыта и {gold_gain} золота\n"
                f"Добыча: {loot if loot else 'нет'}")
            
            
            cursor.execute("UPDATE users SET exp = exp + ?, gold = gold + ? WHERE user_id = ?",
                        (exp_gain, gold_gain, user_id))
            conn.commit()
            
            
            new_level = check_level_up(user_id)
            level_up_msg = f"\n🎉 Поздравляем! Вы достигли уровня {new_level}!" if new_level else ""
            
            markup = types.InlineKeyboardMarkup()  
            markup.add(types.InlineKeyboardButton("На главную", callback_data="Главная"))
            
            msg = (f"🏆 Победа!\n"
                f"Получено: {exp_gain} опыта и {gold_gain} золота\n"
                f"Добыча: {loot if loot else 'нет'}"
                f"{level_up_msg}")
                
            bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup)  
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
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("На главную", callback_data="Главная"))
            bot.edit_message_text("🏃♂️ Вы успешно сбежали!", 
                                call.message.chat.id, 
                                call.message.message_id,
                                reply_markup=markup)
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
    msg = "Действие выполнено"  
    
    try:
        if call.data == "revive_sleep":
            cursor.execute("SELECT death_time FROM deaths WHERE user_id = ?", (user_id,))
            death_time = cursor.fetchone()[0]
            time_diff = time.time() - death_time
            
            if time_diff < 300:  
                new_hp = int(user[10] * 0.85)
                cursor.execute("UPDATE users SET stamina = ? WHERE user_id = ?", (new_hp//10, user_id))
                msg = f"💤 Вы поспали и потеряли 15% HP! Текущее HP: {new_hp}"
            else:
                msg = "💤 Вы полноценно отдохнули и не потеряли HP!"
            
            cursor.execute("DELETE FROM deaths WHERE user_id = ?", (user_id,))
            conn.commit()

        elif call.data == "revive_potion":
            
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

    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Гильдия", callback_data="Гильдия"),
           types.InlineKeyboardButton("Профиль", callback_data="Профиль"),
           types.InlineKeyboardButton("Магазин", callback_data="Магазин"),
           types.InlineKeyboardButton("Бой", callback_data="start_battle"))
    bot.send_message(call.message.chat.id, "🏠 Главное меню", reply_markup=markup)



def get_exp_to_next_level(current_level):
    if current_level < 5:
        return 500
    elif current_level < 10:
        return 700
    else:
        return 1000
    
def get_exp_requirements(level):
    return 500 * (1.5 ** (level-1))

def check_level_up(user_id):
    user = get_user(user_id)
    required = get_exp_requirements(user[13])
    
    if user[14] >= required:
        new_level = user[13] + 1
        class_ = user[6]
        
        
        updates = {
            'strength': 0,
            'agility': 0,
            'intellect': 0,
            'stamina': 1,  
            'luck': 0
        }
        
        
        if class_ == 'Воин':
            updates['strength'] = 2
        elif class_ == 'Лучник':
            updates['agility'] = 2
        elif class_ == 'Маг':
            updates['intellect'] = 2
        elif class_ == 'Вор':
            updates['luck'] = 2
        
        
        cursor.execute(f"""UPDATE users SET
            level = ?,
            exp = exp - ?,
            exp_to_next_level = ?,
            strength = strength + ?,
            agility = agility + ?,
            intellect = intellect + ?,
            stamina = stamina + ?,
            luck = luck + ?
            WHERE user_id = ?""",
            (new_level, 
             required, 
             get_exp_requirements(new_level),
             updates['strength'],
             updates['agility'],
             updates['intellect'],
             updates['stamina'],
             updates['luck'],
             user_id))
        
        conn.commit()
        
        
        bonus_text = []
        if updates['strength']: bonus_text.append(f"💪 Сила +{updates['strength']}")
        if updates['agility']: bonus_text.append(f"🏹 Ловкость +{updates['agility']}")
        if updates['intellect']: bonus_text.append(f"📚 Интеллект +{updates['intellect']}")
        if updates['luck']: bonus_text.append(f"🍀 Удача +{updates['luck']}")
        bonus_text.append(f"❤️ Выносливость +{updates['stamina']} (+{updates['stamina']*10} HP)")
        
        return {
            'new_level': new_level,
            'bonuses': "\n".join(bonus_text)
        }
    return None

def show_battle_interface(message, user_id):
    battle = BATTLE_STATES[user_id]
    enemy = battle["enemy"]
    user = get_user(user_id)
    
    
    cursor.execute("SELECT effect_type, power FROM effects WHERE user_id = ? AND expires > ?", 
                 (user_id, time.time()))
    effects = cursor.fetchall()
    effect_text = "\n".join([f"✨ {eff[0].capitalize()} +{int((eff[1]-1)*100)}%" for eff in effects])
    
    msg_text = (f"⚔️ Бой с {enemy['name']} (Ур. {user[13]})\n"
               f"❤️ Ваше здоровье: {battle['user_hp']}/{user[10] * 10}\n"
               f"💀 Здоровье врага: {battle['enemy_hp']}/{enemy['hp']}")
    
    if effect_text:
        msg_text += f"\n\nАктивные эффекты:\n{effect_text}"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Атаковать", callback_data="battle_attack"),
               types.InlineKeyboardButton(f"Сбежать ({calculate_escape_chance(user_id)}%)", callback_data="battle_flee"))
    
    
    inventory = get_user_inventory(user_id)
    potion_buttons = []
    for item in inventory:
        if "Зелье" in item[2] or "Эликсир" in item[2]:
            potion_buttons.append(types.InlineKeyboardButton(f"⚗️ {item[2]} x{item[5]}", callback_data=f"use_{item[0]}"))
    
    
    for i in range(0, len(potion_buttons), 2):
        if i+1 < len(potion_buttons):
            markup.row(potion_buttons[i], potion_buttons[i+1])
        else:
            markup.add(potion_buttons[i])
    
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




def get_user(user_id):
    cursor.execute("""SELECT *, 
        (SELECT GROUP_CONCAT(effect_type || ':' || power) 
         FROM effects 
         WHERE user_id = ? AND expires > ?) as active_effects
        FROM users WHERE user_id = ?""",
        (user_id, time.time(), user_id))
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

    
    if call.data.startswith("use_"):
        item_id = int(call.data.split("_")[1])
        user_id = call.from_user.id
        inventory = get_user_inventory(user_id)
        item = next((i for i in inventory if i[0] == item_id), None)
        
        if not item:
            bot.answer_callback_query(call.id, "Предмет не найден!")
            return
        
        try:
            effect_msg = ""
            battle = BATTLE_STATES.get(user_id)
            user = get_user(user_id)
            
            if "Зелье силы" in item[2]:
                expires = int(time.time()) + 600  
                cursor.execute("INSERT INTO effects (user_id, effect_type, power, expires) VALUES (?, ?, ?, ?)",
                             (user_id, "strength", 1.5, expires))
                effect_msg = "💪 Сила увеличена на 50% на 10 минут!"
                
            elif "Зелье ловкости" in item[2]:
                expires = int(time.time()) + 600 
                cursor.execute("INSERT INTO effects (user_id, effect_type, power, expires) VALUES (?, ?, ?, ?)",
                             (user_id, "agility", 1.5, expires))
                effect_msg = "🏃♂️ Ловкость увеличена на 50% на 10 минут!"
                
            elif "Зелье удачи" in item[2]:
                expires = int(time.time()) + 600  
                cursor.execute("INSERT INTO effects (user_id, effect_type, power, expires) VALUES (?, ?, ?, ?)",
                             (user_id, "luck", 2.0, expires))
                effect_msg = "🍀 Удача увеличена! Шанс лута и опыт +100% на 10 минут!"
                
            elif "Эликсир здоровья" in item[2]:
                if battle:
                    max_hp = user[10] * 10
                    battle['user_hp'] = max_hp
                    effect_msg = "❤️ Здоровье полностью восстановлено в бою!"
                else:
                    cursor.execute("UPDATE users SET stamina = ? WHERE user_id = ?", (user[10], user_id))
                    effect_msg = "❤️ Здоровье полностью восстановлено!"
            
            
            if item[5] > 1:
                cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE id = ?", (item_id,))
            else:
                cursor.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
            conn.commit()
            
            bot.answer_callback_query(call.id, effect_msg)
            
            
            if battle:
                show_battle_interface(call.message, user_id)
            else:
                bot.send_message(call.message.chat.id, effect_msg)
            return
            
        except Exception as e:
            print(f"Ошибка: {str(e)}")
            bot.answer_callback_query(call.id, "Ошибка использования предмета!")
            return

    
    elif call.data == "Главная":
                markup = types.InlineKeyboardMarkup()
                markup.row(
                    types.InlineKeyboardButton("Профиль", callback_data="Профиль"),
                    types.InlineKeyboardButton("Магазин", callback_data="Магазин")
                )
                markup.row(
                    types.InlineKeyboardButton("Гильдия", callback_data="Гильдия"),
                    types.InlineKeyboardButton("Бой", callback_data="start_battle")
                )
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
        
        
        cursor.execute("UPDATE users SET gold = gold - ? WHERE user_id = ?", 
                    (prices[item_type], call.from_user.id))
        
        
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

def apply_effect(user_id, effect_type, power, duration):
    """Применяет эффект к пользователю"""
    try:
        expires = int(time.time()) + duration
        cursor.execute("""
            INSERT INTO effects (user_id, effect_type, power, expires)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, effect_type) DO UPDATE SET
                power = excluded.power,
                expires = excluded.expires
        """, (user_id, effect_type, power, expires))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error applying effect: {str(e)}")

ITEM_HANDLERS = {
    'heal_potion': lambda user, battle: {
        'heal': user[10]*10,
        'message': "❤️ Здоровье полностью восстановлено!"
    },
    'strength_potion': lambda user, battle: {
        'effect': ('strength', 1.5, 600),
        'message': "💪 Сила увеличена на 50% на 10 минут!"
    }
}


@bot.callback_query_handler(lambda call: call.data.startswith("use_"))
def handle_item_use(call: types.CallbackQuery):
    user_id = call.from_user.id
    item_id = int(call.data.split("_")[1])
    inventory = get_user_inventory(user_id)
    item = next((i for i in inventory if i[0] == item_id), None)
    
    if not item:
        bot.answer_callback_query(call.id, "Предмет не найден!")
        return

    try:
        effect_msg = ""
        battle = BATTLE_STATES.get(user_id)
        user = get_user(user_id)
        
        
        handler = ITEM_HANDLERS.get(item[3])  
        if handler:
            effect = handler(user, battle)
            if effect.get('heal'):
                battle['user_hp'] = min(battle['user_hp'] + effect['heal'], user[10]*10)
                effect_msg = effect['message']
            if effect.get('effect'):
                apply_effect(user_id, *effect['effect'])
                effect_msg = effect['message']
        else:
            
            if "Зелье силы" in item[2]:
                apply_effect(user_id, "strength", 1.5, 600)
                effect_msg = "💪 Сила увеличена на 50% на 10 минут!"
            elif "Зелье ловкости" in item[2]:
                apply_effect(user_id, "agility", 1.5, 600)
                effect_msg = "🏃♂️ Ловкость увеличена на 50% на 10 минут!"
            elif "Зелье удачи" in item[2]:
                apply_effect(user_id, "luck", 2.0, 600)
                effect_msg = "🍀 Удача увеличена! Шанс лута и опыт +100% на 10 минут!"
            elif "Эликсир здоровья" in item[2]:
                if battle:
                    max_hp = user[10] * 10
                    battle['user_hp'] = max_hp
                    effect_msg = "❤️ Здоровье полностью восстановлено в бою!"
                else:
                    cursor.execute("UPDATE users SET stamina = ? WHERE user_id = ?", (user[10], user_id))
                    effect_msg = "❤️ Здоровье полностью восстановлено!"

        
        if item[5] > 1:
            cursor.execute("UPDATE inventory SET quantity = quantity - 1 WHERE id = ?", (item_id,))
        else:
            cursor.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
        conn.commit()

        bot.answer_callback_query(call.id, effect_msg)
        
        if battle:
            show_battle_interface(call.message, user_id)
        else:
            bot.send_message(call.message.chat.id, effect_msg)

    except Exception as e:
        print(f"Ошибка: {str(e)}")
        bot.answer_callback_query(call.id, "Ошибка использования предмета!")
        
@bot.message_handler(commands=["addexp"])
def add_exp_command(message: types.Message):
    
    if message.from_user.id != 5863827462: 
        bot.reply_to(message, "У вас нет прав для этой команды!")
        return
    
    try:
        # Формат команды: /addexp @username 100
        args = message.text.split()
        if len(args) != 3:
            bot.reply_to(message, "Использование: /addexp @username количество")
            return
            
        username = args[1].replace("@", "")
        amount = int(args[2])
        
        cursor.execute("UPDATE users SET exp = exp + ? WHERE username = ?", (amount, username))
        conn.commit()
        
        
        cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,))
        if user_id := cursor.fetchone():
            if new_level := check_level_up(user_id[0]):
                bot.reply_to(message, f"Добавлено {amount} опыта пользователю @{username}. Новый уровень: {new_level}")
            else:
                bot.reply_to(message, f"Добавлено {amount} опыта пользователю @{username}")
        else:
            bot.reply_to(message, "Пользователь не найден!")
            
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {str(e)}")        
        

def calculate_player_damage(user_id):
    user = get_user(user_id)
    base_damage = user[7]  
    cursor.execute("SELECT power FROM effects WHERE user_id = ? AND effect_type = 'strength' AND expires > ?", 
                 (user_id, time.time()))
    if strength_effect := cursor.fetchone():
        base_damage *= strength_effect[0]
    return int(base_damage + random.randint(1, 5))        

def handle_death(user_id):
    cursor.execute("INSERT OR REPLACE INTO deaths VALUES (?, ?)", (user_id, int(time.time())))
    conn.commit()
    
    
    cursor.execute("DELETE FROM effects WHERE user_id = ?", (user_id,))
    conn.commit()
    
    
    cursor.execute("UPDATE users SET gold = gold * 0.7 WHERE user_id = ?", (user_id,))
    conn.commit()

def format_battle_message(user_id, battle):
    user = get_user(user_id)
    enemy = battle['enemy']
    hp_bar = progress_bar(battle['user_hp'], user[10]*10)
    enemy_hp_bar = progress_bar(battle['enemy_hp'], enemy['hp'])
    
    return f"""
⚔️ *Бой с {enemy['name']}*
{hp_bar} Ваше HP: {battle['user_hp']}/{user[10]*10}
{enemy_hp_bar} HP врага: {battle['enemy_hp']}/{enemy['hp']}
"""

def generate_enemy(level):
    tier = min(level // 5 + 1, 4)
    templates = {
        1: ["Гоблин", "Волк"],
        2: ["Орк", "Рыцарь"],
        3: ["Демон", "Дракон"],
        4: ["Босс"]
    }
    
    enemy_type = random.choice(templates[tier])
    multiplier = 1 + (tier-1)*0.5
    
    return {
        'name': f"{enemy_type} Ур. {level}",
        'hp': 50 * level * multiplier,
        'attack': 10 * level * multiplier
    }

def get_active_effects(user_id):
    """Возвращает активные эффекты пользователя"""
    effects = {}
    try:
        cursor.execute("""
            SELECT effect_type, power 
            FROM effects 
            WHERE user_id = ? AND expires > ?
        """, (user_id, int(time.time())))
        for row in cursor.fetchall():
            effects[row[0]] = row[1]
    except sqlite3.Error as e:
        print(f"Error getting effects: {str(e)}")
    return effects




def get_user_stats(user_id):
    """Возвращает полную статистику пользователя"""
    stats = {}
    try:
        
        user = get_user(user_id)
        if not user:
            return None
            
        
        cursor.execute("""
            SELECT 
                COUNT(*) AS total_battles,
                SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) AS wins,
                SUM(CASE WHEN result = 'lose' THEN 1 ELSE 0 END) AS losses
            FROM battles 
            WHERE user_id = ?
        """, (user_id,))
        battle_stats = cursor.fetchone() or (0, 0, 0)

        
        cursor.execute("SELECT achievement_id FROM user_achievements WHERE user_id = ?", (user_id,))
        achievements = [row[0] for row in cursor.fetchall()]

        
        stats = {
            'user_id': user_id,
            'level': user[13],
            'exp': user[14],
            'gold': user[16],
            'total_battles': battle_stats[0],
            'wins': battle_stats[1],
            'losses': battle_stats[2],
            'achievements': achievements,
            'active_effects': get_active_effects(user_id)
        }
        
    except sqlite3.Error as e:
        print(f"Error getting user stats: {str(e)}")
    
    return stats



ACHIEVEMENTS = {
    'first_blood': {
        'title': "Первая кровь",
        'condition': lambda stats: stats['kills'] >= 1
    },
    'veteran': {
        'title': "Ветеран",
        'condition': lambda stats: stats['level'] >= 10
    }
}

def check_achievements(user_id):
    stats = get_user_stats(user_id)
    unlocked = []
    
    for ach_id, ach in ACHIEVEMENTS.items():
        if ach['condition'](stats) and not ach_id in stats['achievements']:
            unlocked.append(ach['title'])
    
    return unlocked

if __name__ == "__main__":
    print("Бот запущен...")
    bot.polling(none_stop=True)
