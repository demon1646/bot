from aiogram import Router


def setup_routers() -> Router:
    """Создает и настраивает главный роутер со всеми обработчиками"""
    from foodfit_bot.handlers.commands import router as commands_router
    from foodfit_bot.handlers.admin import router as admin_router
    from foodfit_bot.handlers.cart import router as cart_router
    from foodfit_bot.handlers.menu import router as menu_router
    from foodfit_bot.handlers.orders import router as orders_router
    from foodfit_bot.handlers.staff import router as staff_router

    main_router = Router(name="MainRouter")

    main_router.include_router(commands_router)
    main_router.include_router(admin_router)
    main_router.include_router(cart_router)
    main_router.include_router(menu_router)
    main_router.include_router(orders_router)
    main_router.include_router(staff_router)

    return main_router
