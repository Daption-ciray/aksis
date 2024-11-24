import logging
import requests
import pandas as pd
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes

# Bot'un API Token'ını buraya yapıştırın
API_TOKEN = '7529083346:AAE4N9zB_Ks16Sxf9eUniqXTJ-Ov2-FBOWc'

# Logging ayarları
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Global değişkenler
year = None
semester = None

# Aksis İşlevleri
def get_verification_token(session, url):
    response = session.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        token = soup.find("input", {"name": "__RequestVerificationToken"})["value"]
        return token
    else:
        return None

def login_to_aksis(session, username, password, login_url, token):
    login_data = {
        "UserName": username,
        "Password": password,
        "__RequestVerificationToken": token
    }
    response = session.post(login_url, data=login_data)
    if response.status_code == 200 and "Oturum açma başarısız" not in response.text:
        return True
    else:
        return False

def check_aksis_api(session, api_url):
    response = session.post(api_url)
    if response.status_code == 200:
        try:
            json_response = response.json()
            return json_response.get('IsSuccess') == True
        except ValueError:
            return False
    else:
        return False

def post_to_obs_results(session, url):
    payload = {
        "group": "DersAdi-asc",
        "yil": year,
        "donem": semester
    }
    response = session.post(url, data=payload)
    if response.status_code == 200:
        try:
            return response.json()
        except ValueError:
            return None
    else:
        return None

def format_results_as_text(data):
    if not data or not isinstance(data, list):
        return "Geçersiz veya boş veri, sonuç görüntülenemiyor."
    
    df = pd.DataFrame(data)
    return df.to_string(index=False)

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
    await update.message.reply_text('Lütfen şifrenizi girin:')
    return 2

async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['password'] = update.message.text
    await update.message.reply_text('Lütfen yıl bilgisini girin:')
    return 3

async def get_year(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    global year
    year = update.message.text
    await update.message.reply_text('Lütfen dönem bilgisini girin:')
    return 4

async def get_semester(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    global semester
    semester = update.message.text
    
    username = context.user_data['username']
    password = context.user_data['password']
    
    aksis_login_url = "https://aksis.istanbul.edu.tr/Account/LogOn"
    aksis_api_url = "https://aksis.istanbul.edu.tr/Home/Check667ForeignStudent"
    obs_url = "https://obs.istanbul.edu.tr"
    obs_post_url = "https://obs.istanbul.edu.tr/OgrenimBilgileri/SinavSonuclariVeNotlar/GetOgrenciSinavSonuc"

    session = requests.Session()
    token = get_verification_token(session, aksis_login_url)

    if token and login_to_aksis(session, username, password, aksis_login_url, token):
        if check_aksis_api(session, aksis_api_url):
            response_first = session.get(obs_url)
            if response_first.status_code == 200:
                result = post_to_obs_results(session, obs_post_url)
                if result:
                    formatted_result = format_results_as_text(result)
                    await update.message.reply_text(f"POST isteği başarılı. Sonuçlar:\n{formatted_result}")
                else:
                    await update.message.reply_text("POST isteğinde hata oluştu veya veri formatı geçersiz.")
            else:
                await update.message.reply_text("İlk obs sayfasına erişim sağlanamadı.")
        else:
            await update.message.reply_text("Aksis API sayfasına erişim sağlanamadı.")
    else:
        await update.message.reply_text("Aksis giriş başarısız.")
    return ConversationHandler.END

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
