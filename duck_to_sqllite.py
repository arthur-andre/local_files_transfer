import duckdb
import sqlite3

def convert_duckdb_to_sqlite(duckdb_path, sqlite_path):
    con_duck = duckdb.connect(duckdb_path)
    con_sqlite = sqlite3.connect(sqlite_path)
    
    tables = con_duck.execute("SHOW TABLES").fetchall()
    for (table,) in tables:
        df = con_duck.execute(f"SELECT * FROM {table}").fetchdf()
        df.to_sql(table, con_sqlite, if_exists='replace', index=False)
    
    con_sqlite.close()
    con_duck.close()

# Exemple d'appel
convert_duckdb_to_sqlite("historique.db", "historique_sqlite.db")