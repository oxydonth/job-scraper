# -*- coding: utf-8 -*-

import csv
import json
import os
import pandas as pd
import re
import sys
import warnings

# Import packages for manipulating data and searching the web
from bs4 import BeautifulSoup
from time import sleep

from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options as Firefox_Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC

try:
    from urllib.parse import urlparse
except ImportError:
     from urlparse import urlparse

"""
Scrape Indeed for job positions and the associated information with a list of keywords (keywordfile) that have
keywords separated on each line and a list (locationfile) of cities, and/or states as an input file.
The file requires a radius r to indicate the number of miles around the location for which to search. Default
is 0, which means the jobs are confined to the city or state itself. The script also uses a limit (Default 10) of
how many pages of jobs to retrieve for each keyword and location. This script uses Beautiful Soup, Gecko Driver, and Selenium.
Usage: "python indeedScrape.py -k keywordfile -l locationfile -r radius -m limit -g geckodriverpath"
Example: "python src/python/indeedScrape.py -k data/indeed/keywords.txt -l data/indeed/locations.txt -g /Users/syedather/Downloads/geckodriver"
"""

def consent():
    """
    Click the legal consent banner when it pops up.
    """
    elements = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//section[@class='icl-LegalConsentBanner is-shown']"))).click()
    return None if elements else False

def extract_company_from_result(soup):
    """
    Extract company information from soup object.
    """
    companies = []
    for div in soup.find_all("div", attrs={"data-tn-component": "organicJob"}):
        company = div.find_all(name="span", attrs={"class":"company"})
        if len(company) > 0:
            for b in company:
                companies.append(b.text.strip())
        else:
            sec_try = div.find_all(name="span", attrs={"class":"result-link-source"})
            for span in sec_try:
                companies.append(span.text.strip())
    return(companies)

def extract_job_title_from_result(soup):
    """
    Extract job title information from soup object.
    """
    jobs = []
    for div in soup.find_all("div", attrs={"data-tn-component": "organicJob"}):
        for a in div.find_all(name="a", attrs={"data-tn-element":"jobTitle"}):
            jobs.append(a["title"])
    return(jobs)

def extract_location_from_result(soup):
    """
    Extract location from result.
    """
    locations = []
    spans = soup.find_all("div", attrs={"data-tn-component": "organicJob"})
    for span in spans:
        locations.append(span.text)
    return(locations)

def extract_salary_from_result(soup):
    """
    Extract salary information from soup object.
    """
    salaries = []
    for div in soup.find_all("div", attrs={"data-tn-component": "organicJob"}):
        try:
            salaries.append(div.find("nobr").text)
        except Except as Ex:
            try:
                div_two = div.find(name="div", attrs={"class":"sjcl"})
                div_three = div_two.find("div")
                salaries.append(div_three.text.strip())
            except:
                salaries.append("Nothing_found")
    return(salaries)

def extract_summary_from_result(soup):
    """
    Extract summary from results.
    """
    summaries = []
    spans = soup.find_all("div", attrs={"data-tn-component": "organicJob"})
    for span in spans:
        summaries.append(span.text.strip())
    return(summaries)

def get_data(baseurl, query, num_pages, location):
    """
    Get all the job posting data and save in a json file using below structure:
    {<count>: {"title": ..., "posting":..., "url":...}...}
    """
    # Convert the queried title to Indeed format.
    postings_dict = {}
    urls = get_urls(baseurl, query, num_pages, location)
    removealert()
    # Continue only if the requested number of pages is valid (when invalid, a number is returned instead of list).
    if isinstance(urls, list):
        num_urls = len(urls) # Get the number of urls.
        for i, url in enumerate(urls):
            df = get_info(url)
            postings_dict[i] = df.to_dict("dict")
            percent = (i+1) / num_urls
        # Save the dictionary as json file.
        file_name = query.replace("+", "_") + ".json"
        with open("output/indeed/" + file_name, "w") as f:
            json.dump(postings_dict, f)
            for key, value in postings_dict.items():
                csvwriter.writerow([key, value])
        print("All {} postings for {} in {} have been scraped and saved!".format(num_urls, query.replace("+", " "), location))
    else:
        print("Due to similar results, maximum number of pages is only {}. Please try again!".format(urls))

def get_info(url):
    """
    Get the text portion including both title and job description of the job posting from a given url.
    """
    removealert()
    # Get the url content as Beautiful Soup object.
    soup = get_soup(url)
    df = pd.DataFrame(columns=["Title","Location","Company","Salary", "Synopsis"])
    container = soup.findAll("div", {"class" : "result"})
    print(container)
    df = pd.DataFrame()
    # df = df.append({"Title":title, "Location":location, "Company":company, "Salary":salary, "Synopsis":synopsis}, ignore_index=True)
    return df

def get_soup(url):
    """
    Given the url of a page, this function returns the soup object.
    """
    driver.get(url) # Go to the url in Firefox.
    sleep(10) # Wait for the page to load.
    html = driver.page_source # Extract the page source.
    soup = BeautifulSoup(html, "html.parser") # Soup it.
    return soup

def get_urls(baseurl, query, num_pages, location):
    """
    Get all the job posting URLs resulted from a specific search.
    """
    removealert()
    # Get the first page.
    soup = get_soup(baseurl)
    urls = grab_job_links(soup)
    # Get the total number of postings found.
    posting_count = urls.count    
    removealert()    
    for url in urls:
        try:
            soup = get_soup(url)
            urls += grab_job_links(soup)
        except:
            continue
    removealert()
    return urls

def grab_job_links(soup):
    """
    Grab all non-sponsored job posting links from a Indeed search result
    page using the given soup object.
    """
    urls = []    
    removealert()    
    for link in soup.find_all("a", {"class" : "css-v0a1gu e8ju0x50"}):
        if(link!= None):
            url = link.get("href")            
            urls.append(url)
    return urls

def removealert():
    """
    Ignore and remove the jobalert asking for your email address to add to the mailing list
    We implement these methods of removing the alert.
    """
    try: # First, we try to use the built-in switch_to function to switch to the alert and
         # accept and dismiss it.
        alert = driver.switch_to.alert
        alertObj.accept()
        alertObj.dismiss()
    except:
        pass
    try: # If that doesn"t work, we try to look for the "popover-close-link" id and click it.
        driver.find_element_by_xpath("//a[@id='popover-close-link']").click()
    except:
        pass
    try: # If that doesn"t work, we look for the job title and click it.
        driver.find_element_by_xpath("//a[@data-tn-element='jobTitle']").click()
    except Exception as ex: # If that doesnt" work, we click on some body whitespace on the page.
        return

# Suppress FutureWarnings raised by numpy.
warnings.simplefilter(action="ignore", category=FutureWarning)

# Initialize the variables
locationfile = None
keywordfile = None
radius = None
limit = None
gdpath = None

# Load the arguments
args = sys.argv
for i, j in enumerate(args):
    if j == "-k": # file with the list of keywords that we search
        keywordfile = args[i+1]
    elif j == "-l": # file with the list of locations
        locationfile = args[i+1]
    elif j == "-r": # radius for each location
        radius = int(args[i+1])
    elif j == "-m": # page limit
        limit = int(args[i+1])
    elif j == "-g": # Gecko Driver path
        gdpath = args[i+1]

if radius is None: # Set default radius value to 0
    radius = 0
if limit is None: # Set default limit value to 10
    limit = 10

pathname = os.path.dirname(sys.argv[0])

errormessage = []
keywordfile = pathname+"/keywords.txt"
locationfile = pathname+"/locations.txt"
gdpath = "/usr/bin/geckodriver"

if keywordfile is None:
    errormessage.append("No keyword file given.")
if locationfile is None:
    errormessage.append("No location file given.")
if gdpath is None:
    errormessage.append("No Gecko Driver path given.")

helpmessage = ("Scrape Indeed for job positions and the associated information with a list of keywords (keywordfile) that have"
               "keywords separated on each line and a list (locationfile) of cities and/or states as an input file."
               "Radius (radius) indicates the number of miles around the location for which to search (default 0, which means the jobs are confined to the city or state itself)."
               "The script also uses a limit (Default 10) of how many pages of jobs to retrieve for each keyword and location."
               "This script uses Beautiful soup, Gecko Driver, and Selenium."
               "Example: python src/python/indeedScrape.py -k data/indeed/keywords.txt -l data/indeed/locations.txt -g /Users/syedather/Downloads/geckodriver"
               "Usage: python indeedScrape.py -k keywordfile -l locationfile -r radius -g geckodriverpath")

if errormessage:
    errormessage.insert(0, helpmessage)
    for i in errormessage:
        print(i)
    sys.exit()

# Input the list of keywords
keywords = [] # Initialize the list we will use to store keywords
with open(keywordfile, "r") as file: # Open the keyword file
    for line in file: # For each line in the file,
        keywords.append(line.replace("\n", "")) # append each line to the list keywords

# Do the same for locations
locations = []
with open(locationfile, "r") as file:
    for line in file:
        locations.append(line.replace("\n", ""))

# Print out the locations
print("Your locations are: " + "; ".join(locations))
# Print out the keywords
print("Your keywords are: " + ", ".join(keywords))

os.chdir(pathname)

# Check if the output file directory exists. If not, make it.
if not os.path.isdir("output/indeed"):
    os.mkdir("output/indeed")

# Same for the cleaned contentecho
if not os.path.isdir("output/indeed/cleaned"):
    os.mkdir("output/indeed/cleaned")

# Log path for a log of the data
logpath = "output/indeed/driver_cities.log"

options = Firefox_Options()
driverService = Service(gdpath)
options.set_preference("browser.download.folderList",2)
options.set_preference("browser.download.manager.showWhenStarting", False)
options.set_preference("browser.download.dir","/Data")
options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/octet-stream,application/vnd.ms-excel")
options.binary_location="/home/deck/firefox-esr/firefox"
driver = webdriver.Firefox(service=driverService, options=options)

# Loop through the list of cities and obtain information.
with open("output/indeed/cities.csv", "w") as csvfile:
    for l in locations: # For each locations in the list
        for kw in keywords: # For each keyword
            csvwriter = csv.writer(csvfile)
            removealert() # Check for jobalert to remove.
            baseurl = "https://www.indeed.de/jobs?q=" + str(kw.replace(" ", "+")) + "&l=" + str(l) + "&radius=" + str(radius)
            removealert()
            get_data(baseurl, kw, limit, l)