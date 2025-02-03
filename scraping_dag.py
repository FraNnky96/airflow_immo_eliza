# Import libraries
import requests
from bs4 import BeautifulSoup
import re
import json
import pandas as pd
import concurrent.futures
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

# Defining functions

# Functions for scraping appartments

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

# Retreive links of all the appartments from a page
def retreive_apartment_links():
    appartements_url = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(fetch_links_from_page_apartment, counter) for counter in range(1, 3)]        # CHANGE FOR THE NUMBER OF PAGES
        for future in concurrent.futures.as_completed(futures):
            try:
                page_links = future.result()
                appartements_url.extend(page_links)
            except Exception as exc:
                print(f'Generated an exception: {exc}')
    
    return appartements_url


# Function for scraping apartment info from links
def retreive_apartment_info(url):
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
    apartement_data = []
    url = retreive_apartment_links()
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_url = {executor.submit(retreive_apartment_info, link): link for link in url}
        for future in concurrent.futures.as_completed(future_to_url):
            try:
                data = future.result()
                apartement_data.append(data)
            except Exception as exc:
                print(f'Generated an exception: {exc}')
    
    return apartement_data

# Function to save the data in a csv file apartment
def save_csv_apartement(classified_dict):
    df = pd.DataFrame(
        classified_dict
    )  # Convert the list of dictionaries into a DataFrame
    df.to_csv("data_immo_eliza_apartment.csv", index=False)
    print("Data saved as data_immo_eliza_apartment.csv")
    return "data_immo_eliza_apartment.csv"


# Functions to scrape houses

# Functions for retreiving links for houses
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

# Retreive links of all the houses from a page
def retreive_house_links():
    appartements_url = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(fetch_links_from_page_house, counter) for counter in range(1, 3)]        # CHANGE FOR THE NUMBER OF PAGES
        for future in concurrent.futures.as_completed(futures):
            try:
                page_links = future.result()
                appartements_url.extend(page_links)
            except Exception as exc:
                print(f'Generated an exception: {exc}')
    
    return appartements_url


# Function for scraping houses info from links
def retreive_house_info(url):
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
    apartement_data = []
    url = retreive_house_links()
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_url = {executor.submit(retreive_house_info, link): link for link in url}
        for future in concurrent.futures.as_completed(future_to_url):
            try:
                data = future.result()
                apartement_data.append(data)
            except Exception as exc:
                print(f'Generated an exception: {exc}')
    
    return apartement_data

# Function to save the data in a csv file houses
def save_csv_house(classified_dict):
    df = pd.DataFrame(
        classified_dict
    )  # Convert the list of dictionaries into a DataFrame
    df.to_csv("data_immo_eliza_house.csv", index=False)
    print("Data saved as data_immo_eliza_house.csv")
    return "data_immo_eliza_house.csv"


def scraping_apartement_main():
    data_apartment = scraping_apartment()
    save_csv_apartement(data_apartment)


def scraping_house_main():
    data_house = scraping_house()
    save_csv_house(data_house)

# Function to concatonate the 2 csv files

def save_all_data_to_csv():
    df1 = pd.read_csv('data_immo_eliza_apartment.csv')
    df2 = pd.read_csv('data_immo_eliza_house.csv')
    df = pd.concat([df1, df2])
    df.to_csv('all_data_immo_eliza.csv', index=False)
    print("Data concatonated and saved as all_data_immo_eliza.csv")
    return 'all_data_immo_eliza.csv'


def main():
    scraping_apartement_main()
    scraping_house_main()
    save_all_data_to_csv()


main()




# Defining the DAG

default_args = {
    'owner': 'airflow',
    'depends_on_past': False
}

dag = DAG(
    'scraping_dag',
    default_args=default_args,
    description='A scraping DAG',
    schedule='0 18 * * *',
    start_date=datetime.now()
)

scraping_house_task = PythonOperator(
    task_id='scraping_house',
    python_callable=scraping_house_main,
    dag=dag
)

scraping_apartment_task = PythonOperator(
    task_id='scraping_apartment',
    python_callable=scraping_apartement_main,
    dag=dag
)

saving_data_task = PythonOperator(
    task_id='saving_data',
    python_callable=save_all_data_to_csv,
    dag=dag
)

