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
                    try:
                        cursor.execute(stmt)
                    except Error as err:
                        print(f"Warning executing statement: {err}")



            # 创建存储过程：借书
            cursor.execute("DROP PROCEDURE IF EXISTS borrow_book")
            create_proc_borrow = '''
            CREATE PROCEDURE borrow_book(IN p_user_id INT, IN p_book_id INT)
            BEGIN
                DECLARE rows_affected INT;
                DECLARE has_borrowed INT DEFAULT 0;

                SELECT COUNT(*) INTO has_borrowed FROM borrow_records WHERE user_id = p_user_id AND book_id = p_book_id;

                IF has_borrowed > 0 THEN
                    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '您已借阅过该书，不能重复借阅';
                ELSE
                    UPDATE books SET quantity = quantity - 1 WHERE id = p_book_id AND quantity > 0;
                    SELECT ROW_COUNT() INTO rows_affected;
                    
                    IF rows_affected > 0 THEN
                        INSERT INTO borrow_records (user_id, book_id) VALUES (p_user_id, p_book_id);
                    ELSE
                        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '图书库存不足，无法借阅';
                    END IF;
                END IF;
            END
            '''
            cursor.execute(create_proc_borrow)

            # 创建存储过程：还书
            cursor.execute("DROP PROCEDURE IF EXISTS return_book")
            create_proc_return = '''
            CREATE PROCEDURE return_book(IN p_user_id INT, IN p_book_id INT)
            BEGIN
                DECLARE borrow_id INT;
                SELECT id INTO borrow_id FROM borrow_records WHERE user_id = p_user_id AND book_id = p_book_id LIMIT 1;
                IF borrow_id IS NOT NULL THEN
                    UPDATE books SET quantity = quantity + 1 WHERE id = p_book_id;
                    DELETE FROM borrow_records WHERE id = borrow_id;
                END IF;
            END
            '''
            cursor.execute(create_proc_return)

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