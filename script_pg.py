import sqlite3
import pandas as pd
import os

db_path = "test_multi_tables.db"
output_dir = "sqlite_tables_csv"
os.makedirs(output_dir, exist_ok=True)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()

for (table_name,) in tables:
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    df.to_csv(f"{output_dir}/{table_name}.csv", index=False)

conn.close()