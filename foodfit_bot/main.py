import logging
from aiogram import Bot, Dispatcher
from config.config import BOT_TOKEN
from config.database import init_db
from handlers import commands, admin, cart, menu, orders, staff
from handlers import setup_routers

# Инициализация
bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# Регистрация обработчиков
dp.include_router(orders.router)
dp.include_router(staff.router)
dp.include_router(commands.router)
dp.include_router(admin.router)
dp.include_router(cart.router)
dp.include_router(menu.router)


async def main():
    dp = Dispatcher()
    dp.include_router(setup_routers())
    init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())