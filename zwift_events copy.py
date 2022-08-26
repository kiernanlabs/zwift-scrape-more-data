from cProfile import label
import sys
import re
from os import path, listdir, mkdir, chmod
from stat import S_IXUSR, S_IWUSR, S_IRUSR
from time import sleep
import numpy as np
import pandas as pd
from argparse import ArgumentParser
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from credentials import *
import time
import zwift_scrape


def getEventURLs(urlpage, headless=False):
    opts = Options()
    if headless:
        opts.headless = True
    scraped_data = {} 
    platform = sys.platform
    driverPath = "./drivers/geckodriver-{}".format(platform)
    if platform == "win32":
        driverPath += ".exe"
    elif platform in ["linux", "darwin"]:
        chmod(driverPath, S_IXUSR | S_IWUSR | S_IRUSR)
    with webdriver.Firefox(
        executable_path=driverPath,
        service_log_path="./drivers/logs/geckodriver-{}_log.log".format(platform),
        options=opts,
    ) as driver:
        driver.implicitly_wait(10)
        print("Scraping data from: {}.".format(urlpage))
        driver.get(urlpage)
        
        login_button = driver.find_element(
            By.XPATH, '//*[@id="login"]/fieldset/div/div[1]/div/a'
        )
        login_button.click()
        
        sleep(1)
        emailField = driver.find_element(By.XPATH, '//input[@id="username"]')
        passwordField = driver.find_element(By.XPATH, '//input[@id="password"]')
        loginButton2 = driver.find_element(By.XPATH, '//button[@id="submit-button"]')
        emailField.send_keys(email)
        passwordField.send_keys(password)
        loginButton2.click()
        login_wait = WebDriverWait(driver, 30)
        
        print("collecting event URLs...")
        resultsButton = driver.find_element(By.XPATH, '//button[@id="button_event_results"]')
        resultsButton.click()
        sleep(0.25)
        results = driver.find_element(By.XPATH, '//*[@id="zwift_event_list"]/tbody')
        links = results.find_elements(By.TAG_NAME, "a")
        print(f"found {len(links)} events")
        urls = []
        for link in links:
            urls.append(link.get_attribute("href"))
        return urls
            
def main():
    startTime = time.time()
    parser = ArgumentParser(
        description="Scrape the first X urls from the zwiftpower results page"
    )
    parser.add_argument("count", nargs='?', default=25, help="number of URLs to scrape ZwiftPower results from")
    settings = parser.parse_args()
        
    urls = getEventURLs("https://zwiftpower.com/")
    print(f"{len(urls)} Events found; scraping first {settings.count}")
    
    urls = urls[0:settings.count]
    successFinishes = 0
    finishErrorURLs = []
    successPrimes = 0
    primeErrorURLs = []

    for n, url in enumerate(urls) :
        print(f'URL #{n+1}/{settings.count}: {url}')
        urlArray = [url]
        results = zwift_scrape.scrape(urlArray)  
        for (name, event) in enumerate(results.items()):
            if event[1][0] is None: finishErrorURLs.append(url)
            else: 
                successFinishes += 1
                zwift_scrape.mkdirAndSave("finishes", event[1][0], event[0])
            if event[1][1] is None: primeErrorURLs.append(url)
            else: 
                successPrimes += 1
                zwift_scrape.mkdirAndSave("primes", event[1][1], event[0])

    print(f'==== [Run Report] Total Execution time: {round((time.time() - startTime)/60,1)}')
    print(f'==== [Run Report] Successful finish data scrapes: {successFinishes}/{settings.count}')
    print(f'==== [Run Report] Successful prime data scrapes: {successPrimes}/{settings.count}')
    print(f'==== [Run Report] events with scrape errors:')
    for errorUrl in finishErrorURLs:
        print(f'==== [Run Report] * {errorUrl}')

if __name__ == "__main__":
    main()
