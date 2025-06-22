import re
import logging
import requests
from typing import Optional
from datetime import datetime

from foodfit_bot.config.config import API_URL, API_HEADERS
from foodfit_bot.utils.helpers import clean_text

logger = logging.getLogger(__name__)


class AIService:
    @staticmethod
    async def generate_dish_description(dish_name: str, attempts: int = 3) -> Optional[str]:

        prompt = (
            "Сгенерируй описания для меню ресторана. И напиши БЖУ добавляемого блюда"
            "Требования:\n"
            "1. Только факты о блюде\n"
            "2. Без вводных слов ('Это', 'Хорошо' и т.д.)\n"
            "3. Конкретные детали приготовления\n\n"
            "4. БЖУ данного блюда"
            f"Пример для 'Стейк': 'Мраморная говядина сухой выдержки, обжаренная на гриле. "
            "Подается с трюфельным соусом и запеченными овощами.'\n\n"
            f"Блюдо: {dish_name}\n"
            "Описание:"
            "БЖУ:"
        )

        data = {
            "model": "deepseek-ai/DeepSeek-R1-0528",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Ты шеф-повар, составляешь  описания блюд. "
                        "В формате отсутствуют: \n"
                        "- Вводные конструкции\n"
                        "- Общие фразы\n"
                        "- Теги <think>\n"
                        "Начинай сразу с описания."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        for attempt in range(attempts):
            try:
                response = requests.post(API_URL, headers=API_HEADERS, json=data)
                response.raise_for_status()
                result = response.json()
                description = result['choices'][0]['message']['content']

                # Очистка ответа
                description = re.sub(r'<[^>]+>|Хорошо,|Итак,|Давай|\.\.\.', '', description).strip()

                # Проверка качества
                if len(description.split()) >= 6 and '.' in description:  # Минимум 6 слов и точка
                    return description

                logger.warning(f"Слишком короткое описание, попытка {attempt + 1}")

            except Exception as e:
                logger.error(f"Ошибка генерации описания (попытка {attempt + 1}): {str(e)}")

        return None

    @staticmethod
    async def generate_daily_recommendation(user_preferences: str) -> Optional[str]:
        """
        Генерирует персональную рекомендацию блюда
        :param user_preferences: Предпочтения пользователя
        :return: Рекомендация или None
        """
        prompt = (
            f"Ты гастрономический помощник. Рекомендуй одно блюдо клиенту на основе его предпочтений.\n"
            f"Формат ответа:\n"
            f"1. Название блюда (строго одно)\n"
            f"2. Краткое обоснование (1 предложение)\n\n"
            f"Предпочтения клиента: {user_preferences}\n"
            f"Рекомендация:"
        )

        try:
            data = {
                "model": "deepseek-ai/DeepSeek-R1-0528",
                "messages": [
                    {
                        "role": "system",
                        "content": "Ты даешь персонализированные рекомендации блюд. Будь кратким и убедительным."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 150
            }

            response = requests.post(API_URL, headers=API_HEADERS, json=data, timeout=7)
            response.raise_for_status()

            result = response.json()
            recommendation = result['choices'][0]['message']['content']
            return clean_text(recommendation.split('\n')[0].strip())  # Возвращаем только название

        except Exception as e:
            logger.error(f"Ошибка генерации рекомендации: {str(e)}")
            return None

    @staticmethod
    async def analyze_feedback(feedback_text: str) -> dict:
        """
        Анализирует текстовый отзыв с помощью AI
        :param feedback_text: Текст отзыва
        :return: Анализ в виде словаря
        """
        prompt = (
            f"Проанализируй отзыв клиента и извлеки:\n"
            f"1. Основную эмоцию (позитив/нейтрал/негатив)\n"
            f"2. Ключевые темы (качество, сервис, доставка и т.д.)\n"
            f"3. Предложения по улучшению (если есть)\n\n"
            f"Отзыв: {feedback_text}\n\n"
            f"Ответ в формате JSON:"
        )

        try:
            data = {
                "model": "deepseek-ai/DeepSeek-R1-0528",
                "messages": [
                    {
                        "role": "system",
                        "content": "Ты анализируешь отзывы. Возвращай только валидный JSON без пояснений."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "response_format": {"type": "json_object"}
            }

            response = requests.post(API_URL, headers=API_HEADERS, json=data, timeout=10)
            response.raise_for_status()

            result = response.json()
            return result['choices'][0]['message']['content']

        except Exception as e:
            logger.error(f"Ошибка анализа отзыва: {str(e)}")
            return {
                "sentiment": "neutral",
                "topics": [],
                "suggestions": []
            }

    @staticmethod
    async def generate_daily_special(date: datetime = None) -> str:
        """
        Генерирует предложение дня
        :param date: Дата для сезонного предложения
        :return: Текст предложения
        """
        date_str = date.strftime("%d %B") if date else "сегодня"

        prompt = (
            f"Придумай 'Предложение дня' для ресторана.\n"
            f"Формат:\n"
            f"1. Название блюда\n"
            f"2. Краткое описание (1 предложение)\n"
            f"3. Особые условия (скидка/подарок)\n\n"
            f"Дата: {date_str}\n"
            f"Предложение:"
        )

        try:
            data = {
                "model": "deepseek-ai/DeepSeek-R1",
                "messages": [
                    {
                        "role": "system",
                        "content": "Ты создаешь привлекательные предложения для ресторана."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 200
            }

            response = requests.post(API_URL, headers=API_HEADERS, json=data, timeout=7)
            response.raise_for_status()

            result = response.json()
            return clean_text(result['choices'][0]['message']['content'])

        except Exception as e:
            logger.error(f"Ошибка генерации предложения: {str(e)}")
            return f"🍽 Специальное предложение {date_str}!\nПопробуйте наш шеф-сюрприз со скидкой 15%!"


# Функции для быстрого доступа (можно вызывать напрямую)
async def generate_ai_description(*args, **kwargs):
    return await AIService.generate_dish_description(*args, **kwargs)


async def get_ai_recommendation(*args, **kwargs):
    return await AIService.generate_daily_recommendation(*args, **kwargs)