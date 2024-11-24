from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from twilio.rest import Client  # Twilio library
import os
import time

# Twilio credentials (use environment variables for security)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "ACxxxxxxxxxxxxxxxxxxxxxx")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "xxxxxxxxxxxxxxxxxxxxxxxx")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "+19787189737")
TO_PHONE_NUMBER = os.getenv("TO_PHONE_NUMBER", "+905301536941")

# User credentials
USERNAME = input("Kullanıcı adı ya da TC gir: ")
PASSWORD = input("Şifreyi gir: ")

# Configure Edge browser options
options = webdriver.EdgeOptions()
options.add_argument("--inprivate")  # Edge equivalent of incognito mode
options.add_experimental_option("detach", True)

# Initialize Edge WebDriver
driver = webdriver.Edge(options=options)

try:
    # Open the login page
    driver.get("https://aksis.istanbul.edu.tr/Account/LogOn")

    # Login process
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, "UserName")))
    user_input = driver.find_element(By.NAME, "UserName")
    user_input.clear()
    user_input.send_keys(USERNAME)

    password_input = driver.find_element(By.NAME, "Password")
    password_input.clear()
    password_input.send_keys(PASSWORD)
    password_input.send_keys(Keys.RETURN)

    # Navigate to OBS link
    WebDriverWait(driver, 20).until(EC.url_contains("aksis.istanbul.edu.tr"))
    driver.get("https://obs.istanbul.edu.tr/")

    # Close the pop-up (if exists)
    try:
        close_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@data-dismiss='modal' and @aria-hidden='true']"))
        )
        close_button.click()
    except Exception as e:
        print("No pop-up to close or issue closing pop-up:", e)

    # Navigate to the marks page
    driver.get("https://obs.istanbul.edu.tr/OgrenimBilgileri/SinavSonuclariVeNotlar/Index")
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "sinavSonucGrid")))

    # Extract marks from table
    grid_element = driver.find_element(By.ID, "sinavSonucGrid")
    rows = grid_element.find_elements(By.TAG_NAME, "tr")

    mark_rows = []
    for row in rows:
        if row.get_attribute("data-uid") is not None:
            mark_rows.append(row)

    # Prepare SMS content
    message_body = "Exam Results:\n"
    for row in mark_rows:
        row_tds = row.find_elements(By.TAG_NAME, "td")
        message_body += " | ".join([data.text for data in row_tds]) + "\n"

    print("Extracted Marks:")
    print(message_body)

    # Twilio SMS Sending
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=message_body,
            from_=TWILIO_PHONE_NUMBER,
            to=TO_PHONE_NUMBER
        )
        print(f"SMS sent successfully! Message SID: {message.sid}")
    except Exception as e:
        print(f"Failed to send SMS: {e}")

except Exception as e:
    print(f"An error occurred: {e}")
finally:
    # Close the browser
    driver.quit()
