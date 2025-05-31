import os
from aiogram import F, Router
from aiogram.types import Message
from typing import List, Dict, Optional
from fuzzywuzzy import process
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command, StateFilter
import asyncpg
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
import io
import asyncio
import logging
import platform

# Создаем роутер
router = Router()

if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

pool: Optional[asyncpg.Pool] = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Загрузка переменных окружения
load_dotenv()
# Инициализация бота
bot = Bot(token="8191831600:AAHFOw5vlc-e2dN6znY--i1kxC75KaPfEek")
dp = Dispatcher()
dp.include_router(router)  # Добавляем роутер в диспетчер


class RecipeForm(StatesGroup):
    name = State()
    description = State()
    steps = State()
    difficulty = State()
    ingredients = State()


async def init_db():
    global pool
    max_retries = 5
    retry_delay = 3

    for attempt in range(max_retries):
        try:
            pool = await asyncpg.create_pool(
                host=os.getenv('DB_HOST', 'localhost'),
                port=int(os.getenv('DB_PORT', 5432)),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD'),
                database=os.getenv('DB_NAME', 'bachelor_helper'),
                min_size=1,
                max_size=10
            )
            logger.info(f"✅ Пул БД создан (попытка {attempt + 1})")
            return True
        except Exception as e:
            logger.error(f"⚠️ Попытка {attempt + 1} не удалась: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)

    logger.error("❌ Все попытки подключения к БД провалились")
    return False


# Классы состояний для FSM
class RecipeStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_steps = State()
    waiting_for_ingredients = State()
    waiting_for_recipe_confirmation = State()
    waiting_for_recipe_feedback = State()
    waiting_for_new_recipe = State()
    waiting_for_new_recipe_ingredients = State()
    waiting_for_new_recipe_steps = State()


async def check_db_connection():
    global pool
    if pool is None:
        return False
    try:
        async with pool.acquire() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception:
        return False


# Инициализация базы данных
async def create_tables():
    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            async with pool.acquire() as conn:
                # Создаём таблицы
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS ingredients (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) UNIQUE NOT NULL,
                        calories INT,
                        proteins DECIMAL(5,2),
                        fats DECIMAL(5,2),
                        carbohydrates DECIMAL(5,2)
                    )
                ''')

                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS recipes (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) UNIQUE NOT NULL,
                        description TEXT,
                        steps TEXT[],
                        difficulty INT,
                        rating DECIMAL(3,2) DEFAULT 0,
                        votes INT DEFAULT 0
                    )
                ''')

                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS recipe_ingredients (
                        recipe_id INT REFERENCES recipes(id) ON DELETE CASCADE,
                        ingredient_id INT REFERENCES ingredients(id) ON DELETE CASCADE,
                        amount VARCHAR(50),
                        PRIMARY KEY (recipe_id, ingredient_id)
                    )
                ''')

                # Добавляем базовые ингредиенты
                basic_ingredients = [
                    ('яйца', 155, 13, 11, 1),
                    ('хлеб', 265, 9, 3, 49),
                    ('сыр', 402, 25, 33, 1),
                    ('колбаса', 300, 12, 28, 2),
                    ('масло', 717, 0.5, 81, 0.8),
                    ('молоко', 60, 3.2, 3.6, 4.8),
                    ('картофель', 77, 2, 0.1, 17),
                    ('лук', 40, 1.1, 0.1, 9),
                    ('помидор', 18, 0.9, 0.2, 3.9),
                    ('огурец', 15, 0.7, 0.1, 3.6),
                    ('майонез', 680, 1, 75, 2.6),
                    ('кетчуп', 110, 2, 0.2, 25),
                    ('соль', 0, 0, 0, 0),
                    ('перец', 0, 0, 0, 0),
                    ('вода', 0, 0, 0, 0)
                ]

                for ing in basic_ingredients:
                    await conn.execute('''
                        INSERT INTO ingredients (name, calories, proteins, fats, carbohydrates)
                        VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT (name) DO NOTHING
                    ''', *ing)

                # Добавляем базовые рецепты, если их нет
                basic_recipes = [
                    ('Яичница', 'Простая яичница из яиц',
                     ['1. Разогрей сковороду', '2. Разбей яйца на сковороду', '3. Жарь 3-5 минут до готовности'],
                     1, ['яйца', 'масло']),
                    ('Бутерброд с колбасой', 'Простой бутерброд с колбасой',
                     ['1. Отрежь кусок хлеба', '2. Положи на хлеб колбасу',
                      '3. При желании добавь кетчуп или майонез'],
                     1, ['хлеб', 'колбаса']),
                    ('Гренки', 'Жареный хлеб',
                     ['1. Нарежь хлеб кусочками', '2. Разогрей сковороду с маслом',
                      '3. Обжарь хлеб с двух сторон до золотистой корочки'],
                     1, ['хлеб', 'масло']),
                    ('Сэндвич с яйцом', 'Сэндвич с вареным яйцом',
                     ['1. Свари яйца вкрутую (5 минут)', '2. Очисти яйца и нарежь', '3. Намажь хлеб майонезом',
                      '4. Выложи яйца на хлеб'],
                     2, ['яйца', 'хлеб', 'майонез']),
                    ('Картофель жареный', 'Жареный картофель',
                     ['1. Очисти картофель и нарежь соломкой', '2. Разогрей сковороду с маслом',
                      '3. Обжарь картофель до готовности', '4. Посоли по вкусу'],
                     2, ['картофель', 'масло', 'соль'])
                ]

                for recipe in basic_recipes:
                    # Проверяем существует ли рецепт
                    existing_id = await conn.fetchval(
                        'SELECT id FROM recipes WHERE name = $1', recipe[0]
                    )

                    if existing_id is None:
                        # Добавляем новый рецепт
                        recipe_id = await conn.fetchval('''
                            INSERT INTO recipes (name, description, steps, difficulty)
                            VALUES ($1, $2, $3, $4)
                            RETURNING id
                        ''', recipe[0], recipe[1], recipe[2], recipe[3])
                    else:
                        recipe_id = existing_id
                        # Обновляем существующий рецепт
                        await conn.execute('''
                            UPDATE recipes 
                            SET description = $2, steps = $3, difficulty = $4
                            WHERE id = $1
                        ''', recipe_id, recipe[1], recipe[2], recipe[3])

                    # Добавляем ингредиенты для рецепта
                    for ing_name in recipe[4]:
                        ing_id = await conn.fetchval(
                            'SELECT id FROM ingredients WHERE name = $1', ing_name
                        )
                        if ing_id:
                            await conn.execute('''
                                INSERT INTO recipe_ingredients (recipe_id, ingredient_id, amount)
                                VALUES ($1, $2, 'по вкусу')
                                ON CONFLICT (recipe_id, ingredient_id) DO NOTHING
                            ''', recipe_id, ing_id)

                logger.info("✅ Таблицы успешно созданы")
                return conn

        except Exception as e:
            logger.error(f"⚠️ Попытка {attempt + 1} не удалась: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
            else:
                logger.error("❌ Не удалось создать таблицы")
                raise RuntimeError("Не удалось создать таблицы") from e


# Функция для поиска похожих ингредиентов с учетом опечаток
async def find_similar_ingredients(user_input: str):
    if pool is None:
        print("⚠️ Пул соединений не инициализирован!")
        return []

    try:
        async with pool.acquire() as conn:
            # Получаем все ингредиенты из базы
            ingredients = await conn.fetch('SELECT name FROM ingredients')
            ingredient_names = [ing['name'] for ing in ingredients]

            # Разделяем ввод пользователя
            input_ingredients = [x.strip().lower() for x in user_input.split(',')]

            # Поиск совпадений
            matched = []
            for user_ing in input_ingredients:
                best_match = process.extractOne(user_ing, ingredient_names)
                if best_match and best_match[1] > 70:  # Порог схожести 70%
                    matched.append(best_match[0])

            return matched

    except Exception as e:
        print(f"Ошибка при поиске ингредиентов: {e}")
        return []  # Возвращаем пустой список при ошибке


# Функция для расчета пищевой ценности
async def calculate_nutrition(recipe_id: int) -> Dict[str, float]:
    conn = await create_tables()
    try:
        nutrition = await conn.fetchrow('''
            SELECT SUM(i.calories) as calories,
                   SUM(i.proteins) as proteins,
                   SUM(i.fats) as fats,
                   SUM(i.carbohydrates) as carbohydrates
            FROM recipe_ingredients ri
            JOIN ingredients i ON ri.ingredient_id = i.id
            WHERE ri.recipe_id = $1
        ''', recipe_id)

        return {
            'calories': nutrition['calories'] or 0,
            'proteins': nutrition['proteins'] or 0,
            'fats': nutrition['fats'] or 0,
            'carbohydrates': nutrition['carbohydrates'] or 0
        }
    finally:
        await conn.close()


# Функция для генерации изображения с рецептом
async def generate_recipe_image(recipe: Dict) -> io.BytesIO:
    # Создаем изображение
    img = Image.new('RGB', (800, 1200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Загружаем шрифт (можно использовать стандартный, если нет файла шрифта)
    try:
        font = ImageFont.truetype("arial.ttf", 24)
        font_title = ImageFont.truetype("arial.ttf", 32)
    except:
        font = ImageFont.load_default()
        font_title = ImageFont.load_default()

    # Рисуем заголовок
    draw.text((50, 50), recipe['name'], fill=(0, 0, 0), font=font_title)

    # Рисуем описание
    draw.text((50, 100), recipe['description'], fill=(0, 0, 0), font=font)

    # Рисуем ингредиенты
    draw.text((50, 150), "Ингредиенты:", fill=(0, 0, 0), font=font)
    for i, ing in enumerate(recipe['ingredients']):
        draw.text((70, 180 + i * 30), f"• {ing}", fill=(0, 0, 0), font=font)

    # Рисуем пищевую ценность
    nut = recipe['nutrition']
    nut_text = (f"Пищевая ценность:\n"
                f"Калории: {nut['calories']:.0f} ккал\n"
                f"Белки: {nut['proteins']:.1f} г\n"
                f"Жиры: {nut['fats']:.1f} г\n"
                f"Углеводы: {nut['carbohydrates']:.1f} г")
    draw.text((50, 300), nut_text, fill=(0, 0, 0), font=font)

    # Рисуем шаги приготовления
    draw.text((50, 400), "Приготовление:", fill=(0, 0, 0), font=font)
    for i, step in enumerate(recipe['steps']):
        draw.text((70, 430 + i * 50), f"{i + 1}. {step}", fill=(0, 0, 0), font=font)

    # Сохраняем изображение в буфер
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)

    return buf


# Обработчик команды /start
@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я Холостяцкий Помощник - бот, который поможет приготовить вкусное блюдо из того, что есть в холодильнике.\n\n"
        "Доступные команды:\n"
        "/help - показать справку\n"
        "/random - случайный рецепт\n"
        "/add_recipe - добавить свой рецепт"
    )


# Обработчик команды /help
@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "Как пользоваться ботом:\n\n"
        "1. Я подберу рецепты, которые можно приготовить из этих продуктов\n"
        "2. Выбери понравившийся рецепт и следуй инструкции\n\n"
        "Дополнительные команды:\n"
        "/random - получить случайный рецепт\n"
        "/add_recipe - добавить свой рецепт в базу\n"
        "/help - показать эту справку"
    )


# Обработчик команды /random
@router.message(Command("random"))
async def cmd_random(message: Message):
    try:
        async with pool.acquire() as conn:  # Автоматическое управление соединением
            # Получаем случайный рецепт
            recipe = await conn.fetchrow(
                "SELECT * FROM recipes ORDER BY RANDOM() LIMIT 1"
            )

            if not recipe:
                await message.answer("Рецептов пока нет в базе!")
                return

            # Получаем ингредиенты для этого рецепта
            ingredients = await conn.fetch(
                """
                SELECT i.name, ri.amount 
                FROM recipe_ingredients ri
                JOIN ingredients i ON ri.ingredient_id = i.id
                WHERE ri.recipe_id = $1
                """,
                recipe['id']
            )

            # Формируем сообщение
            response = (
                f"🍴 <b>{recipe['name']}</b>\n\n"
                f"📝 <b>Описание:</b> {recipe['description']}\n\n"
                f"📌 <b>Ингредиенты:</b>\n"
            )

            for ing in ingredients:
                response += f"- {ing['name']}: {ing['amount']}\n"

            response += f"\n👨‍🍳 <b>Шаги приготовления:</b>\n"
            for i, step in enumerate(recipe['steps'], 1):
                response += f"{i}. {step}\n"

            await message.answer(response, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Ошибка при получении случайного рецепта: {e}")
        await message.answer("Произошла ошибка при получении рецепта. Попробуйте позже.")


# Функция для отправки рецепта
async def send_recipe(message: types.Message, recipe: Dict, show_buttons: bool = True):
    # Формируем текст рецепта
    recipe_text = (
        f"<b>{recipe['name']}</b>\n\n"
        f"<i>{recipe['description']}</i>\n\n"
        f"<b>Ингредиенты:</b>\n"
        f"{', '.join(recipe['ingredients'])}\n\n"
        f"<b>Пищевая ценность (приблизительно):</b>\n"
        f"🥚 Белки: {recipe['nutrition']['proteins']:.1f} г\n"
        f"🧈 Жиры: {recipe['nutrition']['fats']:.1f} г\n"
        f"🍞 Углеводы: {recipe['nutrition']['carbohydrates']:.1f} г\n"
        f"Калории: {recipe['nutrition']['calories']:.0f} ккал\n\n"
        f"<b>Приготовление:</b>\n"
    )
    # Добавляем шаги приготовления
    for i, step in enumerate(recipe['steps']):
        recipe_text += f"{i + 1}. {step}\n"

    # Добавляем рейтинг, если он есть
    if recipe['rating'] and recipe['rating'] > 0:
        recipe_text += f"\n⭐ Рейтинг: {recipe['rating']:.1f}/5"

    # Создаем клавиатуру с кнопками
    if show_buttons:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(text="👍", callback_data=f"rate_good_{recipe['id']}"),
            types.InlineKeyboardButton(text="👎", callback_data=f"rate_bad_{recipe['id']}"),
            types.InlineKeyboardButton(text="🖼️ Получить картинкой", callback_data=f"image_{recipe['id']}")
        )
    else:
        keyboard = None

    # Отправляем сообщение
    await message.answer(recipe_text, parse_mode='HTML', reply_markup=keyboard)


# Обработчик команды /add_recipe
@router.message(Command("add_recipe"))
async def cmd_add_recipe(message: Message, state: FSMContext):
    await message.answer("Введите название рецепта:")
    await state.set_state(RecipeForm.name)


# Обработчик ввода названия нового рецепта
@router.message(RecipeForm.name)
async def process_recipe_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите описание рецепта:")
    await state.set_state(RecipeForm.description)


# Обработчик ввода описания рецепта
@router.message(RecipeForm.description)
async def process_recipe_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Введите шаги приготовления (каждый шаг с новой строки):")
    await state.set_state(RecipeForm.steps)


@router.message(RecipeForm.steps)
async def process_recipe_steps(message: Message, state: FSMContext):
    steps = message.text.split('\n')
    await state.update_data(steps=steps)
    await message.answer("Введите сложность (от 1 до 5):")
    await state.set_state(RecipeForm.difficulty)


# Обработчик ввода ингредиентов для нового рецепта
@router.message(RecipeForm.difficulty)
async def process_recipe_difficulty(message: Message, state: FSMContext):
    try:
        difficulty = int(message.text)
        if difficulty < 1 or difficulty > 5:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите число от 1 до 5:")
        return

    await state.update_data(difficulty=difficulty)
    await message.answer("Введите ингредиенты (каждый ингредиент с новой строки в формате: Название:Количество):")
    await state.set_state(RecipeForm.ingredients)


@router.message(RecipeForm.ingredients)
async def process_recipe_ingredients(message: Message, state: FSMContext):
    ingredients = []
    for line in message.text.split('\n'):
        if ':' in line:
            name, amount = line.split(':', 1)
            ingredients.append((name.strip(), amount.strip()))
        else:
            ingredients.append((line.strip(), "по вкусу"))

    async with pool.acquire() as conn:
        # Получаем данные из состояния
        data = await state.get_data()

        # Добавляем рецепт
        recipe_id = await conn.fetchval(
            """
            INSERT INTO recipes (name, description, steps, difficulty)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """,
            data['name'], data['description'], data['steps'], data['difficulty']
        )

        # Добавляем ингредиенты
        for name, amount in ingredients:
            # Получаем ID ингредиента (или создаем новый)
            ingredient_id = await conn.fetchval(
                """
                INSERT INTO ingredients (name)
                VALUES ($1)
                ON CONFLICT (name) DO UPDATE SET name=EXCLUDED.name
                RETURNING id
                """,
                name
            )

            # Связываем рецепт и ингредиент
            await conn.execute(
                """
                INSERT INTO recipe_ingredients (recipe_id, ingredient_id, amount)
                VALUES ($1, $2, $3)
                ON CONFLICT (recipe_id, ingredient_id) DO UPDATE SET amount=EXCLUDED.amount
                """,
                recipe_id, ingredient_id, amount
            )

        await message.answer(f"Рецепт '{data['name']}' успешно добавлен!")
        await state.clear()


# Обработчик подтверждения рецепта
@dp.message(
    F.text.in_(["Да, все верно", "Нет, изменить"]),
    StateFilter(RecipeStates.waiting_for_recipe_feedback)
)
async def process_recipe_confirmation(message: types.Message, state: FSMContext):
    if message.text == "Нет, изменить":
        await RecipeStates.waiting_for_new_recipe.set()
        await message.answer(
        "Хорошо, начнем заново. Введи название рецепта:",
        reply_markup=types.ReplyKeyboardRemove()
        )
        return

    # Сохраняем рецепт в базу данных
    async with state.proxy() as data:
        conn = await create_tables()
        try:
            # Добавляем рецепт
            recipe_id = await conn.fetchval('''
                INSERT INTO recipes (name, description, steps, difficulty)
                VALUES ($1, $2, $3, $4)
                RETURNING id
            ''', data['name'], data['description'], data['steps'], len(data['steps']) // 3 + 1)

            if not recipe_id:
                await message.answer("Ошибка при сохранении рецепта.", reply_markup=types.ReplyKeyboardRemove())
                await state.finish()
                return

            # Добавляем ингредиенты
            for ing_name in data['ingredients']:
                ing_id = await conn.fetchval('SELECT id FROM ingredients WHERE name = $1', ing_name)
                if ing_id:
                    await conn.execute('''
                        INSERT INTO recipe_ingredients (recipe_id, ingredient_id, amount)
                        VALUES ($1, $2, 'по вкусу')
                    ''', recipe_id, ing_id)

            await message.answer(
                "Рецепт успешно сохранен! Спасибо за вклад в нашу базу.",
                reply_markup=types.ReplyKeyboardRemove()
            )

            # Получаем полный рецепт для отправки
            recipe = await conn.fetchrow('SELECT * FROM recipes WHERE id = $1', recipe_id)
            recipe_ings = await conn.fetch('''
                SELECT i.name FROM recipe_ingredients ri
                JOIN ingredients i ON ri.ingredient_id = i.id
                WHERE ri.recipe_id = $1
            ''', recipe_id)

            recipe_data = {
                'id': recipe['id'],
                'name': recipe['name'],
                'description': recipe['description'],
                'steps': recipe['steps'],
                'difficulty': recipe['difficulty'],
                'ingredients': [ing['name'] for ing in recipe_ings],
                'nutrition': await calculate_nutrition(recipe_id),
                'rating': 0
            }

            # Отправляем рецепт пользователю
            await send_recipe(message, recipe_data)

        finally:
            await conn.close()

    await state.finish()


# Обработчик текстовых сообщений (ввод ингредиентов)
@router.message(RecipeForm.ingredients)
async def process_ingredients(message: types.Message, state: FSMContext):
    try:
        ingredients = []
        for line in message.text.split('\n'):
            if ':' in line:
                name, amount = line.split(':', 1)
                ingredients.append((name.strip(), amount.strip()))
            else:
                ingredients.append((line.strip(), "по вкусу"))

        data = await state.get_data()

        async with pool.acquire() as conn:
            # Добавляем рецепт
            recipe_id = await conn.fetchval(
                """
                INSERT INTO recipes (name, description, steps, difficulty)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                data['name'], data['description'], data['steps'], data['difficulty']
            )

            # Добавляем ингредиенты
            for name, amount in ingredients:
                ingredient_id = await conn.fetchval(
                    """
                    INSERT INTO ingredients (name)
                    VALUES ($1)
                    ON CONFLICT (name) DO UPDATE SET name=EXCLUDED.name
                    RETURNING id
                    """,
                    name
                )

                await conn.execute(
                    """
                    INSERT INTO recipe_ingredients (recipe_id, ingredient_id, amount)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (recipe_id, ingredient_id) DO UPDATE SET amount=EXCLUDED.amount
                    """,
                    recipe_id, ingredient_id, amount
                )

        await message.answer(f"Рецепт '{data['name']}' успешно добавлен!")
        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при добавлении рецепта: {e}")
        await message.answer("Произошла ошибка при добавлении рецепта. Попробуйте ещё раз.")
        await state.clear()


# Обработчик callback-запросов (кнопки)
@dp.callback_query(lambda c: c.data.startswith('recipe_') or c.data.startswith('rate_') or c.data.startswith('image_'))
async def process_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    if callback_query.data.startswith('recipe_'):
        # Показываем другой рецепт
        recipe_id = int(callback_query.data.split('_')[1])
        conn = await create_tables()
        try:
            recipe = await conn.fetchrow('SELECT * FROM recipes WHERE id = $1', recipe_id)
            if recipe:
                recipe_ings = await conn.fetch('''
                    SELECT i.name FROM recipe_ingredients ri
                    JOIN ingredients i ON ri.ingredient_id = i.id
                    WHERE ri.recipe_id = $1
                ''', recipe_id)

                recipe_data = {
                    'id': recipe['id'],
                    'name': recipe['name'],
                    'description': recipe['description'],
                    'steps': recipe['steps'],
                    'difficulty': recipe['difficulty'],
                    'ingredients': [ing['name'] for ing in recipe_ings],
                    'nutrition': await calculate_nutrition(recipe_id),
                    'rating': recipe['rating']
                }

                await send_recipe(callback_query.message, recipe_data)
        finally:
            await conn.close()

    elif callback_query.data.startswith('rate_'):
        # Оцениваем рецепт
        action, recipe_id = callback_query.data.split('_')[1], int(callback_query.data.split('_')[2])
        conn = await create_tables()
        try:
            if action == 'good':
                await conn.execute('''
                    UPDATE recipes 
                    SET rating = (rating * votes + 5) / (votes + 1),
                        votes = votes + 1
                    WHERE id = $1
                ''', recipe_id)
                await callback_query.message.answer("Спасибо за оценку 👍")
            elif action == 'bad':
                await conn.execute('''
                    UPDATE recipes 
                    SET rating = (rating * votes + 1) / (votes + 1),
                        votes = votes + 1
                    WHERE id = $1
                ''', recipe_id)
                await callback_query.message.answer("Спасибо за оценку 👎")
        finally:
            await conn.close()

    elif callback_query.data.startswith('image_'):
        # Генерируем и отправляем изображение с рецептом
        recipe_id = int(callback_query.data.split('_')[1])
        conn = await create_tables()
        try:
            recipe = await conn.fetchrow('SELECT * FROM recipes WHERE id = $1', recipe_id)
            if recipe:
                recipe_ings = await conn.fetch('''
                    SELECT i.name FROM recipe_ingredients ri
                    JOIN ingredients i ON ri.ingredient_id = i.id
                    WHERE ri.recipe_id = $1
                ''', recipe_id)

                recipe_data = {
                    'id': recipe['id'],
                    'name': recipe['name'],
                    'description': recipe['description'],
                    'steps': recipe['steps'],
                    'difficulty': recipe['difficulty'],
                    'ingredients': [ing['name'] for ing in recipe_ings],
                    'nutrition': await calculate_nutrition(recipe_id),
                    'rating': recipe['rating']
                }

                image = await generate_recipe_image(recipe_data)
                await bot.send_photo(callback_query.message.chat.id, photo=image)
        finally:
            await conn.close()


# Запуск бота
async def on_startup():
    try:
        logger.info("Попытка инициализации БД...")
        db_initialized = await init_db()
        if not db_initialized:
            logger.error("❌ Не удалось инициализировать БД")
            raise RuntimeError("DB initialization failed")
        if not await create_tables():
            raise RuntimeError("Не удалось создать таблицы")

        commands = [
            types.BotCommand(command="start", description="Запустить бота"),
            types.BotCommand(command="help", description="Помощь"),
            types.BotCommand(command="random", description="Случайный рецепт"),
            types.BotCommand(command="add_recipe", description="Добавить рецепт")
        ]
    except Exception as e:
        print(f"Critical startup error: {e}")
        raise


async def main():
    await on_startup()
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger.info("🟢 Запуск бота")
    print("Бот успешно запущен!")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен")