# Import libraries
import requests
from bs4 import BeautifulSoup
import re
import json
import concurrent.futures
import pandas as pd

# Defining functions

# Functions for scraping apartments

def fetch_links_from_page_apartment(counter):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }
    url = f'https://www.immoweb.be/en/search/apartment/for-sale?countries=BE&page={counter}'
    print(url)
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.content, 'html.parser')
    page_links = [elem['href'] for elem in soup.find_all('a', href=True) if 'classified/apartment/' in elem['href']]
    return page_links

# Retrieve links of all the apartments from a page
def retrieve_apartment_links():
    apartments_url = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(fetch_links_from_page_apartment, counter) for counter in range(1, 2)]  # CHANGE FOR THE NUMBER OF PAGES
        for future in concurrent.futures.as_completed(futures):
            try:
                page_links = future.result()
                apartments_url.extend(page_links)
            except Exception as exc:
                print(f'Generated an exception: {exc}')
    
    return apartments_url

# Function for scraping apartment info from links
def retrieve_apartment_info(url):
    # Fetch the page content using requests
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    req_info = requests.get(url, headers=headers)

    if req_info.status_code != 200:
        print(f"Error fetching {url}: {req_info.status_code}")
        return None

    print(f"Scraping {url}")

    # Parse the HTML content with BeautifulSoup
    soup = BeautifulSoup(req_info.content, "lxml")

    # Find the script tag containing the JSON data
    try:
        data_script = soup.find_all("script")[11].text  # Update this index if it varies
    except IndexError:
        print(f"Could not find the data script in {url}")
        return None

    # Clean up the JavaScript to get the JSON data
    x = re.sub(r"\s+", "", data_script)
    x = re.sub(r"window.classified=", "", x)
    x = x[:-1]  # Remove the trailing semicolon

    # Parse the JSON data
    try:
        data_dict = json.loads(x)
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {url}")
        return None

    # Extract the relevant fields and handle missing data
    classified_dict = {}

    # Get the nested value from the dictionary in each page
    def get_nested_value(data, *keys):
        """Safe access to nested values in the dictionary."""
        for key in keys:
            if isinstance(data, dict):
                data = data.get(key, {})
            else:
                return None
        return data if data else None

    classified_dict["Postcode"] = get_nested_value(
        data_dict, "property", "location", "postalCode"
    )
    classified_dict["Type"] = get_nested_value(data_dict, "property", "type")
    classified_dict["Subtype"] = get_nested_value(data_dict, "property", "subtype")
    classified_dict["Price"] = get_nested_value(data_dict, "price", "mainValue")
    classified_dict["Bedrooms"] = get_nested_value(
        data_dict, "property", "bedroomCount"
    )
    classified_dict["Area"] = get_nested_value(
        data_dict, "property", "netHabitableSurface"
    )
    classified_dict["Kitchen"] = get_nested_value(
        data_dict, "property", "kitchen", "type"
    )
    classified_dict["Fireplace"] = get_nested_value(
        data_dict, "property", "fireplaceExists"
    )
    classified_dict["Frontages"] = get_nested_value(
        data_dict, "property", "building", "facadeCount"
    )
    classified_dict["Garden"] = get_nested_value(data_dict, "property", "hasGarden")
    classified_dict["Garden_surface"] = get_nested_value(
        data_dict, "property", "gardenSurface"
    )
    classified_dict["Terrace"] = get_nested_value(data_dict, "property", "hasTerrace")
    classified_dict["Terrace_Surface"] = get_nested_value(
        data_dict, "property", "terraceSurface"
    )
    classified_dict["Furnished"] = get_nested_value(
        data_dict, "transaction", "sale", "isFurnished"
    )
    classified_dict["Type_of_sale"] = get_nested_value(
        data_dict, "transaction", "subtype"
    )
    classified_dict["State_of_building"] = get_nested_value(
        data_dict, "property", "building", "condition"
    )
    classified_dict["Swimmingpool"] = get_nested_value(
        data_dict, "property", "hasSwimmingPool"
    )
    classified_dict["ID IMMOWEB"] = get_nested_value(data_dict, "id")
    classified_dict["Cadastral_income"] = get_nested_value(
        data_dict, "transaction", "sale", "cadastralIncome"
    )
    classified_dict["Plot_surface"] = get_nested_value(
        data_dict, "property", "land", "surface"
    )
    return classified_dict

# Function to make it faster with threading
def scraping_apartment():
    apartment_data = []
    url = retrieve_apartment_links()
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_url = {executor.submit(retrieve_apartment_info, link): link for link in url}
        for future in concurrent.futures.as_completed(future_to_url):
            try:
                data = future.result()
                if data:  # Ensure data is not None
                    apartment_data.append(data)
            except Exception as exc:
                print(f'Generated an exception: {exc}')
    
    return apartment_data

# Functions to scrape houses

# Functions for retrieving links for houses
def fetch_links_from_page_house(counter):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }
    url = f'https://www.immoweb.be/en/search/house/for-sale?countries=BE&page={counter}'
    print(url)
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.content, 'html.parser')
    page_links = [elem['href'] for elem in soup.find_all('a', href=True) if 'classified/house/' in elem['href']]
    return page_links

# Retrieve links of all the houses from a page
def retrieve_house_links():
    houses_url = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(fetch_links_from_page_house, counter) for counter in range(1, 2)]  # CHANGE FOR THE NUMBER OF PAGES
        for future in concurrent.futures.as_completed(futures):
            try:
                page_links = future.result()
                houses_url.extend(page_links)
            except Exception as exc:
                print(f'Generated an exception: {exc}')
    
    return houses_url

# Function for scraping houses info from links
def retrieve_house_info(url):
    # Fetch the page content using requests
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    req_info = requests.get(url, headers=headers)

    if req_info.status_code != 200:
        print(f"Error fetching {url}: {req_info.status_code}")
        return None

    print(f"Scraping {url}")

    # Parse the HTML content with BeautifulSoup
    soup = BeautifulSoup(req_info.content, "lxml")

    # Find the script tag containing the JSON data
    try:
        data_script = soup.find_all("script")[11].text  # Update this index if it varies
    except IndexError:
        print(f"Could not find the data script in {url}")
        return None

    # Clean up the JavaScript to get the JSON data
    x = re.sub(r"\s+", "", data_script)
    x = re.sub(r"window.classified=", "", x)
    x = x[:-1]  # Remove the trailing semicolon

    # Parse the JSON data
    try:
        data_dict = json.loads(x)
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {url}")
        return None

    # Extract the relevant fields and handle missing data
    classified_dict = {}

    # Get the nested value from the dictionary in each page
    def get_nested_value(data, *keys):
        """Safe access to nested values in the dictionary."""
        for key in keys:
            if isinstance(data, dict):
                data = data.get(key, {})
            else:
                return None
        return data if data else None

    classified_dict["Postcode"] = get_nested_value(
        data_dict, "property", "location", "postalCode"
    )
    classified_dict["Type"] = get_nested_value(data_dict, "property", "type")
    classified_dict["Subtype"] = get_nested_value(data_dict, "property", "subtype")
    classified_dict["Price"] = get_nested_value(data_dict, "price", "mainValue")
    classified_dict["Bedrooms"] = get_nested_value(
        data_dict, "property", "bedroomCount"
    )
    classified_dict["Area"] = get_nested_value(
        data_dict, "property", "netHabitableSurface"
    )
    classified_dict["Kitchen"] = get_nested_value(
        data_dict, "property", "kitchen", "type"
    )
    classified_dict["Fireplace"] = get_nested_value(
        data_dict, "property", "fireplaceExists"
    )
    classified_dict["Frontages"] = get_nested_value(
        data_dict, "property", "building", "facadeCount"
    )
    classified_dict["Garden"] = get_nested_value(data_dict, "property", "hasGarden")
    classified_dict["Garden_surface"] = get_nested_value(
        data_dict, "property", "gardenSurface"
    )
    classified_dict["Terrace"] = get_nested_value(data_dict, "property", "hasTerrace")
    classified_dict["Terrace_Surface"] = get_nested_value(
        data_dict, "property", "terraceSurface"
    )
    classified_dict["Furnished"] = get_nested_value(
        data_dict, "transaction", "sale", "isFurnished"
    )
    classified_dict["Type_of_sale"] = get_nested_value(
        data_dict, "transaction", "subtype"
    )
    classified_dict["State_of_building"] = get_nested_value(
        data_dict, "property", "building", "condition"
    )
    classified_dict["Swimmingpool"] = get_nested_value(
        data_dict, "property", "hasSwimmingPool"
    )
    classified_dict["ID IMMOWEB"] = get_nested_value(data_dict, "id")
    classified_dict["Cadastral_income"] = get_nested_value(
        data_dict, "transaction", "sale", "cadastralIncome"
    )
    classified_dict["Plot_surface"] = get_nested_value(
        data_dict, "property", "land", "surface"
    )
    return classified_dict

# Function to make it faster with threading
def scraping_house():
    house_data = []
    url = retrieve_house_links()
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_url = {executor.submit(retrieve_house_info, link): link for link in url}
        for future in concurrent.futures.as_completed(future_to_url):
            try:
                data = future.result()
                if data:  # Ensure data is not None
                    house_data.append(data)
            except Exception as exc:
                print(f'Generated an exception: {exc}')
    
    return house_data

# Function to save the data in a csv file apartment
def save_csv_apartment(classified_dict):
    # Filter out None entries if they exist
    classified_dict = [entry for entry in classified_dict if entry is not None]
    
    if classified_dict:  # Ensure there is data to save
        df = pd.DataFrame(classified_dict)
        df.to_csv("datasets/data_immo_eliza_apartment.csv", index=False)
        print("Data saved as data_immo_eliza_apartment.csv")
    else:
        print("No valid data to save.")
    return "data_immo_eliza_apartment.csv"

# Function to save the data in a csv file houses
def save_csv_house(classified_dict):
    # Filter out None entries if they exist
    classified_dict = [entry for entry in classified_dict if entry is not None]
    
    if classified_dict:  # Ensure there is data to save
        df = pd.DataFrame(classified_dict)
        df.to_csv("datasets/data_immo_eliza_house.csv", index=False)
        print("Data saved as data_immo_eliza_house.csv")
    else:
        print("No valid data to save.")
    return "data_immo_eliza_house.csv"

# Function to concatenate the 2 csv files
def save_all_data_to_csv():
    df1 = pd.read_csv('datasets/data_immo_eliza_apartment.csv')
    df2 = pd.read_csv('datasets/data_immo_eliza_house.csv')
    df = pd.concat([df1, df2])
    df.to_csv('datasets/all_data_immo_eliza.csv', index=False)
    print("Data concatenated and saved as all_data_immo_eliza.csv")
    return 'all_data_immo_eliza.csv'

def scraping_apartment_main():
    data_apartment = scraping_apartment()
    save_csv_apartment(data_apartment)

def scraping_house_main():
    data_house = scraping_house()
    save_csv_house(data_house)

def main():
    scraping_apartment_main()
    scraping_house_main()
    save_all_data_to_csv()

main()