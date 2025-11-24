-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL
);

-- 创建管理员表
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL
);

-- 创建图书表
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(255) NOT NULL,
    image_filename VARCHAR(255),
    quantity INTEGER NOT NULL DEFAULT 0
);

-- 创建借阅记录表
CREATE TABLE IF NOT EXISTS borrow_records (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    user_id INTEGER NOT NULL,
    book_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);

-- 插入用户的占位语句
INSERT INTO users (username, password_hash) VALUES
    ('user', 'e606e38b0d8c19b24cf0ee3808183162ea7cd63ff7912dbb22b5e803286b4446');
-- user user123

-- 插入管理员的占位语句
INSERT INTO admins (username, password_hash) VALUES
    ('admin', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9');
-- admin admin123

-- 插入图书的占位语句
INSERT INTO books (title, image_filename, quantity) VALUES
    ('123', '123.jpg', 10);