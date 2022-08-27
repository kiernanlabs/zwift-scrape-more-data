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
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from webdriver_manager.firefox import GeckoDriverManager

from credentials import *
import time
import zwift_scrape


def getRaceURLs(urlpage, driver=None):
    opts = Options()
    if driver == None: 
        close_at_end = 1
        driver = webdriver.Firefox(service=Service(GeckoDriverManager().install()), options=opts)
    
    print("Scraping data from: {}.".format(urlpage))
    driver.get(urlpage)
    
    if len(driver.find_elements(By.XPATH, '//*[@id="login"]/fieldset/div/div[1]/div/a')) > 0: zwift_scrape.login(driver)
    
    print("collecting race URLs...")
    
    resultsButton = driver.find_element(By.XPATH, '//button[@id="button_event_results"]')
    resultsButton.click()
    filterButton = driver.find_element(By.XPATH, '//button[@id="button_event_filter"]')
    filterButton.click()
    raceButton = driver.find_element(By.XPATH, '//button[@data-value="TYPE_RACE"]')
    raceButton.click()

    sleep(0.25)
    results = driver.find_element(By.XPATH, '//*[@id="zwift_event_list"]/tbody')
    links = results.find_elements(By.TAG_NAME, "a")
    print(f"found {len(links)} events")

    if close_at_end:
        driver.quit()

    urls = []
    for link in links:
        urls.append(link.get_attribute("href"))
    return urls

            
def main():
    startTime = time.time()
    parser = ArgumentParser(
        description="Scrape the first X urls from the zwiftpower results page"
    )
    parser.add_argument("count", nargs='?', type=int, default=10, help="number of URLs to scrape ZwiftPower results from")
    settings = parser.parse_args()
    
    opts = Options()
    service = Service(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=service, options=opts)

    urls = getRaceURLs("https://zwiftpower.com/", driver)
    print(f"{len(urls)} Events found; scraping first {settings.count}")
    
    urls = urls[0:settings.count]
    successFinishes = 0
    finishErrorURLs = []
    successPrimes = 0
    primeErrorURLs = []

    for n, url in enumerate(urls) :
        print(f'URL #{n+1}/{settings.count}: {url}')
        urlArray = [url]
        
        results = zwift_scrape.scrape(urlArray, driver)  

        for (name, event) in enumerate(results.items()):
            if event[1][0] is None: finishErrorURLs.append(url)
            else: 
                successFinishes += 1
                zwift_scrape.mkdirAndSave("finishes", event[1][0], event[0])
            if event[1][1] is None: primeErrorURLs.append(url)
            else: 
                successPrimes += 1
                zwift_scrape.mkdirAndSave("primes", event[1][1], event[0])

    print(f'==== [Run Report] Total Execution time: {round((time.time() - startTime)/60,1)} minutes')
    print(f'==== [Run Report] Successful finish data scrapes: {successFinishes}/{settings.count}')
    print(f'==== [Run Report] Successful prime data scrapes: {successPrimes}/{settings.count}')
    print(f'==== [Run Report] events with scrape errors:')
    for errorUrl in finishErrorURLs:
        print(f'==== [Run Report] * {errorUrl}')
    driver.quit()

if __name__ == "__main__":
    main()
