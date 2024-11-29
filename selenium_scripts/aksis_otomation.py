import os
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Email credentials from environment variables
SENDER_EMAIL = os.getenv('SENDER_EMAIL')   # Your email address
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD') # Your email password (or use an app-specific password for Gmail)
TO_EMAIL = os.getenv('TO_EMAIL')  # Recipient email address

# Check if all email credentials are set
if not all([SENDER_EMAIL, SENDER_PASSWORD, TO_EMAIL]):
    raise ValueError("Email credentials are not fully set. Please set them as environment variables.")

# Driver setup for Edge
USERNAME = os.getenv('USERNAME')   # Your Aksis username
PASSWORD = os.getenv('PASSWORD')   # Your Aksis password

# Check if all Aksis credentials are set
if not all([USERNAME, PASSWORD]):
    raise ValueError("Aksis credentials are not fully set. Please set them as environment variables.")

options = webdriver.EdgeOptions()
options.add_argument("--inprivate")  # Edge equivalent of incognito mode
options.add_experimental_option("detach", True)

driver = webdriver.Edge(options=options)  # Use Edge driver
driver.get("https://aksis.istanbul.edu.tr/Account/LogOn")

# Login info
user_input = driver.find_element(By.NAME, "UserName")
user_input.clear()
user_input.send_keys(USERNAME)

password_input = driver.find_element(By.NAME, "Password")
password_input.clear()
password_input.send_keys(PASSWORD)
password_input.send_keys(Keys.RETURN)

time.sleep(1)

# Navigate to marks page
driver.get("https://obs.istanbul.edu.tr/")
time.sleep(1)

# Close the pop-up
try:
    close_button = driver.find_element(By.XPATH, "//button[@data-dismiss='modal' and @aria-hidden='true']")
    close_button.click()
except Exception as e:
    print("No pop-up found: ", e)

# Navigate to marks page
driver.get("https://obs.istanbul.edu.tr/OgrenimBilgileri/SinavSonuclariVeNotlar/Index")
time.sleep(1)

# Extract marks from table
grid_element = driver.find_element(By.ID, "sinavSonucGrid")
rows = grid_element.find_elements(By.TAG_NAME, "tr")

mark_rows = []
for row in rows:
    if row.get_attribute("data-uid") is not None:
        mark_rows.append(row)

# Prepare the email content
message_body = "Exam Results:\n"
for row in mark_rows:
    row_tds = row.find_elements(By.TAG_NAME, "td")
    message_body += " | ".join([data.text for data in row_tds]) + "\n"

print("Extracted Marks:")
print(message_body)

# Email Sending Setup
msg = MIMEMultipart()
msg['From'] = SENDER_EMAIL
msg['To'] = TO_EMAIL
msg['Subject'] = "Your Exam Results"

# Attach the body with the email
msg.attach(MIMEText(message_body, 'plain'))

try:
    # Setting up the SMTP server (Gmail)
    server = smtplib.SMTP('smtp.gmail.com', 587)  # For Gmail SMTP
    server.starttls()  # Secure the connection
    server.login(SENDER_EMAIL, SENDER_PASSWORD)  # Login to your email account
    text = msg.as_string()
    
    # Send the email
    server.sendmail(SENDER_EMAIL, TO_EMAIL, text)
    print(f"Email sent successfully to {TO_EMAIL}")
    
    server.quit()  # Close the connection to the server
except Exception as e:
    print(f"Failed to send email: {e}")

# Close the browser
driver.close()
