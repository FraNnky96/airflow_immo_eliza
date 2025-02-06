import pandas as pd
from sklearn.model_selection import train_test_split, GridSearchCV
from catboost import CatBoostRegressor
from sklearn.metrics import mean_absolute_error
import joblib

def model():
    # Load the dataset
    df = pd.read_csv('datasets/cleaned_data.csv')
    
    # Identify categorical columns
    cat_cols = ['Type', 'Subtype', 'Kitchen', 'Type_of_sale', 'State_of_building']
    
    # Handle missing values: 
    for col in cat_cols:
        df[col] = df[col].astype(str).fillna('Unknown')  # Fill categorical NaN with 'Unknown'
    
    df.fillna(df.mean(numeric_only=True), inplace=True)  # Fill numeric NaN with column mean
    
    # Define the features and target variable
    X = df.drop(columns=['Price'])
    y = df['Price']
    
    # Split the data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Define the CatBoost model (passing categorical features correctly)
    model = CatBoostRegressor(random_state=42, verbose=100)
    
    # Define the model with the best parameters
    best_params = {'depth': 8, 'iterations': 300, 'learning_rate': 0.1}
    model = CatBoostRegressor(**best_params)

    # Fit the model
    model.fit(X_train, y_train, cat_features=cat_cols)

    # Make predictions
    y_pred = model.predict(X_test)

    # Evaluate the model
    mae = mean_absolute_error(y_test, y_pred)
    print(f'Mean Absolute Error: {mae}')

    # Save the model
    joblib.dump(model, 'model.pkl')
    print('Model saved as model.pkl')



