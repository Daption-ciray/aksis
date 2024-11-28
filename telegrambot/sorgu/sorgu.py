import requests
import time
import csv
from bs4 import BeautifulSoup

def get_verification_token(session, url):
    response = session.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        token = soup.find("input", {"name": "__RequestVerificationToken"})["value"]
        return token
    else:
        print(f"Giriş sayfasına erişim başarısız: {response.status_code}")
        return None

def login_to_aksis(session, username, password, login_url, token):
    login_data = {
        "UserName": username,
        "Password": password,
        "__RequestVerificationToken": token
    }
    response = session.post(login_url, data=login_data)
    if response.status_code == 200 and "Oturum açma başarısız" not in response.text:
        print("Aksis'e başarılı giriş")
        return True
    else:
        print("Aksis giriş başarısız")
        return False

def check_aksis_api(session, api_url):
    response = session.post(api_url)
    if response.status_code == 200:
        try:
            json_response = response.json()
            print("Aksis API Yanıtı: ", json_response)
            return json_response.get('IsSuccess') == True
        except ValueError:
            print("Aksis API yanıtı JSON formatında değil")
            return False
    else:
        print(f"Aksis API isteğinde hata: {response.status_code}")
        return False

def post_to_obs_results(session, url, year, semester):
    payload = {
        "group": "DersAdi-asc",
        "yil": year,
        "donem": semester
    }
    response = session.post(url, data=payload)
    if response.status_code == 200:
        print("POST isteği başarılı.")
        data = response.json()
        save_to_csv(data)
    else:
        print(f"POST isteğinde hata: {response.status_code}")

def save_to_csv(data):
    if 'Data' in data:
        with open('dersler.csv', mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['SinavID', 'Ders Adı'])
            for entry in data['Data']:
                if 'Items' in entry:
                    for item in entry['Items']:
                        writer.writerow([item['SinavID'], item['DersAdi']])
        print("Dersler CSV dosyasına kaydedildi.")
    else:
        print("Veri formatı geçersiz veya boş.")

def main():
    username = input("TC: ")
    password = input("Şifre: ")
    year = input("Yıl: ")
    semester = input("Dönem: ")
    aksis_login_url = "https://aksis.istanbul.edu.tr/Account/LogOn"
    aksis_api_url = "https://aksis.istanbul.edu.tr/Home/Check667ForeignStudent"
    obs_url = "https://obs.istanbul.edu.tr"
    obs_post_url = "https://obs.istanbul.edu.tr/OgrenimBilgileri/SinavSonuclariVeNotlar/GetOgrenciSinavSonuc"

    session = requests.Session()
    token = get_verification_token(session, aksis_login_url)

    if token and login_to_aksis(session, username, password, aksis_login_url, token):
        if check_aksis_api(session, aksis_api_url):
            print("Aksis sayfasına erişim sağlandı")
            response_first = session.get(obs_url)
            if response_first.status_code == 200:
                print("İlk obs sayfasına erişim sağlandı")
                while True:
                    post_to_obs_results(session, obs_post_url, year, semester)
                    time.sleep(300)  # 5 dakika bekle
            else:
                print(f"İlk obs sayfasına erişim sağlanamadı: {response_first.status_code}")
        else:
            print("Aksis sayfasına erişim sağlanamadı")
    else:
        print("Aksis giriş başarısız")

if __name__ == "__main__":
    main()