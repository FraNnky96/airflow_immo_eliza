import pandas as pd


def drop_duplicate_data():
    df = pd.read_csv("datasets/all_data_immo_eliza.csv")
    no_duplicate_df = df.drop_duplicates()
    return no_duplicate_df


def clean_data():
    df = drop_duplicate_data()
    df = df.dropna(subset=["Price", "Area", "Bedrooms"])

    # Remove rows where 'Postalcode' contains any letters
    df = df[~df["Postcode"].str.contains("[A-Za-z]", na=False)]

    # Define a dictionary with column names as keys and tuples of fill values and data types as values
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

    # Loop through the dictionary and apply fillna and astype operations
    for column, (fill_value, dtype) in fill_values.items():
        if column in df.columns:
            df[column] = df[column].fillna(fill_value).astype(dtype)

    print(df.isna().sum())
    print(df.shape)
    # Save the cleaned DataFrame to a new CSV file
    df.to_csv("datasets/cleaned_data.csv", index=False)
