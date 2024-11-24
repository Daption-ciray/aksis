import logging
import aiohttp
import pandas as pd
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
from decouple import config


# Bot'un API Token'ını .env dosyasından alın
API_TOKEN = config("API_TOKEN")

# Logging ayarları
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Aksis İşlevleri
async def get_verification_token(session, url):
    async with session.get(url) as response:
        if response.status == 200:
            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")
            token = soup.find("input", {"name": "__RequestVerificationToken"})["value"]
            return token
        return None


async def login_to_aksis(session, username, password, login_url, token):
    login_data = {
        "UserName": username,
        "Password": password,
        "__RequestVerificationToken": token,
    }
    async with session.post(login_url, data=login_data) as response:
        if response.status == 200 and "Oturum açma başarısız" not in await response.text():
            return True
        return False


async def check_aksis_api(session, api_url):
    async with session.post(api_url) as response:
        if response.status == 200:
            try:
                json_response = await response.json()
                return json_response.get("IsSuccess") == True
            except ValueError:
                return False
        return False


async def post_to_obs_results(session, url, year, semester):
    payload = {"group": "DersAdi-asc", "yil": year, "donem": semester}
    async with session.post(url, data=payload) as response:
        if response.status == 200:
            try:
                return await response.json()
            except ValueError:
                return None
        return None


def extract_relevant_data(data):
    relevant_data = []
    if "Data" in data:
        for entry in data["Data"]:
            if "Items" in entry:
                for item in entry["Items"]:
                    relevant_data.append(
                        {
                            "Yıl": item["Yil"],
                            "Dönem": item["EnumDonem"],
                            "Ders Adı": item["DersAdi"],
                            "Sınav Adı": item["SinavAdi"],
                            "Sınav Tarihi": item["SinavTarihiString"],
                            "Notu": item["Notu"],
                        }
                    )
    return relevant_data


async def format_results_as_text(data):
    """
    JSON yanıtını kullanıcı dostu bir metne dönüştürür.
    """
    relevant_data = extract_relevant_data(data)
    if not relevant_data:
        return "Sonuç bulunamadı."

    # DataFrame oluştur
    df = pd.DataFrame(relevant_data)

    # DataFrame'i tablo formatında metne dönüştür
    return f"Sonuçlar:\n\n```{df.to_string(index=False, col_space=15)}```"


async def send_csv(update, context, data):
    """
    Veriyi CSV dosyası olarak kullanıcıya gönderir.
    """
    relevant_data = extract_relevant_data(data)
    if not relevant_data:
        await update.message.reply_text("Sonuç bulunamadı.")
        return

    df = pd.DataFrame(relevant_data)
    buffer = io.BytesIO()
    df.to_csv(buffer, index=False, encoding="utf-8")
    buffer.seek(0)

    await update.message.reply_document(
        document=buffer, filename="sinav_sonuclari.csv"
    )


# Telegram bot işlevleri
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Merhaba! Ben bir Telegram botuyum. Size nasıl yardımcı olabilirim? /login komutunu kullanarak giriş yapabilirsiniz."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Yardım komutları: /start, /help, /login"
    )


# Giriş işlemleri
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Lütfen TC kimlik numaranızı girin:")
    return 1


async def get_tc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["username"] = update.message.text
    await update.message.reply_text("Lütfen şifrenizi girin:")
    return 2


async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["password"] = update.message.text
    await update.message.reply_text("Lütfen yıl bilgisini girin:")
    return 3


async def get_year(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["year"] = update.message.text
    await update.message.reply_text("Lütfen dönem bilgisini girin:")
    return 4


async def get_semester(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["semester"] = update.message.text

    username = context.user_data["username"]
    password = context.user_data["password"]
    year = context.user_data["year"]
    semester = context.user_data["semester"]

    aksis_login_url = "https://aksis.istanbul.edu.tr/Account/LogOn"
    aksis_api_url = "https://aksis.istanbul.edu.tr/Home/Check667ForeignStudent"
    obs_post_url = "https://obs.istanbul.edu.tr/OgrenimBilgileri/SinavSonuclariVeNotlar/GetOgrenciSinavSonuc"

    async with aiohttp.ClientSession() as session:
        token = await get_verification_token(session, aksis_login_url)
        if not token:
            await update.message.reply_text("Token alınamadı, lütfen tekrar deneyin.")
            return ConversationHandler.END

        if not await login_to_aksis(session, username, password, aksis_login_url, token):
            await update.message.reply_text("Aksis giriş başarısız.")
            return ConversationHandler.END

        if not await check_aksis_api(session, aksis_api_url):
            await update.message.reply_text("Aksis API'ye erişim sağlanamadı.")
            return ConversationHandler.END

        result = await post_to_obs_results(session, obs_post_url, year, semester)
        if not result:
            await update.message.reply_text(
                "POST isteğinde hata oluştu veya veri alınamadı."
            )
            return ConversationHandler.END

        await format_results_as_text(result)
        await update.message.reply_text(formatted_text, parse_mode="Markdown")
    return ConversationHandler.END


def main() -> None:
    application = Application.builder().token(API_TOKEN).build()

    login_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("login", login)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tc)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_year)],
            4: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_semester)],
        },
        fallbacks=[],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(login_conv_handler)

    application.run_polling()


if __name__ == "__main__":
    main()
