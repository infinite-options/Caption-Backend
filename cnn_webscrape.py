# import json
# import re
# import time
# import os
# from selenium.webdriver.common.by import By
# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# import boto3

# def lambda_handler(event, context):
#     options = Options()
#     options.binary_location = "/opt/headless-chromium"
#     options.add_argument("--headless")
#     options.add_argument("--no-sandbox")
#     options.add_argument("--single-process")
#     options.add_argument("--disable-dev-shm-usage")

#     browser= webdriver.Chrome("/opt/chromedriver", chrome_options=options)
    
#     total_links=[]
#     from_val=0
#     page_val=1
    

#     while len(total_links)<10:
#         base_url = f'https://www.cnn.com/search?q=The+week+in&from={from_val}&size=10&page={page_val}&sort=newest&types=gallery&section='
#         browser.implicitly_wait(10)
#         browser.get(base_url)

#         # text_sections = browser.find_elements(By.XPATH, "//div[@class='container__headline container_list-with-images__headline']/span")
#         text_sections = browser.find_elements(By.XPATH, "//div[@class='container__headline  container_list-']/span")
        
#         # text_desc= browser.find_elements(By.XPATH, "//div[@class='container__date container_list-with-images__date inline-placeholder']")
#         text_desc= browser.find_elements(By.XPATH, "//div[@class='container__date']")

#         # img= browser.find_elements(By.XPATH, "//div[@class= 'image__container image']/picture[@class= 'image__picture']")
#         img= browser.find_elements(By.XPATH, "//div[@class= 'image__container']/picture[@class= 'image__picture']")
        
        
#         if not text_sections or not text_desc or not img:
#             response = {
#                 'statusCode': 400,
#                 'headers': {
#                 'Access-Control-Allow-Origin': '*'
#                 },
#                 'body': json.dumps(total_links)
#             }
#             # if response['statusCode']==400:
#             #     message = 'You are receiving this message because the Lambda Function "Cnn-web-scrape" is unable to retrieve the images from CNN. Please make necessary changes to the function, if there are any.'
#             #     sns = boto3.client('sns')
#             #     sns.publish(TopicArn='arn:aws:sns:us-west-2:580022141311:cnn_scrape_notify', Message=message)
#             return response
        
#         images= img[0].find_elements(By.XPATH, "//img[@src]")
#         pattern1 = r"The week in (\d+) photos"
#         pattern2= r"This week in (\d+) photos"
        
#         for i in range(len(text_sections)):
#             if re.match(pattern1, text_sections[i].text) or re.match(pattern2, text_sections[i].text):
#                 temp_obj={}
#                 temp_obj["article_link"]= text_sections[i].get_attribute("data-zjs-href")
#                 temp_obj["thumbnail_link"]=images[i].get_attribute("src")
#                 temp_obj["date"]=text_desc[i].text
#                 total_links.append(temp_obj)
#                 print(temp_obj)
#                 if len(total_links)==10:
#                     break
#         if len(total_links)==10:
#                     break
#         from_val+=10
#         page_val+=1
#     browser.close()
    
#     response = {
#         'statusCode': 200,
#         'headers': {
#             'Access-Control-Allow-Origin': '*'
#         },
#         'body': json.dumps(total_links)
#     }
#     return response


import json
import re
import time
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

class CNNWebScrape:
    def __init__(self):
        print("in cnn webscrape init")
        options = Options()
        options.binary_location = "/opt/headless-chromium"
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--single-process")
        options.add_argument("--disable-dev-shm-usage")

        self.browser = webdriver.Chrome("/opt/chromedriver", chrome_options=options)
        self.total_links = []
        self.from_val = 0
        self.page_val = 1

    def scrape_data(self):
        print("in cnn webscrape_data")
        while len(self.total_links) < 10:
            base_url = f'https://www.cnn.com/search?q=The+week+in&from={self.from_val}&size=10&page={self.page_val}&sort=newest&types=gallery&section='
            self.browser.implicitly_wait(10)
            self.browser.get(base_url)

            text_sections = self.browser.find_elements(By.XPATH, "//div[@class='container__headline  container_list-']/span")
            text_desc = self.browser.find_elements(By.XPATH, "//div[@class='container__date']")

            img = self.browser.find_elements(By.XPATH, "//div[@class= 'image__container']/picture[@class= 'image__picture']")

            if not text_sections or not text_desc or not img:
                self.close_browser()
                return {'statusCode': 400, 'headers': {'Access-Control-Allow-Origin': '*'}, 'body': json.dumps(self.total_links)}

            images = img[0].find_elements(By.XPATH, "//img[@src]")
            pattern1 = r"The week in (\d+) photos"
            pattern2 = r"This week in (\d+) photos"

            for i in range(len(text_sections)):
                if re.match(pattern1, text_sections[i].text) or re.match(pattern2, text_sections[i].text):
                    temp_obj = {}
                    temp_obj["article_link"] = text_sections[i].get_attribute("data-zjs-href")
                    temp_obj["thumbnail_link"] = images[i].get_attribute("src")
                    temp_obj["date"] = text_desc[i].text
                    self.total_links.append(temp_obj)
                    print(temp_obj)
                    if len(self.total_links) == 10:
                        break

            if len(self.total_links) == 10:
                break

            self.from_val += 10
            self.page_val += 1

        self.close_browser()

        return {'statusCode': 200, 'headers': {'Access-Control-Allow-Origin': '*'}, 'body': json.dumps(self.total_links)}

    def close_browser(self):
        self.browser.close()

def lambda_handler():
    print("in lambda handler")
    web_scraper = CNNWebScrape()
    return web_scraper.scrape_data()
