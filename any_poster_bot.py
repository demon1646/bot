import os
import logging
from typing import Dict, List, Union, Optional
from pathlib import Path
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import instagrapi
from instagrapi.types import Media
import vk_api
from vk_api.upload import VkUpload


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class SocialMediaPoster:
    def __init__(self):
        self.vk_session = vk_api.VkApi(token=os.getenv('VK_TOKEN'))
        self.vk = self.vk_session.get_api()
        self.vk_upload = VkUpload(self.vk_session)
        self.instagram_client = instagrapi.Client()
        self.instagram_client.login(os.getenv('INSTAGRAM_USERNAME'), os.getenv('INSTAGRAM_PASSWORD'))

    def post_to_vk(self, text: str, media_paths: List[Union[str, Path]] = None) -> bool:
        try:
            attachments = []
            if media_paths:
                for path in media_paths:
                    path_str = str(path)
                    if path_str.lower().endswith(('.jpg', '.jpeg', '.png')):
                        photo = self.vk_upload.photo(path_str)
                        attachments.append(f"photo{photo[0]['owner_id']}_{photo[0]['id']}")
                    elif path_str.lower().endswith(('.mp4', '.mov')):
                        video = self.vk_upload.video(path_str)
                        attachments.append(f"video{video['owner_id']}_{video['video_id']}")

            self.vk.wall.post(
                owner_id=os.getenv('VK_GROUP_ID'),
                message=text,
                attachments=','.join(attachments) if attachments else None
            )
            return True
        except Exception as e:
            logger.error(f"Error posting to VK: {e}")
            return False

    def post_to_instagram(self, text: str, media_path: Optional[Union[str, Path]] = None) -> bool:
        media: Optional[Media] = None
        try:
            if media_path:
                path_obj = Path(media_path)
                path_str = str(path_obj)
                if path_obj.suffix.lower() in ('.jpg', '.jpeg', '.png'):
                    media = self.instagram_client.photo_upload(path_obj, caption=text)
                elif path_obj.suffix.lower() in ('.mp4', '.mov'):
                    media = self.instagram_client.video_upload(path_obj, caption=text)
            else:
                dummy_photo = Path("dummy.jpg")
                if not dummy_photo.exists():
                    from PIL import Image
                    img = Image.new('RGB', (1, 1), color='white')
                    img.save(dummy_photo)
                media = self.instagram_client.photo_upload(dummy_photo, caption=text)
            return media is not None
        except Exception as e:
            logger.error(f"Error posting to Instagram: {e}")
            return False


def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    update.message.reply_text(
        f"Привет, {user.first_name}!\n\n"
        "Я Any Poster - бот для кросс-постинга в социальные сети.\n\n"
        "Просто отправь мне текст, фото или видео, и я опубликую это в подключенных соцсетях.\n\n"
        "Доступные команды:\n"
        "/post - опубликовать контент\n"
        "/settings - настройки публикации\n"
        "/status - статус подключенных соцсетей"
    )


def post_content(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    poster = context.bot_data.get('poster')
    if not poster:
        update.message.reply_text("Ошибка: сервис публикации не инициализирован")
        return
    media_paths = []
    if update.message.photo:
        file = context.bot.get_file(update.message.photo[-1].file_id)
        filename = f"temp/{user_id}_{file.file_id}.jpg"
        file.download(filename)
        media_paths.append(filename)
    elif update.message.video:
        file = context.bot.get_file(update.message.video.file_id)
        filename = f"temp/{user_id}_{file.file_id}.mp4"
        file.download(filename)
        media_paths.append(filename)
    text = update.message.caption or update.message.text
    success_vk = poster.post_to_vk(text, media_paths)
    success_insta = poster.post_to_instagram(text, media_paths[0] if media_paths else None)
    report = "Результаты публикации:\n"
    report += f"VK: {'✅' if success_vk else '❌'}\n"
    report += f"Instagram: {'✅' if success_insta else '❌'}\n"
    update.message.reply_text(report)
    for path in media_paths:
        try:
            os.remove(path)
        except:
            pass


def settings(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "Настройки публикации:\n\n"
        "1. Подключенные соцсети\n"
        "2. Расписание публикаций\n"
        "3. Форматирование текста\n"
        "4. Водяные знаки\n\n"
        "Выберите пункт для настройки:"
    )


def status(update: Update, context: CallbackContext) -> None:
    poster = context.bot_data.get('poster')
    if not poster:
        update.message.reply_text("Ошибка: сервис публикации не инициализирован")
        return
    update.message.reply_text(
        "Статус подключенных соцсетей:\n\n"
        "VK: подключено\n"
        "Instagram: подключено\n"
        "Twitter: не подключено\n"
        "Facebook: не подключено"
    )


def error_handler(update: Update, context: CallbackContext) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    if update and update.message:
        update.message.reply_text('Произошла ошибка. Пожалуйста, попробуйте позже.')


def main() -> None:
    if not os.path.exists('temp'):
        os.makedirs('temp')
    updater = Updater(os.getenv('TELEGRAM_TOKEN'))
    dispatcher = updater.dispatcher
    poster = SocialMediaPoster()
    dispatcher.bot_data['poster'] = poster
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("post", post_content))
    dispatcher.add_handler(CommandHandler("settings", settings))
    dispatcher.add_handler(CommandHandler("status", status))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, post_content))
    dispatcher.add_handler(MessageHandler(Filters.photo | Filters.video, post_content))
    dispatcher.add_error_handler(error_handler)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()