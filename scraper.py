from selenium import webdriver
from selenium.webdriver.chrome.service import Service 

from selenium.webdriver.common.by import By
from transformers import pipeline
import pandas as pd
import time
import datetime

start = time.time()

chrome_service = Service()
chrome_options = webdriver.ChromeOptions()
options = [
    "--headless",
    "--disable-gpu",
    "--window-size=1920,1200",
    "--ignore-certificate-errors",
    "--disable-extensions",
    "--no-sandbox",
    "--disable-dev-shm-usage"
]
for option in options:
    chrome_options.add_argument(option)

driver = webdriver.Chrome(service=chrome_service, options=chrome_options)


sentiment_analyzer = pipeline("text-classification", model="cardiffnlp/twitter-roberta-base-sentiment-latest")

# This script is run in a github action at 3:00 AM UTC, which is 10:00 PM EST the day before
today = datetime.date.today() - datetime.timedelta(days=1)
yesterday = today - datetime.timedelta(days=1)

print(f"{today=}")

URL = f"https://www.nytimes.com/{yesterday.year}/{yesterday.month:02}/{yesterday.day:02}/crosswords/daily-puzzle-{today.year}-{today.month:02}-{today.day:02}.html"

driver.get(URL)

print(driver.title)

button = driver.find_element(By.ID, "comments-speech-bubble-header")
button.click()

comments = driver.find_elements(By.CLASS_NAME, "css-aa7djq")
last_count = len(comments)
while True:
    comments = driver.find_elements(By.CLASS_NAME, "css-aa7djq")
    driver.execute_script("arguments[0].scrollIntoView();", comments[-1])
    time.sleep(5)
    comments = driver.find_elements(By.CLASS_NAME, "css-aa7djq")
    new_count = len(comments)
    print(f"Comments: {new_count}")
    if new_count == last_count:
        break
    last_count = new_count

comment_dict = {
    "text": [],
    "recommends": [],
    "label": [],
    "score": [],
}

for comment in comments:
    text = comment.find_element(By.CLASS_NAME, "css-1ep7e7p").text
    comment_dict["text"].append(text)

    try:
        num_recs = int(comment.find_element(By.CLASS_NAME, "css-1ledvhd").text.split(" ")[0])
    except ValueError:
        num_recs = 0
    comment_dict["recommends"].append(num_recs)

    sentiment = sentiment_analyzer(text)[0]
    comment_dict["label"].append(sentiment["label"])
    comment_dict["score"].append(sentiment["score"])

df = pd.DataFrame(comment_dict)
df.to_csv(f"comments_{today:%Y-%m-%d}.csv", index=False)

driver.quit()

print(f"Time: {time.time() - start} seconds")