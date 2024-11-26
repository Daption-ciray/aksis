import logging
import aiohttp
import pandas as pd
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes
from decouple import config
from aiohttp.client_exceptions import ContentTypeError

# Bot'un API Token'ını .env dosyasından alın
API_TOKEN = config("API_TOKEN")

# Logging ayarları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
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
        "__RequestVerificationToken": token
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
                return json_response.get('IsSuccess') == True
            except ContentTypeError:
                return False
        return False

async def post_to_obs_results(session, url, year, semester):
    payload = {
        "group": "DersAdi-asc",
        "yil": year,
        "donem": semester
    }
    async with session.post(url, data=payload) as response:
        if response.status == 200:
            try:
                return await response.json()
            except ValueError:
                return None
        return None

def extract_relevant_data(data):
    relevant_data = []
    if 'Data' in data:
        for entry in data['Data']:
            if 'Items' in entry:
                for item in entry['Items']:
                    relevant_data.append({
                        'Yıl': item['Yil'],
                        'Dönem': item['EnumDonem'],
                        'Ders Adı': item['DersAdi'],
                        'Sınav Adı': item['SinavAdi'],
                        'Sınav Tarihi': item['SinavTarihiString'],
                        'Notu': item['Notu']
                    })
    return relevant_data

async def format_results_as_text(data):
    """
    JSON yanıtını kullanıcı dostu bir metne dönüştürür.
    """
    relevant_data = extract_relevant_data(data)
    if not relevant_data:
        return "Sonuç Mevcut Değil."

    # DataFrame oluştur ve sütunları hizala
    df = pd.DataFrame(relevant_data)
    formatted_text = df.to_markdown(index=False, tablefmt="grid")
    
    return f"Sonuçlar:\n\n```\n{formatted_text}\n```"

# Telegram bot işlevleri
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Merhaba! Ben bir Telegram botuyum. Size nasıl yardımcı olabilirim? /login komutunu kullanarak giriş yapabilirsiniz.')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Yardım komutları: /start, /help, /login')

# Giriş işlemleri
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('Lütfen TC kimlik numaranızı girin:')
    return 1

async def get_tc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['username'] = update.message.text
    await update.message.reply_text('🔑 Lütfen şifrenizi girin:')
    return 2

async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['password'] = update.message.text
    await update.message.reply_text('📅 Lütfen yıl bilgisini girin:')
    return 3

async def get_year(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['year'] = update.message.text
    await update.message.reply_text('📅 Lütfen dönem bilgisini girin: Güz veya Bahar')
    return 4

async def get_semester(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    username = context.user_data['username']
    password = context.user_data['password']
    year = context.user_data['year']
    semester = update.message.text.lower()
    if semester == "güz":
        semester = "1"
    elif semester == "bahar":
        semester = "2"
    else:
        await update.message.reply_text("❌ Geçersiz dönem bilgisi, lütfen 'Güz' veya 'Bahar' olarak girin.")
        return 4

    aksis_login_url = "https://aksis.istanbul.edu.tr/Account/LogOn"
    aksis_api_url = "https://aksis.istanbul.edu.tr/Home/Check667ForeignStudent"
    obs_url = "https://obs.istanbul.edu.tr"
    obs_post_url = "https://obs.istanbul.edu.tr/OgrenimBilgileri/SinavSonuclariVeNotlar/GetOgrenciSinavSonuc"

    async with aiohttp.ClientSession() as session:
        token = await get_verification_token(session, aksis_login_url)

        if token and await login_to_aksis(session, username, password, aksis_login_url, token):
            if await check_aksis_api(session, aksis_api_url):
                async with session.get(obs_url) as response_first:
                    if response_first.status == 200:
                        cookies = response_first.cookies
                        result = await post_to_obs_results(session, obs_post_url, year, semester)
                        if result:
                            # JSON verisini tablo olarak metne çevir ve gönder
                            formatted_result = await format_results_as_text(result)
                            await update.message.reply_text(
                                formatted_result, parse_mode="Markdown"
                            )
                        else:
                            await update.message.reply_text("❌ POST isteğinde hata oluştu veya veri formatı geçersiz.")
                    else:
                        await update.message.reply_text(f"❌ İlk obs sayfasına erişim sağlanamadı: {response_first.status}")
            else:
                await update.message.reply_text("❌ Kimlik bilgileri yanlış. Lütfen tekrar deneyin.")
        else:
            await update.message.reply_text("⚠️ Aksis giriş başarısız.")
    return ConversationHandler.END

# Ana fonksiyon
def main() -> None:
    application = Application.builder().token(API_TOKEN).build()

    login_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('login', login)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_tc)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_year)],
            4: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_semester)],
        },
        fallbacks=[]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(login_conv_handler)

    application.run_polling()

if __name__ == '__main__':
    main()