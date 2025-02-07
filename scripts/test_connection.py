import psycopg2


def fetch_data():
    try:
        print("Attempting to connect...")
        # Establish the connection
        conn = psycopg2.connect(
            user="airflow",
            password="airflow",
            database="airflow",
            host="localhost",  # Connect to the host where PostgreSQL is exposed
            port=5432,
        )

        # Manually set client encoding after connection
        conn.set_client_encoding("UTF8")

        print("Connection established")

        # Create a cursor
        cursor = conn.cursor()

        # Execute the query
        cursor.execute("SELECT * FROM immo_data LIMIT 5")

        # Fetch the data
        result = cursor.fetchall()

        print("Fetched data:")
        try:
            for row in result:
                try:
                    print(row)
                except UnicodeDecodeError as e:
                    print(f"Unicode decode error with row: {row}")
                    print(f"Error: {e}")
        except Exception as e:
            print(f"Error: {e}")

        # Close the cursor and connection
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")


# Run the function
if __name__ == "__main__":
    fetch_data()
