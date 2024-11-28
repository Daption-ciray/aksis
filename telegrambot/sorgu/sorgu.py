import asyncio
import aiohttp
import csv
from bs4 import BeautifulSoup

async def get_verification_token(session, url):
    async with session.get(url) as response:
        if response.status == 200:
            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")
            token = soup.find("input", {"name": "__RequestVerificationToken"})["value"]
            return token
        else:
            print(f"Giriş sayfasına erişim başarısız: {response.status}")
            return None

async def login_to_aksis(session, username, password, login_url, token):
    login_data = {
        "UserName": username,
        "Password": password,
        "__RequestVerificationToken": token
    }
    async with session.post(login_url, data=login_data) as response:
        if response.status == 200 and "Oturum açma başarısız" not in await response.text():
            print("Aksis'e başarılı giriş")
            return True
        else:
            print("Aksis giriş başarısız")
            return False

async def check_aksis_api(session, api_url):
    async with session.post(api_url) as response:
        if response.status == 200:
            try:
                json_response = await response.json()
                print("Aksis API Yanıtı: ", json_response)
                return json_response.get('IsSuccess') == True
            except ValueError:
                print("Aksis API yanıtı JSON formatında değil")
                return False
        else:
            print(f"Aksis API isteğinde hata: {response.status}")
            return False

async def post_to_obs_results(session, url, year, semester):
    payload = {
        "group": "DersAdi-asc",
        "yil": year,
        "donem": semester
    }
    async with session.post(url, data=payload) as response:
        if response.status == 200:
            print("POST isteği başarılı.")
            try:
                data = await response.json()
                await save_to_csv(data)
            except ValueError:
                print("POST isteği yanıtı JSON formatında değil.")
        else:
            print(f"POST isteğinde hata: {response.status}")

async def save_to_csv(data):
    if 'Data' in data:
        with open('datasets/dersler.csv', mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['SinavID', 'Ders Adı'])
            for entry in data['Data']:
                if 'Items' in entry:
                    for item in entry['Items']:
                        writer.writerow([item['SinavID'], item['DersAdi']])
        print("Dersler CSV dosyasına kaydedildi.")
    else:
        print("Veri formatı geçersiz veya boş.")

async def main():
    username = input("TC: ")
    password = input("Şifre: ")
    year = input("Yıl: ")
    semester = input("Dönem: ").lower()
    if semester == "güz":
        semester = "1"
    elif semester == "bahar":
        semester = "2"
    else:
        print("❌ Geçersiz dönem bilgisi, lütfen 'Güz' veya 'Bahar' olarak girin.")
        return

    aksis_login_url = "https://aksis.istanbul.edu.tr/Account/LogOn"
    aksis_api_url = "https://aksis.istanbul.edu.tr/Home/Check667ForeignStudent"
    obs_url = "https://obs.istanbul.edu.tr"
    obs_post_url = "https://obs.istanbul.edu.tr/OgrenimBilgileri/SinavSonuclariVeNotlar/GetOgrenciSinavSonuc"

    async with aiohttp.ClientSession() as session:
        token = await get_verification_token(session, aksis_login_url)

        if token and await login_to_aksis(session, username, password, aksis_login_url, token):
            if await check_aksis_api(session, aksis_api_url):
                print("Aksis sayfasına erişim sağlandı")
                async with session.get(obs_url) as response_first:
                    if response_first.status == 200:
                        print("İlk obs sayfasına erişim sağlandı")
                        while True:
                            await post_to_obs_results(session, obs_post_url, year, semester)
                            await asyncio.sleep(300)  # 5 dakika bekle
                    else:
                        print(f"İlk obs sayfasına erişim sağlanamadı: {response_first.status}")
            else:
                print("Aksis API doğrulaması başarısız.")
        else:
            print("Aksis giriş başarısız")

if __name__ == "__main__":
    asyncio.run(main())
