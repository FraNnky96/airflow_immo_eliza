# Import libraries
import requests
from bs4 import BeautifulSoup
import re
import json
import concurrent.futures
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
import pandas as pd
import datetime
from catboost import CatBoostRegressor
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_absolute_error
import joblib
import os

# Defining functions

# Functions for scraping appartments


def fetch_links_from_page_apartment(counter):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    }
    url = f"https://www.immoweb.be/en/search/apartment/for-sale?countries=BE&page={counter}"
    print(url)
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.content, "html.parser")
    page_links = [
        elem["href"]
        for elem in soup.find_all("a", href=True)
        if "classified/apartment/" in elem["href"]
    ]
    return page_links


# Retreive links of all the appartments from a page
def retreive_apartment_links():
    appartements_url = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(fetch_links_from_page_apartment, counter)
            for counter in range(1, 2)
        ]  # CHANGE FOR THE NUMBER OF PAGES
        for future in concurrent.futures.as_completed(futures):
            try:
                page_links = future.result()
                appartements_url.extend(page_links)
            except Exception as exc:
                print(f"Generated an exception: {exc}")

    return appartements_url


# Function for scraping apartment info from links
def retreive_apartment_info(url):
    # Initialize data_dict as None to avoid reference errors
    data_dict = None

    # Fetch the page content using requests
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    req_info = requests.get(url, headers=headers)

    if req_info.status_code != 200:
        print(f"Error fetching {url}: {req_info.status_code}")
        return None

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

    # If data_dict is None or doesn't contain expected data, return early
    if not data_dict or "property" not in data_dict:
        print(f"Incomplete or missing data for {url}")
        return {}

    # Initialize classified_dict
    classified_dict = {}

    # Extract the relevant fields and handle missing data
    def get_nested_value(data, *keys):
        """Safe access to nested values in the dictionary."""
        for key in keys:
            if isinstance(data, dict):
                data = data.get(key, {})
            else:
                return None
        return data if data else None

    # Using get_nested_value for safe data extraction
    classified_dict["Postcode"] = get_nested_value(data_dict, "property", "location", "postalCode")
    classified_dict["Type"] = get_nested_value(data_dict, "property", "type")
    classified_dict["Subtype"] = get_nested_value(data_dict, "property", "subtype")
    classified_dict["Price"] = get_nested_value(data_dict, "price", "mainValue")
    classified_dict["Bedrooms"] = get_nested_value(data_dict, "property", "bedroomCount")
    classified_dict["Area"] = get_nested_value(data_dict, "property", "netHabitableSurface")
    classified_dict["Kitchen"] = get_nested_value(data_dict, "property", "kitchen", "type")
    classified_dict["Fireplace"] = get_nested_value(data_dict, "property", "fireplaceExists")
    classified_dict["Frontages"] = get_nested_value(data_dict, "property", "building", "facadeCount")
    classified_dict["Garden"] = get_nested_value(data_dict, "property", "hasGarden")
    classified_dict["Garden_surface"] = get_nested_value(data_dict, "property", "gardenSurface")
    classified_dict["Terrace"] = get_nested_value(data_dict, "property", "hasTerrace")
    classified_dict["Terrace_Surface"] = get_nested_value(data_dict, "property", "terraceSurface")
    classified_dict["Furnished"] = get_nested_value(data_dict, "transaction", "sale", "isFurnished")
    classified_dict["Type_of_sale"] = get_nested_value(data_dict, "transaction", "subtype")
    classified_dict["State_of_building"] = get_nested_value(data_dict, "property", "building", "condition")
    classified_dict["Swimmingpool"] = get_nested_value(data_dict, "property", "hasSwimmingPool")
    classified_dict["ID IMMOWEB"] = get_nested_value(data_dict, "id")
    classified_dict["Cadastral_income"] = get_nested_value(data_dict, "transaction", "sale", "cadastralIncome")
    classified_dict["Plot_surface"] = get_nested_value(data_dict, "property", "land", "surface")

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
                if data:  # Ensure None values are not added
                    apartement_data.append(data)
            except Exception as exc:
                print(f"Generated an exception: {exc}")

    return apartement_data


# Function to save the data in a csv file apartment
def save_csv_apartement(classified_dict):

    df = pd.DataFrame(classified_dict)


    df.to_csv(
        "/opt/airflow/datasets/data_immo_eliza_apartment.csv",
        mode='a',
        index=False,
        header=1
    )
    print("Data saved as data_immo_eliza_apartment.csv")
    return "data_immo_eliza_apartment.csv"


# Functions for retreiving links for houses
def fetch_links_from_page_house(counter):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    }
    url = f"https://www.immoweb.be/en/search/house/for-sale?countries=BE&page={counter}"
    print(url)
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.content, "html.parser")
    page_links = [
        elem["href"]
        for elem in soup.find_all("a", href=True)
        if "classified/house/" in elem["href"]
    ]
    return page_links


# Retreive links of all the houses from a page
def retreive_house_links():
    appartements_url = []
    with concurrent.futures.ThreadPoolExecutor() as executor:

        futures = [
            executor.submit(fetch_links_from_page_house, counter)
            for counter in range(1, 2)
        ]  # CHANGE FOR THE NUMBER OF PAGES
        for future in concurrent.futures.as_completed(futures):
            try:
                page_links = future.result()
                appartements_url.extend(page_links)
            except Exception as exc:
                print(f"Generated an exception: {exc}")

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

        future_to_url = {
            executor.submit(retreive_house_info, link): link for link in url
        }
        for future in concurrent.futures.as_completed(future_to_url):
            try:
                data = future.result()
                apartement_data.append(data)
            except Exception as exc:
                print(f"Generated an exception: {exc}")

    return apartement_data


# Function to save the data in a csv file houses
def save_csv_house(classified_dict):
    df = pd.DataFrame(
        classified_dict
    )  # Convert the list of dictionaries into a DataFrame
    df.to_csv("/opt/airflow/datasets/data_immo_eliza_house.csv",mode='a', index=False,header=1)
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
    df1 = pd.read_csv("/opt/airflow/datasets/data_immo_eliza_apartment.csv")
    df2 = pd.read_csv("/opt/airflow/datasets/data_immo_eliza_house.csv")
    df = pd.concat([df1, df2])
    df.to_csv("/opt/airflow/datasets/all_data_immo_eliza.csv",mode='a', index=False,header=1)
    print("Data concatonated and saved as all_data_immo_eliza.csv")
    return "all_data_immo_eliza.csv"


# Function to save data to PostgreSQL ( Not working yet)
"""def save_to_postgres():
    try:
        # Read the scraped data with UTF-8 encoding
        df = pd.read_csv("/opt/airflow/all_data_immo_eliza.csv", encoding="utf-8")

        # Connect to PostgreSQL
        hook = PostgresHook(postgres_conn_id="postgres_default")
        engine = hook.get_sqlalchemy_engine()

        # Save DataFrame to PostgreSQL
        df.to_sql("immo_data", engine, if_exists="append", index=False)
        print("Data successfully saved to PostgreSQL.")

    except Exception as e:
        print(f"Error occurred: {e}")"""



# Function to clean the data
def drop_duplicate_data():
    df = pd.read_csv("/opt/airflow/datasets/all_data_immo_eliza.csv")
    # Remove rows where 'Postcode' column has the value 'Postcode'
    df = df[df['Postcode'] != 'Postcode']
    no_duplicate_df = df.drop_duplicates()
    return no_duplicate_df


def clean_data():
    df = drop_duplicate_data()
    df = df.dropna(subset=["Price", "Area", "Bedrooms"])

    # Ensure 'Postcode' is a string and remove rows with letters in it
    df["Postcode"] = df["Postcode"].astype(str)
    df = df[~df["Postcode"].str.contains("[A-Za-z]", na=False)]

    # Define fill values and data types
    fill_values = {
        "Fireplace": (0, int),
        "Swimmingpool": (0, int),
        "Furnished": (0, int),
        "Terrace": (0, int),
        "Terrace_Surface": (0, float),
        "Garden": (0, int),
        "Garden_surface": (0, float),
        "Kitchen": ("NO_INFO", str),
        "Frontages": (0, float),
        "State_of_building": ("NO_INFO", str),
        "Plot_surface": (0, float),
        "Cadastral_income": (0, float),
    }

    # Loop through columns and clean the data
    for column, (fill_value, dtype) in fill_values.items():
        if column in df.columns:
            # Handle boolean-like values in integer fields
            if dtype == int:
                df[column] = df[column].replace({'True': 1, 'False': 0, True: 1, False: 0})
            
            df[column] = df[column].fillna(fill_value).astype(dtype)

    print(df.isna().sum())
    print(df.shape)

    # Save cleaned data to a new CSV file
    df = df[df['Postcode'] != 'Postcode']
    df.to_csv("/opt/airflow/datasets/cleaned_data.csv", mode='a', index=False)



# Function for model


def model():
    # Load the dataset
    df = pd.read_csv("/opt/airflow/datasets/cleaned_data.csv")
    df = df[df['Postcode'] != 'Postcode']

    # Identify categorical columns
    cat_cols = ["Type", "Subtype", "Kitchen", "Type_of_sale", "State_of_building"]

    # Handle missing values:
    for col in cat_cols:
        df[col] = (
            df[col].astype(str).fillna("Unknown")
        )  # Fill categorical NaN with 'Unknown'

    df.fillna(
        df.mean(numeric_only=True), inplace=True
    )  # Fill numeric NaN with column mean

    # Define the features and target variable
    X = df.drop(columns=["Price"])
    y = df["Price"]

    # Split the data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Define the CatBoost model (passing categorical features correctly)
    model = CatBoostRegressor(random_state=42, verbose=100)

    # Define the model with the best parameters
    best_params = {"depth": 8, "iterations": 300, "learning_rate": 0.1}
    model = CatBoostRegressor(**best_params)

    # Fit the model
    model.fit(X_train, y_train, cat_features=cat_cols)

    # Make predictions
    y_pred = model.predict(X_test)

    # Evaluate the model
    mae = mean_absolute_error(y_test, y_pred)
    print(f"Mean Absolute Error: {mae}")

    # Save the model
    joblib.dump(model, "model.pkl")
    print("Model saved as model.pkl")

    # Print the model prediction
    print(model.predict(X_test))


# Defining the DAG

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retry_delay": datetime.timedelta(minutes=5),
}

dag = DAG(
    "immo_eliza_pipeline_dag",
    default_args=default_args,
    description="Pipeline for scraping, saving, cleaning, and fitting a model for immo eliza data",
    schedule="0 23 * * * *",
    catchup=False,
    start_date=datetime.datetime(2024, 2, 4),
)

scraping_house_task = PythonOperator(
    task_id="scraping_house", python_callable=scraping_house_main, dag=dag
)

scraping_apartment_task = PythonOperator(
    task_id="scraping_apartment", python_callable=scraping_apartement_main, dag=dag
)

saving_data_task = PythonOperator(
    task_id="saving_data", python_callable=save_all_data_to_csv, dag=dag
)
# Not working
"""save_data_postgres_task = PythonOperator(
    task_id="saving_data_postgres",
    python_callable=save_to_postgres,
    dag=dag
)"""

clean_data_task = PythonOperator(
    task_id="clean_data", python_callable=clean_data, dag=dag
)

model_task = PythonOperator(task_id="model", python_callable=model, dag=dag)

# Setting the order of the tasks

(
    scraping_house_task
    >> scraping_apartment_task
    >> saving_data_task
    >> clean_data_task
    >> model_task
)
