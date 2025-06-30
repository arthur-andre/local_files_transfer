import sqlite3

def explorer_sqlite(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Récupérer la liste des tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]

    print(f"📋 Tables trouvées dans la base '{db_path}' :\n")

    for table in tables:
        print(f"🔹 Table : {table}")
        cursor.execute(f"PRAGMA table_info({table});")
        colonnes = cursor.fetchall()
        if colonnes:
            for col in colonnes:
                cid, nom, type_col, notnull, default, pk = col
                pk_info = " (PK)" if pk else ""
                print(f"   - {nom} ({type_col}){' NOT NULL' if notnull else ''}{pk_info}")
        else:
            print("   ⚠️ Aucune colonne trouvée.")
        print()  # Ligne vide entre les tables

    conn.close()

# Exemple d'utilisation
if __name__ == "__main__":
    chemin_db = "ton_fichier.db"
    explorer_sqlite(chemin_db)
