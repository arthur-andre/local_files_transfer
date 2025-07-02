from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import re

from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from typing import Dict, List
import uvicorn


# === CONFIG ===
DB_DIR = "./db"
API_BASE = "http://localhost:8010/v1"
MODEL = "/workspace/models/mistral-7b-instruct"

# === INIT APP ===
app = FastAPI()

# === CORS pour développement ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # à restreindre en prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === UTILS ===
def charger_base_sqlite(nom_fichier: str) -> SQLDatabase:
    chemin = os.path.join(DB_DIR, nom_fichier)
    if not os.path.isfile(chemin):
        raise FileNotFoundError(f"Base non trouvée : {chemin}")
    return SQLDatabase.from_uri(f"sqlite:///{chemin}")

def get_columns_for_table(db: SQLDatabase, table_name: str):
    rows = db._execute(f"PRAGMA table_info({table_name})")  # rows = list of tuples
    return [row['name'] for row in rows]

def extraire_sql_depuis_texte(texte: str) -> str:
    match = re.search(r"```sql\n(.*?)\n```", texte, re.DOTALL)
    return match.group(1).strip() if match else None

def reponse_finale(llm: ChatOpenAI, question: str, requete_sql: str, resultat_sql: str):
    prompt = f"""
Tu es un assistant expert en base de données.

QUESTION POSÉE :
{question}

REQUÊTE SQL GÉNÉRÉE :
{requete_sql}

RÉSULTAT OBTENU :
{resultat_sql}

formule une réponse synthétique et claire à la question en t'appuyant sur les données retournées. Formule la réponse absolument en français.
"""
    return llm.invoke(prompt)

def get_sql_results_two_formats(db, sql):
    result_proxy = db._execute(sql)
    columns = result_proxy.keys()
    rows = result_proxy.fetchall()

    # Format 1 : liste de dictionnaires (colonne: valeur)
    list_of_dicts = [dict(zip(columns, row)) for row in rows]

    # Format 2 : dict colonnes + valeurs en listes
    columns_values = {
        "columns": list(columns),
        "values": [list(row) for row in rows]
    }

    return list_of_dicts, columns_values


# === MODELE REQUETE ===
class QuestionPayload(BaseModel):
    question: str
    database: str

# === ENDPOINT 1 : Liste des bases ===
@app.get("/list_databases")
def list_databases():
    if not os.path.exists(DB_DIR):
        raise HTTPException(status_code=404, detail="Dossier db non trouvé.")
    fichiers = [
        f for f in os.listdir(DB_DIR)
        if f.endswith(".db") and os.path.isfile(os.path.join(DB_DIR, f))
    ]
    return fichiers

# === ENDPOINT 2 : Pose ta question ===
@app.post("/pose_question")
def pose_question(payload: QuestionPayload):
    try:
        # Charger DB + LLM
        db = charger_base_sqlite(payload.database)
        llm = ChatOpenAI(
            temperature=0,
            model=MODEL,
            openai_api_base=API_BASE,
            openai_api_key="fake"
        )

        schema = db.get_table_info()
        prompt = PromptTemplate(
            input_variables=["schema", "question"],
            template="""
Tu es un assistant SQL. Voici la structure de la base :

{schema}

En te basant uniquement sur cette structure, écris une requête SQL pour répondre à la question suivante :

{question}

Retourne uniquement la requête SQL entre balises ```sql ... ```
"""
        )
        chaine_sql = LLMChain(llm=llm, prompt=prompt)
        texte = chaine_sql.run(schema=schema, question=payload.question)
        requete_sql = extraire_sql_depuis_texte(texte)

        if not requete_sql:
            raise RuntimeError("❌ Impossible d'extraire la requête SQL depuis la réponse du LLM.")

        try:
            print("==== REQUÊTE SQL GÉNÉRÉE ====")
            print(requete_sql)
            resultat_sql = db.run(requete_sql)
        except Exception as e:
            resultat_sql = f"[ERREUR SQL] {e}"

        list_of_dicts, columns_values = get_sql_results_two_formats(db, requete_sql)
        print("==== RÉSULTAT SQL ====")
        reponse = reponse_finale(llm, payload.question, requete_sql, resultat_sql)
        print("==== RÉPONSE FINALE ====")
        print(reponse.content)
        return {
            "requete_sql": requete_sql,
            "reponse_finale": reponse,
            "resultat_sql_complet": resultat_sql,
            "list_of_dicts": list_of_dicts,
            "columns_values": columns_values
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/schema/{database_name}")
def get_schema(database_name: str):
    db = charger_base_sqlite(database_name)
    tables = db.get_usable_table_names()  # ou get_table_names() selon ta classe
    schema = {}
    for table in tables:
        schema[table] = get_columns_for_table(db, table)
    return schema

# === LANCEMENT SERVEUR ===
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8020, reload=False)