import mysql.connector as m

conn = m.connect(
    host="your_db_host",
    user="your_db_user",
    password="your_db_password",
    database="asterisk"
)

print(conn.is_connected())
