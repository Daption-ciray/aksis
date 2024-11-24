from flask import Flask, request
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import time

app = Flask(__name__)

# Temporary storage for user data
user_sessions = {}

# Path to your EdgeDriver (ensure it's in the correct path)
EDGEDRIVER_PATH = r'C:\Users\ciray\Downloads\edgedriver_win64\msedgedriver.exe'  # Bu yolu kendi indirdiğiniz msedgedriver konumuna göre güncelleyin

@app.route("/whatsapp", methods=["POST"])
def whatsapp_bot():
    incoming_msg = request.values.get("Body", "").strip()
    sender = request.values.get("From", "")  # WhatsApp sender number
    response = MessagingResponse()
    message = response.message()

    # Check if the user is new
    if sender not in user_sessions:
        user_sessions[sender] = {"step": 1}  # Initialize the conversation
        message.body("Welcome! Please enter your username:")
        return str(response)

    # Process user responses based on the current step
    step = user_sessions[sender]["step"]

    if step == 1:
        # Store username and ask for password
        user_sessions[sender]["username"] = incoming_msg
        user_sessions[sender]["step"] = 2
        message.body("Thank you! Now, please enter your password:")
    elif step == 2:
        # Store password and process login
        user_sessions[sender]["password"] = incoming_msg
        message.body("Logging in and retrieving your exam results... Please wait.")
        username = user_sessions[sender]["username"]
        password = user_sessions[sender]["password"]

        # Run the Selenium script to fetch results
        results = fetch_exam_results(username, password)
        if results:
            message.body(f"Here are your exam results:\n{results}")
        else:
            message.body("Failed to retrieve your results. Please try again later.")

        # End the session
        del user_sessions[sender]
    else:
        message.body("I didn't understand that. Let's start over. Please enter your username:")

    return str(response)


def fetch_exam_results(username, password):
    """
    Automates the login and results extraction process using Selenium.
    """
    try:
        # Configure Selenium WebDriver for Edge
        options = webdriver.EdgeOptions()
        options.add_argument("--incognito")
        driver = webdriver.Edge(executable_path=EDGEDRIVER_PATH, options=options)
        
        driver.get("https://aksis.istanbul.edu.tr/Account/LogOn")

        # Enter login credentials
        user_input = driver.find_element(By.NAME, "UserName")
        user_input.clear()
        user_input.send_keys(username)

        password_input = driver.find_element(By.NAME, "Password")
        password_input.clear()
        password_input.send_keys(password)
        password_input.send_keys(Keys.RETURN)

        time.sleep(2)

        # Navigate to OBS page and close pop-up
        driver.get("https://obs.istanbul.edu.tr/")
        time.sleep(2)
        try:
            close_button = driver.find_element(By.XPATH, "//button[@data-dismiss='modal' and @aria-hidden='true']")
            close_button.click()
        except Exception:
            pass

        # Navigate to exam results page
        driver.get("https://obs.istanbul.edu.tr/OgrenimBilgileri/SinavSonuclariVeNotlar/Index")
        time.sleep(2)

        # Extract results
        grid_element = driver.find_element(By.ID, "sinavSonucGrid")
        rows = grid_element.find_elements(By.TAG_NAME, "tr")
        mark_rows = [row for row in rows if row.get_attribute("data-uid")]

        # Prepare results
        results = "Exam Results:\n"
        for row in mark_rows:
            row_tds = row.find_elements(By.TAG_NAME, "td")
            results += " | ".join([data.text for data in row_tds]) + "\n"

        driver.quit()
        return results

    except Exception as e:
        print(f"Error during Selenium execution: {e}")
        driver.quit()
        return None

# If you want to send WhatsApp messages directly from the script:
def send_whatsapp_message(message, to_number):
    """
    Uses Selenium to send a WhatsApp message through WhatsApp Web.
    """
    # Initialize the driver for WhatsApp Web
    driver = webdriver.Edge(executable_path=EDGEDRIVER_PATH)

    # Open WhatsApp Web
    driver.get('https://web.whatsapp.com/')

    # Wait for user to scan QR code manually
    time.sleep(15)  # Adjust based on how long it takes you to scan the QR code

    # Find the contact and send the message
    contact = driver.find_element(By.XPATH, f'//span[@title="{to_number}"]')
    contact.click()

    message_box = driver.find_element(By.XPATH, '//div[@contenteditable="true"][@data-tab="1"]')
    message_box.send_keys(message)
    message_box.send_keys(Keys.RETURN)

    time.sleep(2)  # Wait for the message to send
    driver.quit()


if __name__ == "__main__":
    app.run(debug=True)
