import mysql.connector
from mysql.connector import Error
from config import Config

def initialize_database():
    try:
        # Connect to MySQL database
        connection = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB
        )

        if connection.is_connected():
            print("Connected to MySQL database")

            # Read schema.sql file
            with open('schema.sql', 'r', encoding='utf-8') as file:
                schema = file.read()

            # Execute schema
            cursor = connection.cursor()
            for statement in schema.split(';'):
                if statement.strip():
                    cursor.execute(statement)

            connection.commit()
            print("Database initialized successfully.")

    except Error as e:
        print(f"Error: {e}")

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection closed.")

if __name__ == '__main__':
    initialize_database()