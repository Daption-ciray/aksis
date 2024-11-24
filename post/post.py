import requests
import time
from selenium import webdriver 
from selenium.webdriver.common.keys import Keys 
from selenium.webdriver.common.by import By

# Giriş bilgileri
username = input("TC: ")
password = input("Şifre: ")
yil = input("Yıl: ")
donem = input("Dönem: ")

# Tarayıcıyı başlatma ve oturum açma
options = webdriver.EdgeOptions()
options.add_argument("--inprivate")
driver = webdriver.Edge(options=options)
driver.get("https://aksis.istanbul.edu.tr/Account/LogOn")

# Giriş bilgilerini girme
user_input = driver.find_element(By.NAME, "UserName")
user_input.clear()
user_input.send_keys(username)

password_input = driver.find_element(By.NAME, "Password")
password_input.clear()
password_input.send_keys(password)
password_input.send_keys(Keys.RETURN)

# Giriş işlemi için bekleme
time.sleep(2)

# Navigate to marks page
driver.get("https://obs.istanbul.edu.tr/")
time.sleep(1)

# Çerezleri alma
session_cookies = driver.get_cookies()
driver.quit()
# Requests oturumu oluşturma ve çerezleri ekleme
session = requests.Session()
cookies = {cookie['name']: cookie['value'] for cookie in session_cookies}
session.cookies.update(cookies)
# POST isteği için URL
url = "https://obs.istanbul.edu.tr/OgrenimBilgileri/SinavSonuclariVeNotlar/GetOgrenciSinavSonuc"

# Headers bilgileri
headers = {
    "cookie": "; ".join([f"{key}={value}" for key, value in session.cookies.items()]),
}

# Body verileri
data = {
    "group": "DersAdi-asc",
    "yil": f"{yil}",
    "donem": f"{donem}"
}

# POST isteğini gönderme
response = requests.post(url, headers=headers, data=data)

# Yanıtı işleme
if response.status_code == 200:
    print("Başarılı İstek")
    try:
        print("Yanıt:", response.json())
    except requests.exceptions.JSONDecodeError:
        print("Yanıt JSON formatında değil.")
        print("Yanıt:", response.text)
else:
    print("İstek Başarısız")
    print("Durum Kodu:", response.status_code)
    print("Yanıt:", response.text)
