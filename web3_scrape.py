from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import pandas as pd
from selenium.common.exceptions import TimeoutException
from datetime import datetime  # Added for date suffix
import os  # Added for directory handling

options = Options()
# options.add_argument("--headless")

# Output directory
DOWNLOAD_DIR = "auction_exports"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 15)
driver.get("https://eauction.gov.in/eAuction/app?page=FrontEndEauctionByDate&service=page")
time.sleep(5)

try:
    closing_tab = driver.find_element(By.ID, "closingWeekTab")
    closing_tab.click()
    time.sleep(5)
except Exception as e:
    print("Could not click 'Closing within 7 days' tab:", e)

results = []
page_num = 1

while True:
    print(f"Scraping page {page_num}...")
    search_links = driver.find_elements(By.XPATH, "//a[starts-with(@id, 'view_')]")
    popup_urls = [link.get_attribute("href") for link in search_links]

    for url in popup_urls:
        driver.execute_script("window.open(arguments[0]);", url)
        driver.switch_to.window(driver.window_handles[-1])
        time.sleep(5)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        data = {}

        def get_value(label):
            td = soup.find('td', string=lambda s: s and label in s)
            if td and td.find_next_sibling('td'):
                return td.find_next_sibling('td').get_text(strip=True)
            return ""

        data['Organisation Chain'] = get_value("Organisation Chain")
        data['Auction ID'] = get_value("Auction ID")
        data['EMD Amount'] = get_value("EMD Amount in ₹")
        data['Starting Price'] = get_value("Starting Price in ₹")
        data['Submission Start Date'] = get_value("Submission Start Date")
        data['Submission End Date'] = get_value("Submission End Date")
        data['Auction Start Date'] = get_value("Auction Start Date")

        results.append(data)
        driver.close()
        driver.switch_to.window(driver.window_handles[0])

    try:
        next_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="linkFwd"]')))
        driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
        time.sleep(1)
        next_btn.click()
        time.sleep(3)
        page_num += 1
    except TimeoutException:
        print("No more pages or next button not clickable (timeout).")
        break
    except Exception as e:
        print("No more pages or next button not found.", e)
        break

driver.quit()

df = pd.DataFrame(results)
today_str = datetime.now().strftime('%Y%m%d')
output_file = os.path.join(DOWNLOAD_DIR, f"web3_auctions_{today_str}.csv")
df.to_csv(output_file, index=False)
print(f"Saved to {output_file}")