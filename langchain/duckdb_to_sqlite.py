import duckdb
import sqlite3
import os

def convert_duckdb_to_sqlite(duckdb_path, sqlite_path):
    # Connexions
    duck_conn = duckdb.connect(duckdb_path)
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_cursor = sqlite_conn.cursor()

    # Récupérer les tables DuckDB
    tables = duck_conn.execute("SHOW TABLES").fetchall()
    tables = [t[0] for t in tables]

    for table in tables:
        print(f"Conversion de la table : {table}")

        # Lire la table DuckDB
        df = duck_conn.execute(f"SELECT * FROM {table}").fetchdf()

        # Créer la table dans SQLite
        df.to_sql(table, sqlite_conn, if_exists='replace', index=False)

    # Fermeture
    duck_conn.close()
    sqlite_conn.close()
    print(f"✅ Conversion terminée. Fichier SQLite : {sqlite_path}")

# Exemple d'utilisation
if __name__ == "__main__":
    duckdb_path = "historique.db"
    sqlite_path = "historique_sqlite.db"
    convert_duckdb_to_sqlite(duckdb_path, sqlite_path)
