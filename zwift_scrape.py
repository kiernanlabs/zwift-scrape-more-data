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


def scrape(urlpage, headless=False):
    opts = Options()
    if headless:
        opts.headless = True
    scraped_data = {} 
    
    with webdriver.Firefox(service=Service(GeckoDriverManager().install()), options=opts
    ) as driver:
        driver.implicitly_wait(10)
        for n, url in enumerate(urlpage):
            print("--Scraping data from: {}.".format(url))
            finishData = []
            driver.get(url)
            if n == 0:
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
            raceName = login_wait.until(
                lambda driver: driver.find_element(
                    By.XPATH, '//*[@id="header_details"]/div[1]/h3'
                ).text
            )
            raceName = re.sub(r"[^A-Za-z0-9 ]+", "", raceName)
            raceName = toEventID(url) + " " + raceName
            
            # expecting <span data-value="1661013900" id="EVENT_DATE">Today 12:45</span>
            raceTimestamp = driver.find_element(
                    By.XPATH, '//*[@id="EVENT_DATE"]'
                ).get_attribute('data-value')
            print(f"--{n}:{raceName} - Downloading data")
            
            #Attempt to load the page
            try:
                _pages_loaded = WebDriverWait(driver, 1).until(
                    lambda driver: len(
                        driver.find_elements(
                            By.XPATH, '//*[@id="table_event_results_final_paginate"]/ul/li'
                        )[1:-1]
                    )
                    > 0
                )
            except:
                print(f"--{n}:{raceName} - failed to load")
                continue #do next URL
            
            #Attempt to capture finish positions
            try:
                pages = driver.find_elements(
                    By.XPATH, '//*[@id="table_event_results_final_paginate"]/ul/li'
                )[1:-1]
                nPages = len(pages)
                columnButton = driver.find_element(By.XPATH, '//*[@id="columnFilter"]/button')
                columnButton.click()
                sleep(0.25)
                rankBeforeButton = driver.find_element(By.XPATH, '//*[@id="columnFilter"]//*[@id="table_event_results_final_view_27"]/span')
                rankEventButton = driver.find_element(By.XPATH, '//*[@id="columnFilter"]//*[@id="table_event_results_final_view_28"]/span')
                rankEventButton.location_once_scrolled_into_view
                rankBeforeButton.click()
                rankEventButton.click()
                sleep(0.25)
                results = driver.find_element(
                    By.XPATH, '//*[@id="table_event_results_final"]/tbody'
                )
                print("--Collecting finish data for all riders...")
                for n in range(2, nPages + 2):
                    if n > 2:
                        button = driver.find_element(
                            By.XPATH,
                            '//*[@id="table_event_results_final_paginate"]/ul/li[{}]/a'.format(
                                n
                            ),
                        )
                        name1 = (
                            results.find_elements(By.TAG_NAME, "tr")[0]
                            .find_elements(By.TAG_NAME, "td")[2]
                            .text
                        )
                        driver.execute_script("arguments[0].click();", button)
                        while (
                            results.find_elements(By.TAG_NAME, "tr")[0]
                            .find_elements(By.TAG_NAME, "td")[2]
                            .text
                            == name1
                        ):
                            results = driver.find_element(
                                By.XPATH, '//*[@id="table_event_results_final"]/tbody'
                            )
                            sleep(0.25)
                    rows = results.find_elements(By.TAG_NAME, "tr")
                    for row in rows:
                        cols = row.find_elements(By.TAG_NAME, "td")
                        category = cols[0].text
                        eventID = toEventID(url)
                        name = toName(cols[2].text)
                        team = toTeam(cols[2].text)
                        time = finishTime(cols[3].text)
                        rankBefore = cols[17].text
                        rankEvent = cols[18].text

                        # if there is a primes column, go one more
                        primeCol = results.find_elements(
                            By.XPATH, '//*[@id="table_event_results_final"]//th[@title="Points allocated for crossing the banner inside the top 10 on various laps."]'
                        )
                        if primeCol:
                            rankBefore = cols[18].text
                            rankEvent = cols[19].text
                        
                        finishData += [{"EventID": eventID, "EventTimestamp": raceTimestamp, "Name": name, "Team": team, "Category": category, "Time": time, "RankBefore": rankBefore, "RankEvent": rankEvent}]
                print("--Found {} riders.".format(len(finishData)))
            except Exception as e:
                print(f"--Failed to load finish data:{e}")
                finishData = []
            
            #Attempt to capture primes positions
            try:
                toPrimes = driver.find_element(By.XPATH, '//*[@id="zp_submenu"]/ul/li[4]/a')
                toPrimes.click()
                cButtons = driver.find_elements(
                    By.XPATH, '//*[@id="table_scroll_overview"]/div[1]/div[1]/button'
                )
                categoryBottons = [
                    but for but in cButtons if not (but.text == "" or but.text == "All")
                ]
                pButtons = driver.find_elements(
                    By.XPATH, '//*[@id="table_scroll_overview"]/div[1]/div[2]/button'
                )
                primeButtons = [but for but in pButtons if not but.text == ""]
                primeResults = driver.find_element(
                    By.XPATH, '//*[@id="table_event_primes"]/tbody'
                )
                n = 0
                while True:
                    try:
                        n = n + 1
                        testCell = (
                            primeResults.find_elements(By.TAG_NAME, "tr")[0]
                            .find_elements(By.TAG_NAME, "td")[3]
                            .text
                        )
                    except IndexError:
                        if n > 10 :
                            raise Exception("Timeout waiting for prime data")
                        sleep(0.25)
                    else:
                        break
                presults = {}
                primeButtons.reverse()
                for catBut in categoryBottons:
                    category = catBut.text
                    print("--Collecting prime data for category {}...".format(category))
                    presults[category] = {}
                    catBut.click()
                    for primeBut in primeButtons:
                        prime = primeBut.text
                        presults[category][prime] = {}
                        primeBut.click()
                        testCell2 = testCell
                        while testCell == testCell2:
                            try:
                                testCell2 = (
                                    driver.find_element(
                                        By.XPATH, '//*[@id="table_event_primes"]/tbody'
                                    )
                                    .find_elements(By.TAG_NAME, "tr")[0]
                                    .find_elements(By.TAG_NAME, "td")[3]
                                    .text
                                )
                            except StaleElementReferenceException:
                                testCell2 = testCell
                            sleep(0.25)

                        testCell = testCell2
                        primeResults = driver.find_element(
                            By.XPATH, '//*[@id="table_event_primes"]/tbody'
                        )
                        rows = primeResults.find_elements(By.TAG_NAME, "tr")
                        for row in rows:
                            cols = row.find_elements(By.TAG_NAME, "td")
                            lap = cols[0].text
                            splitName = cols[1].text
                            scores = {
                                toName(cols[n].text): primeTime(cols[n + 1].text, prime)
                                for n in range(2, len(cols), 2)
                                if not cols[n].text == ""
                            }
                            combinedName = "{}_{}".format(lap, splitName)
                            presults[category][prime][combinedName] = scores
            except Exception as e:
                print(f"--Failed to load prime data:{e}")
                presults = []
            scraped_data[raceName] = [formatFinishes(finishData), formatPrimes(presults)]
            print("--Closing connection to {}".format(url))
        print("--Formatting scraped data...")
    print("--Done.")
    return scraped_data

def toEventID(url):
    #expected URL format: https://zwiftpower.com/events.php?zid=3072775
    eventID = ""
    if len(url.split("zid=")) > 1:
        eventID = url.split("zid=")[1]
    return eventID

def toTeam(string):
    #returns the team name if it exists
    team = ""
    if len(string.split("\n")) > 1:
        team = string.split("\n")[1]
    return team

def toName(string):
    # print(string)
    name = string.split("\n")[0]
    # name = re.sub(r'[^A-Za-z0-9 ]+', '', name)
    # name = name.split(' ')[0]+' '+name.split(' ')[1]
    return name

def secsToMS(string):
    flt = float(string)
    return int(flt * 1000)


def hrsToMS(string):
    ints = [int(t) for t in string.split(":")]
    ints.reverse()
    time = 0
    for n, t in enumerate(ints):
        time += 1000 * t * (60**n)
    return time


def toTime(string):
    if len(string.split(".")) == 1:
        return hrsToMS(string)
    else:
        return secsToMS(string)


def finishTime(string):
    timeStrs = string.split("\n")
    if len(timeStrs) == 1:
        return toTime(timeStrs[0])
    else:
        time = toTime(timeStrs[0])
        if (timeStrs[0].split(".") == 1) and (timeStrs.split(".") < 1):
            tString = timeStrs[1].split(".")[1]
            tString = tString.replace("s", "")
            tString = "0." + tString
            if float(tString) < 0.5:
                time -= 1000 - secsToMS(tString)
            else:
                time += secsToMS(tString)
        return time


def primeTime(string, prime):
    if prime == "First over line":
        if string == "":
            return 0
        else:
            string = string.replace("+", "")
            string = string.replace("s", "")
            return toTime(string)
    else:
        return finishTime(string)


def getFinishPositions(sortP):
    currCat = None
    pos = 1
    positions = []
    for cat in sortP["Category"]:
        if currCat != cat:
            currCat = cat
            pos = 1
        positions += [pos]
        pos += 1
    return positions


def getPrimePositions(sortP):
    currDesc = None
    pos = 1
    positions = []
    for _, row in sortP.iterrows():
        desc = "{}_{}_{}".format(row["Category"], row["Split"], row["Prime"])
        if desc != currDesc:
            currDesc = desc
            pos = 1
        positions += [pos]
        pos += 1
    return positions


def formatFinishes(data):
    if data == []: return None
    categories = list(set([x["Category"] for x in data]))
    toFile = {"EventID": [], "EventTimestamp": [], "Name": [], "Team": [], "Category": [], "Time (ms)": [], "RankBefore": [], "RankEvent": []}
    for rider in data:
        toFile["EventID"] += [rider["EventID"]]
        toFile["EventTimestamp"] += [rider["EventTimestamp"]]
        toFile["Name"] += [rider["Name"]]
        toFile["Team"] += [rider["Team"]]
        toFile["Category"] += [rider["Category"]]
        toFile["Time (ms)"] += [rider["Time"]]
        toFile["RankBefore"] += [rider["RankBefore"]]
        toFile["RankEvent"] += [rider["RankEvent"]]
    fPand = pd.DataFrame.from_dict(toFile)
    sortedData = fPand.sort_values(by=["Category", "Time (ms)"])
    positions = getFinishPositions(sortedData)
    sortedData["Position"] = positions
    return sortedData


def formatPrimes(data):
    if data == []: return None
    keys = ["Category", "Prime", "Split", "Rider", "Time (ms)"]
    columns = [[] for _ in keys]
    for key0, data0 in data.items():
        for key1, data1 in data0.items():
            for key2, data2 in data1.items():
                for name, time in data2.items():
                    for index, value in enumerate((key0, key1, key2, name, time)):
                        columns[index].append(value)
    pPand = pd.DataFrame(dict(zip(keys, columns)))
    sortedData = pPand.sort_values(by=["Category", "Split", "Prime", "Time (ms)"])
    positions = getPrimePositions(sortedData)
    sortedData["Position"] = positions
    return sortedData


def mkdirAndSave(name, data, filePath):
    if data is None: return
    resultsPath = "./results/"
    if not path.exists(resultsPath):
        mkdir(resultsPath)
    if not path.exists(path.join(resultsPath, filePath)):
        mkdir(path.join(resultsPath, filePath))
    savePath = path.join(resultsPath,filePath, name + ".csv")
    data.to_csv(savePath, index=False)


# def exportPrimes(primes):
def main():
    parser = ArgumentParser(
        description="Scrape all race time data (finish position and primes)  from a zwiftpower URL"
    )
    parser.add_argument("URL", nargs='+', help="URLs to scrape ZwiftPower results from (must include at least one).")
    parser.add_argument(
        "--saveName",
        "-s",
        help="Specify a filename for the output (default is zwiftpower race title)",
    )
    settings = parser.parse_args()
    results = scrape(settings.URL)
    for n, (name, event) in enumerate(results.items()):
        name = re.sub(r"[^A-Za-z0-9 ]+", "", name)
        if settings.saveName:
            name = f"{settings.saveName}_{n}"
        mkdirAndSave("finishes", event[0], name)
        mkdirAndSave("primes", event[1], name)

if __name__ == "__main__":
    main()
