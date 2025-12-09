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

            cursor = connection.cursor()
            # 普通语句分割执行，跳过触发器
            statements = schema.split(';')
            for statement in statements:
                stmt = statement.strip()
                if stmt and not stmt.lower().startswith('create trigger') and not stmt.lower().startswith('drop trigger'):
                    cursor.execute(stmt)

            # 单独执行触发器
            # 触发器 1
            cursor.execute("DROP TRIGGER IF EXISTS prevent_book_deletion")
            create_trigger1 = '''
            CREATE TRIGGER prevent_book_deletion
            BEFORE DELETE ON books
            FOR EACH ROW
            BEGIN
                DECLARE active_borrows INT DEFAULT 0;
                SELECT COUNT(*) INTO active_borrows 
                FROM borrow_records 
                WHERE book_id = OLD.id;
                IF active_borrows > 0 THEN
                    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '该图书有未归还记录，无法删除';
                END IF;
            END
            '''
            cursor.execute(create_trigger1)

            # 触发器 2
            cursor.execute("DROP TRIGGER IF EXISTS prevent_user_deletion_with_active_borrows")
            create_trigger2 = '''
            CREATE TRIGGER prevent_user_deletion_with_active_borrows
            BEFORE DELETE ON users
            FOR EACH ROW
            BEGIN
                DECLARE active_borrow_count INT DEFAULT 0;
                SELECT COUNT(*) INTO active_borrow_count 
                FROM borrow_records 
                WHERE user_id = OLD.id;
                IF active_borrow_count > 0 THEN
                    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '用户有未归还的图书，请先处理借阅记录再删除';
                END IF;
            END
            '''
            cursor.execute(create_trigger2)

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