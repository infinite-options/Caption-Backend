import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import mysql.connector
from PIL import Image

def connect_database():
    host = "io-mysqldb8.cxjnrciilyjq.us-west-1.rds.amazonaws.com"
    user = "admin"
    password = "prashant"
    database = "captions"

    connection = mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database
    )
    if connection.is_connected():
        print("Connected to MySQL database")

    cursor = connection.cursor()

    return connection, cursor


def scrape_images(url):
    response = requests.get(url)
    if response.status_code >= 200 and response.status_code < 300:
        soup = BeautifulSoup(response.text, 'html.parser')
        images = soup.findAll('img')
        return images, url
    else:
        return None, None


def generate_url(start_day, start_month, end_day, end_month, year):
    month_names = {
        1: "january",
        2: "february",
        3: "march",
        4: "april",
        5: "may",
        6: "june",
        7: "july",
        8: "august",
        9: "september",
        10: "october",
        11: "november",
        12: "december"}
    end_day_prefix = "0" + str(end_day) if end_day < 10 else str(end_day)
    end_month_numeric = "0" + str(end_month) if end_month < 10 else str(end_month)
    url = "https://www.cnn.com/{year}/{month}/{day}/world/gallery/photos-this-week-{start_month}-{start_day}-{end_month}-{end_day}-ctrp/index.html".format(
        year=year, month=end_month_numeric, day=end_day_prefix, start_month=month_names[start_month],
        end_month=month_names[end_month], start_day=start_day, end_day=end_day)
    return url


def calculate_week_from_day_month_year(day, month, year):
    date_string = f"{year}-{month:02d}-{day:02d}"
    date_object = datetime.strptime(date_string, '%Y-%m-%d')
    _, week_number, _ = date_object.isocalendar()
    return week_number


def url_present_in_database(url):
    connection, cursor = connect_database()
    condition = "url = %s"  # Replace column_name and %s with your specific condition
    query = f"SELECT EXISTS (SELECT 1 FROM cnn_images WHERE {condition})"
    cursor.execute(query, (url,))  # Replace your_value with the value to check
    row_exists = cursor.fetchone()[0]
    cursor.close()
    connection.close()

    if row_exists:
        return True
    else:
        return False


def date_loop_until_start_of_year():
    today = datetime.today()
    start_of_year = datetime(today.year, 1, 1)
    count = 0
    valid_weeks = []
    #     while today >= start_of_year:
    while count < 10:
        start_date = today
        start_date -= timedelta(weeks=1)
        start_day = start_date.day
        start_month = start_date.month
        end_day = today.day
        end_month = today.month
        year = today.year
        url = generate_url(start_day, start_month, end_day, end_month, year)
        images, valid_url = scrape_images(url)
        if valid_url:
            week = calculate_week_from_day_month_year(end_day, end_month, year)
            valid_weeks.append([valid_url, week, year])
        today -= timedelta(days=1)
        count += 1
    return valid_weeks


def save_images(images, week, year, url):
    connection, cursor = connect_database()
    for no, image in enumerate(images):
        link = image['src']
        with open(str(no) + '.jpg', 'rb') as f:
            im = requests.get(link)
            image_binary = im.content
            insert_query = "INSERT INTO cnn_images (filename, content_type, data,week_no,year,url) VALUES (%s, %s, %s, %s, %s, %s)"
            cursor.execute(insert_query, (str(no) + '.jpg', 'image/jpg', image_binary, week, year, url))
            connection.commit()
    print("images saved to database for {url}".format(url=url))
    connection.close()
    cursor.close()


def get_images(url):
    connection, cursor = connect_database()
    query = "SELECT filename, data FROM cnn_images WHERE url = %s"
    cursor.execute(query, (url,))
    results = cursor.fetchall()
    cursor.close()
    connection.close()

    if results:
        for result in results:
            filename, image_data = result
            with open(filename, 'wb') as img_file:
                img_file.write(image_data)
            img = Image.open(filename)
            img.show()
    else:
        print("Images not found")


def main():
    # valid_week = date_loop_until_start_of_year()
    # for url, week, year in valid_week:
    #     if url_present_in_database(url):
    #         continue
    #     else:
    #         images, url = scrape_images(url)
    #         save_images(images, week, year, url)

    url = "https://www.cnn.com/2023/08/31/world/gallery/photos-this-week-august-24-august-31-ctrp/index.html"
    get_images(url)

    # connect_database()

main()

