import sqlite3
import psycopg2

sqlite_db_path = 'C:\\data_management_sys\\book_lx.db'

# SQLite连接和游标
sqlite_conn = sqlite3.connect(sqlite_db_path)
sqlite_cursor = sqlite_conn.cursor()

# PostgreSQL连接和游标
postgres_conn = psycopg2.connect(
    database='bookstore',
    user='postgres',
    password='',
    host='127.0.0.1',
    port='5432'
)
postgres_cursor = postgres_conn.cursor()

# 导出SQLite表结构
sqlite_cursor.execute("PRAGMA table_info(book)")
table_structure = sqlite_cursor.fetchall()
table_name = "book"

# 导出SQLite数据
sqlite_cursor.execute(f"SELECT * FROM {table_name}")
table_data = sqlite_cursor.fetchall()

# 插入数据到PostgreSQL
for row in table_data:
    placeholders = ', '.join(['%s' for _ in row])
    insert_sql = f"INSERT INTO book1 VALUES ({placeholders})"
    postgres_cursor.execute(insert_sql, row)

postgres_conn.commit()

# 关闭连接
sqlite_conn.close()
postgres_conn.close()