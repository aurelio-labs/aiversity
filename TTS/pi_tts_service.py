from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import uvicorn
import asyncio
import time
import re
import os

app = FastAPI()

class TextModel(BaseModel):
    text: str

# Setup Chrome options
chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--remote-debugging-port=9222")

# Set up custom user data directory for Chrome profile
user_data_dir = os.path.expanduser('~/ChromeSeleniumProfile')
chrome_options.add_argument(f"user-data-dir={user_data_dir}")
chrome_options.add_argument("--profile-directory=Default")

# Set path to the local chromedriver
current_dir = os.path.dirname(os.path.abspath(__file__))
chromedriver_path = os.path.join(current_dir, "chromedriver")
webdriver_service = Service(chromedriver_path)

# Initialize Chrome Browser
try:
    driver = webdriver.Chrome(service=webdriver_service, options=chrome_options)
    driver.get("https://pi.ai")
    print("Chrome initialized successfully")
except Exception as e:
    print(f"Error initializing Chrome: {e}")
    raise

# Wait for and click the unmute button
try:
    unmute_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "div.relative.flex.items-center.justify-end button"))
    )
    unmute_button.click()
    print("Unmute button clicked")
except Exception as e:
    print(f"Could not click the unmute button: {e}")

# Wait for and click the Pi 4 button
try:
    pi_4_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[text()='Pi 4']"))
    )
    pi_4_button.click()
    print("Pi 4 button clicked")
except Exception as e:
    print(f"Could not click the 'Pi 4' button: {e}")

lock = asyncio.Lock()

@app.post("/send-text/")
async def send_text(text_model: TextModel):
    text = re.sub(r'[^\u0000-\uFFFF]', '', text_model.text)
    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    # Prepare the instruction for Pi to repeat the text
    instruction = "REPEAT THE FOLLOWING TEXT EXACTLY, without any additional commentary: "
    full_text = instruction + text

    async with lock:
        try:
            textarea = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//textarea[@placeholder="Talk with Pi"]'))
            )
            textarea.clear()
            textarea.send_keys(full_text)
            submit_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="Submit text"]'))
            )
            submit_button.click()
            print("Text sent successfully")

            # Wait for Pi's response (optional, depending on whether you want to verify the response)
            response_element = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "whitespace-pre-wrap")]'))
            )
            response_text = response_element.text

            # You can add some basic verification here if needed
            if text.lower() in response_text.lower():
                print("Pi appears to have repeated the text as instructed")
            else:
                print("Pi's response might not contain the exact text. Manual verification may be needed.")

        except Exception as e:
            print(f"Error sending text or getting response: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return {"message": "Text sent successfully for TTS"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5050)