import sqlite3

# 创建与数据库的连接
conn = sqlite3.connect(r"C:\Users\Iceze\Database\test.db")

# 创建一个游标 cursor
cur = conn.cursor()

# 插入单条数据
sql_text_2 = "INSERT INTO DEPARTMENT VALUES(1, 'jkjkjk', 32);"
cur.execute(sql_text_2)

conn.commit()

conn.close()
