import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

with open("schema.sql", "r") as f:
    sql = f.read()

cur.execute(sql)

print("Schema created successfully")

cur.close()
conn.close()