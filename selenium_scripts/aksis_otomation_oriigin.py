from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

import time
#Driver

USERNAME=input("kullanıcı adı ya da TC gir:")
PASSWORD=input("şifreyi gir:")


options = webdriver.EdgeOptions()
options.add_argument("--inprivate")
options.add_experimental_option("detach",True)

driver = webdriver.Edge(options=options)
driver.get("https://aksis.istanbul.edu.tr/Account/LogOn")

#Login info


#fill the form

#username input
user_input = driver.find_element(By.NAME, "UserName")
user_input.clear()
user_input.send_keys(USERNAME)

#password input
password_input = driver.find_element(By.NAME, "Password")
password_input.clear()
password_input.send_keys(PASSWORD)
password_input.send_keys(Keys.RETURN)

#wait for page to load
time.sleep(1)


###navigate to obs link
driver.get("https://obs.istanbul.edu.tr/")

#close pop up
close_button = driver.find_element(By.XPATH, "//button[@data-dismiss='modal' and @aria-hidden='true']")

close_button.click()
#naviggate to marks page
driver.get("https://obs.istanbul.edu.tr/OgrenimBilgileri/SinavSonuclariVeNotlar/Index")
time.sleep(1)
#get marks grid
grid_element=driver.find_element(By.ID,"sinavSonucGrid")
#find rows which contains marks
rows=grid_element.find_elements(By.TAG_NAME,"tr")
mark_rows=list()
for row in rows:
    if row.get_attribute("data-uid") is not None:
        mark_rows.append(row)
#iterate respectively
for row in mark_rows:
    row_tds = row.find_elements(By.TAG_NAME, "td")
    for data in row_tds:
        print(data.text)
    print("\n")
    

driver.close()