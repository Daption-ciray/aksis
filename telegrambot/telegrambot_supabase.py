import logging
import aiohttp
import asyncio
import pandas as pd
from bs4 import BeautifulSoup
from typing import Optional, Dict, List, Any, Union
from supabase import create_client, Client
from decouple import config
from telegram import Bot, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

# States for conversation handler
TCNO, PASSWORD, YEAR, SEMESTER = range(4)

# Configuration
class Config:
    SUPABASE_URL = config("SUPABASE_URL")
    SUPABASE_KEY = config("SUPABASE_KEY")
    API_TOKEN = config("API_TOKEN")
    AKSIS_LOGIN_URL = "https://aksis.istanbul.edu.tr/Account/LogOn"
    AKSIS_API_URL = "https://aksis.istanbul.edu.tr/Home/Check667ForeignStudent"
    OBS_POST_URL = "https://obs.istanbul.edu.tr/OgrenimBilgileri/SinavSonuclariVeNotlar/GetOgrenciSinavSonuc"
    REQUEST_TIMEOUT = 30

# Initialize logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token: str):
        self.application = Application.builder().token(token).build()
        self.setup_handlers()

    def setup_handlers(self) -> None:
        login_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("login", self.start_login)],
            states={
                TCNO: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_tc)],
                PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_password)],
                YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_year)],
                SEMESTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_semester)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
        )

        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(login_conv_handler)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            "Merhaba! İstanbul Üniversitesi sınav sonuçlarını kontrol etmek için /login komutunu kullanabilirsiniz."
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        help_text = (
            "Kullanılabilir komutlar:\n"
            "/start - Botu başlat\n"
            "/help - Yardım menüsünü göster\n"
            "/login - Aksis hesabınıza giriş yapın\n"
            "/cancel - İşlemi iptal et"
        )
        await update.message.reply_text(help_text)

    async def start_login(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.message.reply_text(
            "TC kimlik numaranızı girin (İşlemi iptal etmek için /cancel):"
        )
        return TCNO

    async def get_tc(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        tc = update.message.text
        if not tc.isdigit() or len(tc) != 11:
            await update.message.reply_text("Geçersiz TC kimlik numarası. Lütfen tekrar deneyin:")
            return TCNO
        context.user_data["username"] = tc
        await update.message.reply_text("Şifrenizi girin:")
        return PASSWORD

    async def get_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        context.user_data["password"] = update.message.text
        await update.message.reply_text("Yıl bilgisini girin (örn: 2024):")
        return YEAR

    async def get_year(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        year = update.message.text
        if not year.isdigit() or len(year) != 4:
            await update.message.reply_text("Geçersiz yıl. Lütfen tekrar deneyin (örn: 2024):")
            return YEAR
        context.user_data["year"] = year
        await update.message.reply_text("Dönem bilgisini girin (1 veya 2):")
        return SEMESTER

    async def get_semester(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        semester = update.message.text
        if semester not in ["1", "2"]:
            await update.message.reply_text("Geçersiz dönem. Lütfen 1 veya 2 girin:")
            return SEMESTER
        
        context.user_data["semester"] = semester
        await self.process_login(update, context)
        return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.message.reply_text("İşlem iptal edildi.")
        return ConversationHandler.END

    async def process_login(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            async with aiohttp.ClientSession() as session:
                await update.message.reply_text("Giriş işlemi başlatılıyor...")
                
                # Get user credentials from context
                username = context.user_data.get("username")
                password = context.user_data.get("password")
                year = context.user_data.get("year")
                semester = context.user_data.get("semester")

                # Here you would implement the actual login logic to Aksis
                # For example:
                # login_data = {
                #     "UserName": username,
                #     "Password": password,
                # }
                # async with session.post(Config.AKSIS_LOGIN_URL, data=login_data) as response:
                #     # Handle login response
                
                await update.message.reply_text("İşlem tamamlandı!")
                
        except Exception as e:
            logger.error(f"Login process error: {str(e)}")
            await update.message.reply_text("Bir hata oluştu. Lütfen tekrar deneyin.")

class SupabaseManager:
    def __init__(self, url: str, key: str):
        self.client = create_client(url, key)
        self.bot: Optional[Bot] = None

    async def start_listening(self, bot: Bot) -> None:
        self.bot = bot
        try:
            channel = self.client.realtime.channel('exam_results_changes')
            channel.on('INSERT', lambda payload: asyncio.create_task(
                self.handle_new_result(payload))
            ).subscribe()
            
            while True:
                await asyncio.sleep(60)
                
        except Exception as e:
            logger.error(f"Supabase listening error: {str(e)}")

    async def handle_new_result(self, payload: Dict[str, Any]) -> None:
        if not self.bot:
            return

        try:
            new_record = payload.get("new", {})
            message = self.format_notification(new_record)
            await self.bot.send_message(
                chat_id=new_record.get("user_id"),
                text=message,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Error handling new result: {str(e)}")

    @staticmethod
    def format_notification(record: Dict[str, Any]) -> str:
        return (
            f"📢 <b>Yeni Not Açıklandı!</b>\n\n"
            f"📚 Ders: {record.get('course_name', 'Belirtilmemiş')}\n"
            f"📝 Sınav: {record.get('exam_name', 'Belirtilmemiş')}\n"
            f"📅 Tarih: {record.get('exam_date', 'Belirtilmemiş')}\n"
            f"📊 Not: {record.get('grade', 'Belirtilmemiş')}"
        )

async def run_bot() -> None:
    # Initialize bot
    bot = TelegramBot(Config.API_TOKEN)
    await bot.application.initialize()
    
    # Initialize Supabase manager
    supabase_manager = SupabaseManager(Config.SUPABASE_URL, Config.SUPABASE_KEY)
    
    try:
        # Start both the Supabase listener and the bot
        await asyncio.gather(
            supabase_manager.start_listening(bot.application.bot),
            bot.application.run_polling(allowed_updates=Update.ALL_TYPES)
        )
    finally:
        await bot.application.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        pass