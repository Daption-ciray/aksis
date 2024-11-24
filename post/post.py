import requests

# POST isteği için URL
url = "https://obs.istanbul.edu.tr/OgrenimBilgileri/SinavSonuclariVeNotlar/GetOgrenciSinavSonuc"

# Headers bilgileri
headers = {
#burayıda dolduruver kardeşim

}

# Body verileri
data = {
    "UserName": "",
    "Password": "",
    "yil": "2024",
    "donem": "1"
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
