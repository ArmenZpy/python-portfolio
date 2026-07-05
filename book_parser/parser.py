import requests
from bs4 import BeautifulSoup
import csv
import time

URL = "https://books.toscrape.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

print("Запуск парсера...")
data = []
page = 1

while True:
    print(f"Обработка страницы {page}...")
    url = f"{URL}/catalogue/page-{page}.html"
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        print("Страницы закончились.")
        break

    soup = BeautifulSoup(response.text, "html.parser")
    products = soup.find_all("article", class_="product_pod")

    for product in products:
        title = product.h3.a["title"]
        price = product.find("p", class_="price_color").text
        data.append([title, price])

    page += 1
    time.sleep(1)

with open("products.csv", "w", newline="", encoding="utf-8-sig") as file:
    writer = csv.writer(file)
    writer.writerow(["Название", "Цена"])
    writer.writerows(data)

print(f"Готово. Собрано {len(data)} товаров. Файл: products.csv")