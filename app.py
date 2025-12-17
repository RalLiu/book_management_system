from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from hash_util import generate_hash
import mysql.connector
from config import Config
import os
import subprocess
from datetime import datetime

app = Flask(__name__)

# 获取 config.py 中的参数
app.config.from_object(Config)

app.secret_key = Config.SECRET_KEY

def backup_database():
    """备份数据库到 backup 文件夹"""
    try:
        # 确保备份目录存在
        backup_dir = os.path.join(app.root_path, 'backup')
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        # 生成备份文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"backup_{timestamp}.sql"
        filepath = os.path.join(backup_dir, filename)

        # 获取数据库配置
        host = app.config['MYSQL_HOST']
        user = app.config['MYSQL_USER']
        password = app.config['MYSQL_PASSWORD']
        db_name = app.config['MYSQL_DB']

        # 构建 mysqldump 命令
        # 注意：mysqldump 需要在系统环境变量中，或者指定完整路径
        command = [
            'mysqldump',
            f'-h{host}',
            f'-u{user}',
            f'-p{password}',
            '--routines', # 导出存储过程和函数
            '--events',   # 导出定时事件
            db_name
        ]

        # 执行备份
        with open(filepath, 'w') as f:
            subprocess.run(command, stdout=f, check=True)
        
        print(f"Database backup successful: {filepath}")
    except Exception as e:
        print(f"Database backup failed: {str(e)}")

def restore_database(filename):
    """从 backup 文件夹中的 sql 文件还原数据库"""
    try:
        backup_dir = os.path.join(app.root_path, 'backup')
        filepath = os.path.join(backup_dir, filename)
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Backup file not found: {filename}")

        # 获取数据库配置
        host = app.config['MYSQL_HOST']
        user = app.config['MYSQL_USER']
        password = app.config['MYSQL_PASSWORD']
        db_name = app.config['MYSQL_DB']

        # 构建 mysql 还原命令
        # 注意：mysql 客户端需要在系统环境变量中
        command = [
            'mysql',
            f'-h{host}',
            f'-u{user}',
            f'-p{password}',
            db_name
        ]

        # 执行还原
        with open(filepath, 'r') as f:
            subprocess.run(command, stdin=f, check=True)
            
        print(f"Database restore successful: {filepath}")
        return True, "数据库还原成功"
    except Exception as e:
        print(f"Database restore failed: {str(e)}")
        return False, str(e)

def get_db_connection():
    return mysql.connector.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )

@app.before_request
def check_login():
    # 如果访问首页且已登录，自动跳转到对应主页
    if request.endpoint == 'home':
        if 'user_logged_in' in session:
            return redirect(url_for('user_dashboard'))
        elif 'admin_logged_in' in session:
            return redirect(url_for('admin_dashboard'))
    # 其他页面权限校验
    if request.endpoint not in ['home', 'user_login', 'admin_login', 'static']:
        if 'user_logged_in' not in session and 'admin_logged_in' not in session:
            return redirect(url_for('home'))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/user_login', methods=['POST'])
def user_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    hashed_password = generate_hash(password)

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # 检查用户是否存在
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()

    if user:
        # 检查密码
        if user['password_hash'] == hashed_password:
            session['user_logged_in'] = True
            session['username'] = username
            session['user_id'] = user['id']
            cursor.close()
            connection.close()
            return jsonify({"success": True, "redirect": url_for('user_dashboard')}), 200
        else:
            cursor.close()
            connection.close()
            return jsonify({"success": False, "message": "密码错误"}), 401
    else:
        # 若不存在 创建新用户
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
            (username, hashed_password)
        )
        connection.commit()

        # 再次查询以获取新用户的ID
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        new_user = cursor.fetchone()

        session['user_logged_in'] = True
        session['username'] = username
        session['user_id'] = new_user['id']

        cursor.close()
        connection.close()
        
        # 触发备份
        backup_database()
        
        return jsonify({"success": True, "redirect": url_for('user_dashboard')}), 201

@app.route('/api/admin_login', methods=['POST'])
def admin_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    hashed_password = generate_hash(password)

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM admins WHERE username = %s AND password_hash = %s", (username, hashed_password))
    admin = cursor.fetchone()

    cursor.close()
    connection.close()

    backup_database()

    if admin:
        session['admin_logged_in'] = True
        return jsonify({"success": True, "redirect": url_for('admin_dashboard')}), 200
    else:
        return jsonify({"success": False, "message": "用户名或密码错误"}), 401

@app.route('/user')
def user_dashboard():
    if 'user_logged_in' not in session:
        return redirect(url_for('home'))
    username = session.get('username', '用户')
    return render_template('user.html', username=username)

@app.route('/admin')
def admin_dashboard():
    if 'admin_logged_in' not in session:
        return redirect(url_for('home'))
    
    # 获取备份文件列表
    backup_dir = os.path.join(app.root_path, 'backup')
    backup_files = []
    if os.path.exists(backup_dir):
        files = os.listdir(backup_dir)
        # 过滤出 .sql 文件并按修改时间倒序排列
        sql_files = [f for f in files if f.endswith('.sql')]
        sql_files.sort(key=lambda x: os.path.getmtime(os.path.join(backup_dir, x)), reverse=True)
        backup_files = sql_files
        
    return render_template('admin.html', backup_files=backup_files)

@app.route('/admin/restore', methods=['POST'])
def admin_restore():
    if 'admin_logged_in' not in session:
        return jsonify({"success": False, "message": "未登录管理员账号"}), 401
        
    filename = request.json.get('filename')
    if not filename:
        return jsonify({"success": False, "message": "未选择备份文件"}), 400
        
    success, message = restore_database(filename)
    
    if success:
        return jsonify({"success": True, "message": message}), 200
    else:
        return jsonify({"success": False, "message": f"还原失败: {message}"}), 500

@app.route('/user/borrow_books')
def borrow_books():
    if 'user_logged_in' not in session:
        return redirect(url_for('home'))

    user_id = session.get('user_id')

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT * FROM available_books_per_user_view WHERE user_id = %s
    """
    cursor.execute(query, (user_id,))
    books = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('borrow_books.html', books=books)

@app.route('/user/my_books')
def my_books():
    if 'user_logged_in' not in session:
        return redirect(url_for('home'))

    user_id = session.get('user_id')

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = """
        SELECT * FROM user_borrowed_books_view WHERE user_id = %s
    """
    cursor.execute(query, (user_id,))
    books = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('my_books.html', books=books)

@app.route('/user/borrow', methods=['POST'])
def borrow_book():
    if 'user_logged_in' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401

    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': '用户未登录'}), 401

    book_id = request.form.get('book_id')

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # 调用存储过程实现借书原子操作
        cursor.execute("CALL borrow_book(%s, %s)", (user_id, book_id))
        connection.commit()
        
        # 触发备份
        backup_database()
        
        return jsonify({'success': True, 'message': '借书成功'})
    except mysql.connector.Error as err:
        return jsonify({'success': False, 'message': str(err)})
    finally:
        cursor.close()
        connection.close()

@app.route('/user/return', methods=['POST'])
def return_book():
    if 'user_logged_in' not in session:
        return redirect(url_for('home'))

    user_id = session.get('user_id')
    book_id = request.form.get('book_id')

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # 直接调用还书存储过程
    cursor.execute("CALL return_book(%s, %s)", (user_id, book_id))
    connection.commit()

    cursor.close()
    connection.close()

    # 触发备份
    backup_database()

    return redirect(url_for('my_books'))

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/admin/manage_users')
def manage_users():
    if 'admin_logged_in' not in session:
        return redirect(url_for('home'))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT id, username FROM users")
    users = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('manage_users.html', users=users)

@app.route('/admin/add_user', methods=['POST'])
def add_user():
    if 'admin_logged_in' not in session:
        return redirect(url_for('home'))

    username = request.form.get('username')
    password = request.form.get('password')

    hashed_password = generate_hash(password)

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
        (username, hashed_password)
    )
    connection.commit()

    cursor.close()
    connection.close()

    # 触发备份
    backup_database()

    return redirect(url_for('manage_users'))

@app.route('/admin/edit_user', methods=['POST'])
def edit_user():
    if 'admin_logged_in' not in session:
        return redirect(url_for('home'))

    user_id = request.form.get('user_id')
    username = request.form.get('username')
    password = request.form.get('password')

    connection = get_db_connection()
    cursor = connection.cursor()

    if password:
        hashed_password = generate_hash(password)
        cursor.execute(
            "UPDATE users SET username = %s, password_hash = %s WHERE id = %s",
            (username, hashed_password, user_id)
        )
    else:
        cursor.execute(
            "UPDATE users SET username = %s WHERE id = %s",
            (username, user_id)
        )

    connection.commit()

    cursor.close()
    connection.close()

    # 触发备份
    backup_database()

    return redirect(url_for('manage_users'))

@app.route('/admin/delete_user', methods=['POST'])
def delete_user():
    if 'admin_logged_in' not in session:
        return redirect(url_for('home'))

    user_id = request.form.get('user_id')

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    connection.commit()

    cursor.close()
    connection.close()

    # 触发备份
    backup_database()

    return redirect(url_for('manage_users'))

@app.route('/admin/add_book', methods=['POST'])
def add_book():
    if 'admin_logged_in' not in session:
        return redirect(url_for('home'))

    title = request.form.get('title')
    quantity = request.form.get('quantity')
    image = request.files.get('image')

    if image:
        # 保存图片到 static 文件夹，使用原始文件名
        image_filename = image.filename
        image.save(os.path.join('static', image_filename))
    else:
        image_filename = None

    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        "INSERT INTO books (title, quantity, image_filename) VALUES (%s, %s, %s)",
        (title, quantity, image_filename)
    )
    connection.commit()

    cursor.close()
    connection.close()

    # 触发备份
    backup_database()

    return redirect(url_for('manage_books'))

@app.route('/admin/manage_books')
def manage_books():
    if 'admin_logged_in' not in session:
        return redirect(url_for('home'))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT id, title, quantity, image_filename FROM books")
    books = cursor.fetchall()

    cursor.close()
    connection.close()

    for book in books:
        if book['image_filename']:
            book['image_url'] = url_for('static', filename=book['image_filename'])
        else:
            book['image_url'] = None

    return render_template('manage_books.html', books=books)

@app.route('/admin/manage_borrow_records')
def manage_borrow_records():
    if 'admin_logged_in' not in session:
        return redirect(url_for('home'))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    #查询所有借阅记录
    query = """
        SELECT * FROM borrow_record_view
    """
    cursor.execute(query)
    borrow_records = cursor.fetchall()

    #查询所有用户用于选择
    cursor.execute("SELECT id, username FROM users")
    users = cursor.fetchall()

    #查询所有书籍用于选择
    cursor.execute("SELECT id, title FROM books")
    books = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('manage_borrow_records.html', borrow_records=borrow_records, users=users, books=books)

@app.route('/admin/add_borrow_record', methods=['POST'])
def add_borrow_record():
    if 'admin_logged_in' not in session:
        return redirect(url_for('home'))

    user_id = request.form.get('user_id')
    book_id = request.form.get('book_id')

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # 检查借阅记录是否已存在
    cursor.execute(
        "SELECT COUNT(*) AS count FROM borrow_records WHERE user_id = %s AND book_id = %s",
        (user_id, book_id)
    )
    record_exists = cursor.fetchone()['count'] > 0

    # 查询书籍库存是否大于0
    cursor.execute(
        "SELECT quantity FROM books WHERE id = %s",
        (book_id,)
    )
    book = cursor.fetchone()
    if book:
        book_quantity = book['quantity']
    else:
        book_quantity = 0

    if record_exists:
        cursor.close()
        connection.close()
        return jsonify({"success": False, "message": "该借阅记录已存在！"}), 400

    if book_quantity <= 0:
        cursor.close()
        connection.close()
        return jsonify({"success": False, "message": "书籍库存不足，无法添加借阅记录！"}), 400

    cursor.execute("CALL borrow_book(%s, %s)", (user_id, book_id))

    connection.commit()

    cursor.close()
    connection.close()

    # 触发备份
    backup_database()

    return jsonify({"success": True, "message": "借阅记录添加成功！"}), 200

@app.route('/admin/delete_borrow_record', methods=['POST'])
def delete_borrow_record():
    if 'admin_logged_in' not in session:
        return redirect(url_for('home'))

    borrow_record_id = request.form.get('borrow_record_id')

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # 获取book_id和user_id
    cursor.execute(
        "SELECT book_id, user_id FROM borrow_records WHERE id = %s",
        (borrow_record_id,)
    )
    record = cursor.fetchone()
    if not record:
        cursor.close()
        connection.close()
        return redirect(url_for('manage_borrow_records'))
    book_id = record['book_id']
    user_id = record['user_id']

    # 调用还书存储过程（原子操作：还书+删除记录+加库存）
    cursor.execute("CALL return_book(%s, %s)", (user_id, book_id))
    connection.commit()

    cursor.close()
    connection.close()

    # 触发备份
    backup_database()

    return redirect(url_for('manage_borrow_records'))

@app.route('/api/delete_user', methods=['DELETE'])
def api_delete_user():
    if 'admin_logged_in' not in session:
        return jsonify({"success": False, "message": "未登录管理员账号"}), 401

    user_id = request.json.get('user_id')

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        connection.commit()
        
        # 触发备份
        backup_database()
        
        return jsonify({"success": True, "message": "用户删除成功"}), 200
    except mysql.connector.errors.DatabaseError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    finally:
        cursor.close()
        connection.close()

@app.route('/api/delete_book', methods=['DELETE'])
def api_delete_book():
    if 'admin_logged_in' not in session:
        return jsonify({"success": False, "message": "未登录管理员账号"}), 401

    book_id = request.json.get('book_id')

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("DELETE FROM books WHERE id = %s", (book_id,))
        connection.commit()
        
        # 触发备份
        backup_database()
        
        return jsonify({"success": True, "message": "图书删除成功"}), 200
    except mysql.connector.errors.DatabaseError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    finally:
        cursor.close()
        connection.close()

@app.route('/api/edit_book', methods=['POST'])
def api_edit_book():
    if 'admin_logged_in' not in session:
        return jsonify({"success": False, "message": "未登录管理员账号"}), 401

    book_id = request.form.get('book_id')
    title = request.form.get('title')
    quantity = request.form.get('quantity')
    image = request.files.get('image')

    if not all([book_id, title, quantity]):
        return jsonify({"success": False, "message": "缺少必要的字段"}), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # 更新书籍信息
        cursor.execute(
            """
            UPDATE books
            SET title = %s, quantity = %s
            WHERE id = %s
            """,
            (title, quantity, book_id)
        )

        # 更新图片（如果提供）
        if image:
            image_filename = image.filename
            image.save(os.path.join('static', image_filename))
            cursor.execute(
                """
                UPDATE books
                SET image_filename = %s
                WHERE id = %s
                """,
                (image_filename, book_id)
            )

        connection.commit()
        
        # 触发备份
        backup_database()
        
    except Exception as e:
        connection.rollback()
        return jsonify({"success": False, "message": f"更新失败: {str(e)}"}), 500
    finally:
        cursor.close()
        connection.close()

    return jsonify({"success": True, "message": "图书信息更新成功"}), 200

@app.route('/admin/filter_book', methods = ['POST'])
def admin_filter_book():
    if 'admin_logged_in' not in session:
        return jsonify({"success": False, "message": "未登录管理员账号"}), 401
    title = request.form.get('title', '')
    quantity = request.form.get('quantity', 0)
    try:
        quantity = int(quantity)
    except(ValueError, TypeError):
        quantity = 0

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    sql_query = """
        select * from books where title like %s and quantity >= %s
    """

    like_pattern = f"%{title}%"
    cursor.execute(sql_query, (like_pattern, quantity))
    books = cursor.fetchall()

    cursor.close()
    connection.close()

    for book in books:
        if book.get('image_filename'):
            book['image_url'] = url_for('static', filename=book['image_filename'])
        else:
            book['image_url'] = None

    return jsonify({"success": True, "books": books})

if __name__ == '__main__':
    app.run(debug=True)