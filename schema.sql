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

CREATE INDEX idx_borrow_records_user_id ON borrow_records(user_id);
CREATE INDEX idx_borrow_records_book_id ON borrow_records(book_id);
CREATE INDEX idx_borrow_records_user_book ON borrow_records(user_id, book_id);
CREATE INDEX idx_books_title ON books(title);
CREATE INDEX idx_books_quantity ON books(quantity);
CREATE INDEX idx_borrow_user_time ON borrow_records(user_id, id);
CREATE INDEX idx_borrow_book_time ON borrow_records(book_id, id);

CREATE OR REPLACE VIEW borrow_record_view AS
SELECT
    br.id AS borrow_id,
    u.username AS user_name,
    b.title AS book_title,
    b.image_filename,
    br.user_id,
    br.book_id
FROM borrow_records br
JOIN users u ON br.user_id = u.id
JOIN books b ON br.book_id = b.id;

CREATE OR REPLACE VIEW user_borrowed_books_view AS
SELECT
    u.id AS user_id,
    u.username,
    b.id AS book_id,
    b.title,
    b.image_filename
FROM users u
JOIN borrow_records br ON u.id = br.user_id
JOIN books b ON br.book_id = b.id;

CREATE OR REPLACE VIEW available_books_per_user_view AS
SELECT
    u.id AS user_id,
    b.id AS book_id,
    b.title,
    b.image_filename,
    b.quantity
FROM users u
CROSS JOIN books b
WHERE b.quantity > 0
  AND NOT EXISTS (
      SELECT 1 FROM borrow_records br
      WHERE br.book_id = b.id AND br.user_id = u.id
  );

-- 插入用户的占位语句
INSERT INTO users (username, password_hash) VALUES
    ('user', 'e606e38b0d8c19b24cf0ee3808183162ea7cd63ff7912dbb22b5e803286b4446');
-- user user123

-- 插入管理员的占位语句
INSERT INTO admins (username, password_hash) VALUES
    ('admin', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9');
-- admin admin123