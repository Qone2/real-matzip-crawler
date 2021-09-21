import selenium.common.exceptions
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from traceback import format_exc
from selenium.webdriver.chrome.options import Options
import requests
import time
import platform
import json
import datetime
import random
import threading


chrome_option = Options()
chrome_option.add_argument("headless")
chrome_option.add_argument("window-size=1440x820")
# chrome_option.add_argument("disable-gpu")
chrome_option.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36')
id_counter = [0]


def driver_start():
    if platform.system() == "Windows":
        driver = webdriver.Chrome(executable_path="./chromedriver.exe", chrome_options=chrome_option)
    else:
        driver = webdriver.Chrome(executable_path="./chromedriver", chrome_options=chrome_option)
    driver.get("https://www.google.com")
    driver.implicitly_wait(30)
    with open("./secret.json", 'r') as f:
        secrets = json.load(f)
        user_id = secrets["insta_id" + str(id_counter[0] % 3)]
        user_pw = secrets["insta_pw"]

    driver.get("https://www.instagram.com/")
    time.sleep(5)
    driver.find_element_by_xpath(
        "/html/body/div[1]/section/main/article/div[2]/div[1]/div/form/div/div[1]/div/label/input").send_keys(user_id)
    driver.find_element_by_xpath(
        "/html/body/div[1]/section/main/article/div[2]/div[1]/div/form/div/div[2]/div/label/input").send_keys(user_pw)
    driver.find_element_by_xpath("/html/body/div[1]/section/main/article/div[2]/div[1]/div/form/div/div[3]").click()
    time.sleep(1)
    return driver


def crawl(driver, keyword):
    driver.get("https://www.instagram.com/explore/tags/" + keyword)
    try:
        WebDriverWait(driver, 30).until(EC.presence_of_element_located(
            (By.XPATH, "/html/body/div[1]/section/main/header/div[1]/div/div/img")))
    except selenium.common.exceptions.TimeoutException:
        WebDriverWait(driver, 30).until(EC.presence_of_element_located(
            (By.XPATH, "/html/body/div[1]/section/main/div/div/h2")))
    time.sleep(2)
    html = driver.page_source
    soup = BeautifulSoup(html, features="html.parser")

    posts = soup.select(".v1Nh3.kIKUG._bz0w")

    print(datetime.datetime.now())
    if len(posts) < 9:
        res = requests.delete("http://127.0.0.1:8000/post/" + keyword + '/' + "dummy")
        print(res.status_code)
        return
    for i in reversed(range(9)):
        post_id = posts[i].a["href"][3:-1]
        post_url = "https://www.instagram.com" + posts[i].a["href"]
        print(post_url)
        img_url = post_url + "media/?size=l"
        print(img_url)
        print(keyword)
        if requests.get(
                "http://127.0.0.1:8000/post/" + keyword + '/' + post_id).status_code == 200:
            continue
        driver.get(post_url)
        WebDriverWait(driver, 30).until(EC.presence_of_element_located(
            (By.XPATH, "/html/body/div[1]/section/main/div/div[1]/article/div/div[1]")))
        time.sleep(5)
        html = driver.page_source
        post_detail = BeautifulSoup(html, features="html.parser")
        insta_analysis = ""
        insta_analyses = post_detail.select("._97aPb.wKWK0")
        for analysis in insta_analyses:
            try:
                insta_analysis += analysis.img["alt"]
            except KeyError:
                pass
            except TypeError:
                pass
        texts = post_detail.select_one(".C4VMK")
        post_text = ""
        for j, text in enumerate(texts):
            if j == 1:
                post_text = str(text)
        is_ad = False
        if "광고" in post_text or "협찬" in post_text or "광고" in insta_analysis or "협찬" in insta_analysis:
            is_ad = True
        insta_analysis_food = False
        food_list = ["food", "sashimi", "croquette", "chow mein", "dessert", "hot pot", "pizza"]
        for food in food_list:
            if food in insta_analysis:
                insta_analysis_food = True
        headers = {
            'Content-Type': 'application/json'
        }
        payload = json.dumps({
            "images": [
                img_url
            ]
        })
        res = requests.post("http://127.0.0.1:5000/detections/by-url-list", headers=headers, data=payload)
        food_score = 0.0
        for detection in res.json()["response"][0]["detections"]:
            if detection["confidence"] > food_score:
                food_score = detection["confidence"]
        headers = {
            'Content-Type': 'application/json'
        }
        payload = json.dumps(
            {
                "post_id": post_id,
                "post_url": post_url,
                "img_url": img_url,
                "keyword": keyword,
                "food_score": food_score,
                "post_text": post_text,
                "insta_analysis": insta_analysis,
                "insta_analysis_food": insta_analysis_food,
                "is_ad": is_ad
            }
        )
        res = requests.post("http://127.0.0.1:8000/posts", headers=headers, data=payload)
        print(res.status_code)
        if res.status_code == 400:
            print(payload)
        time.sleep(1)
    time.sleep(10 + random.uniform(-2, 2))


def slow_crawl(driver, timer):
    try:
        while True:
            keyword_list = requests.get("http://127.0.0.1:8000/keywords").json()["keyword_list"]
            for keyword in keyword_list:
                crawl(driver, keyword)
            time.sleep(timer + random.uniform(-10, 10))
    except selenium.common.exceptions.TimeoutException:
        with open("time-out" + str(datetime.datetime.now()) + ".txt", 'w') as f:
            f.write(format_exc())
        id_counter[0] += 1
        next_driver = driver_start()
        slow_crawl(next_driver, timer)
    except selenium.common.exceptions.NoSuchElementException:
        with open("no-such-element" + str(datetime.datetime.now()) + ".txt", 'w') as f:
            f.write(format_exc())
        id_counter[0] += 1
        next_driver = driver_start()
        slow_crawl(next_driver, timer)


def fast_crawl(driver, timer):
    try:
        while True:
            keyword_list = requests.get("http://127.0.0.1:8000/not-crawled-yet").json()["keyword_list"]
            for keyword in keyword_list:
                crawl(driver, keyword)
            time.sleep(timer + random.uniform(-0.5, 0.5))
    except selenium.common.exceptions.TimeoutException:
        with open("time-out" + str(datetime.datetime.now()) + ".txt", 'w') as f:
            f.write(format_exc())
        id_counter[0] += 1
        next_driver = driver_start()
        fast_crawl(next_driver, timer)
    except selenium.common.exceptions.NoSuchElementException:
        with open("no-such-element" + str(datetime.datetime.now()) + ".txt", 'w') as f:
            f.write(format_exc())
        id_counter[0] += 1
        next_driver = driver_start()
        fast_crawl(next_driver, timer)


def main():
    driver = driver_start()
    driver1 = driver_start()

    threading.Thread(target=fast_crawl, args=(driver, 2)).start()
    time.sleep(600)
    threading.Thread(target=slow_crawl, args=(driver1, 3600)).start()


if __name__ == "__main__":
    main()
