import os
from dotenv import load_dotenv
import requests
import sqlite3
from apscheduler.schedulers.blocking import BlockingScheduler
import apprise


def notify_new_goods(new_goods):
    # Load the environment variables.
    load_dotenv()

    user = os.getenv("USER_EMAIL_NAME")
    password = os.getenv("USER_PASSWORD")

    # use apprise to send notification via email
    apobj = apprise.Apprise()
    apobj.add(f"mailto://{user}:{password}@gmail.com")

    # Construct the body of the notification with ttles, prices, and image URLs
    items_info = ""
    for item in new_goods:
        real_url = f"https://www.facebook.com{item['link']}"
        items_info += f"**Title: {item['title']}**, Price: {item['price']}, URL: {real_url}\r\n"

    apobj.notify(
        body=f'There are **{len(new_goods)}** new goods found!\r\n{items_info}',
        title='New goods found!',
        attach=[item['image'] for item in new_goods
                ],  # Attach images if the system supports it
        body_format=apprise.NotifyFormat.MARKDOWN)


def crawl_facebook_marketplace(city, query, max_price):

    res = requests.get(
        f"http://127.0.0.1:8000/crawl_facebook_marketplace?city={city}&query={query}&max_price={max_price}"
    )

    # Convert the response from json into a Python list.
    results = res.json()

    print(f"Number of results: {len(results)}")

    # Create a connection to the SQLite database.
    conn = sqlite3.connect("good.sqlite")
    c = conn.cursor()

    # Create a table to store the goods.
    c.execute(
        "CREATE TABLE IF NOT EXISTS good (id INTEGER, object_id TEXT, title TEXT, price INTEGER, location TEXT, url TEXT, img_url TEXT)"
    )

    new_goods = []
    for item in results:
        title = item["title"]
        price = item["price"]
        location = item["location"]
        url = f"https://www.facebook.com{item['link']}"
        object_id = item["link"].split("/")[3]
        img_url = item["image"]

        c.execute("SELECT * FROM good WHERE object_id=?", (object_id, ))
        if not c.fetchone():
            c.execute(
                "INSERT INTO good (object_id, title, price, location, url, img_url) VALUES (?, ?, ?, ?, ?, ?)",
                (object_id, title, price, location, url, img_url),
            )
            # store the new goods for notification
            new_goods.append(item)
            print(f"New good found: {url}")

            # Commit the changes to the database.
            conn.commit()

    # Close the connection to the database.
    conn.close()

    if new_goods:
        notify_new_goods(new_goods)


if __name__ == '__main__':

    # Load the environment variables.
    load_dotenv()

    keyword = os.getenv("SEARCH_KEYWORD")
    location = os.getenv("SEARCH_LOCATION")
    max_price = os.getenv("SEARCH_MAX_PRICE")

    scheduler = BlockingScheduler(timezone="Asia/Shanghai")

    scheduler.add_job(crawl_facebook_marketplace,
                      'interval',
                      args=[location, keyword, max_price],
                      minutes=1)

    scheduler.start()
