from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import re
from typing import Dict, List
import uvicorn

from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

# === CONFIG ===
DB_DIR = "./db_duck"  # <- nouveau dossier
API_BASE = "http://localhost:8010/v1"
MODEL = "/workspace/models/mistral-7b-instruct"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def charger_base_duckdb(nom_fichier: str) -> SQLDatabase:
    chemin = os.path.join(DB_DIR, nom_fichier)
    if not os.path.isfile(chemin):
        raise FileNotFoundError(f"Base non trouvée : {chemin}")
    return SQLDatabase.from_uri(f"duckdb:///{chemin}")

def extraire_sql_depuis_texte(texte: str) -> str:
    match = re.search(r"```sql\n(.*?)\n```", texte, re.DOTALL)
    return match.group(1).strip() if match else None

def get_sql_results_two_formats(db, sql):
    try:
        list_of_dicts = db._execute(sql)
        if not list_of_dicts:
            return [], {"columns": [], "values": []}
        columns = list(list_of_dicts[0].keys())
        values = [list(d.values()) for d in list_of_dicts]
        return list_of_dicts, {"columns": columns, "values": values}
    except Exception as e:
        error_msg = f"[ERREUR SQL] {e}"
        return [{"Erreur": error_msg}], {
            "columns": ["Erreur"],
            "values": [[error_msg]]
        }

def get_ddl_schema(db: SQLDatabase) -> str:
    tables = db.get_usable_table_names()
    ddl_list = []
    for table in tables:
        try:
            res = db._execute(
                f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'"
            )
            if res and res[0].get("sql"):
                ddl_list.append(res[0]["sql"])
        except Exception as e:
            print(f"[ERREUR DDL] pour {table} : {e}")
    return "\n\n".join(ddl_list)

def reponse_finale(llm: ChatOpenAI, question: str, requete_sql: str, columns_values: dict):
    if columns_values["columns"] == ["Erreur"]:
        prompt = f"""
    Tu es un assistant SQL.

    QUESTION POSÉE :
    {question}

    ERREUR DANS LA REQUÊTE SQL :
    {columns_values["values"][0][0]}

    Explique clairement l'erreur et propose une piste de correction éventuelle en français.
    """
    else:
        prompt = f"""
        Tu es un assistant expert en base de données.

        QUESTION POSÉE :
        {question}

        REQUÊTE SQL GÉNÉRÉE :
        {requete_sql}

        RÉSULTATS DE LA REQUÊTE :
        Colonnes : {columns_values["columns"]}
        Lignes :
        {columns_values["values"]}

        En te basant uniquement sur les résultats de la requête SQL, réponds à la question en français de manière claire, concise et précise.
        """
    return llm.invoke(prompt)

class QuestionPayload(BaseModel):
    question: str
    database: str

@app.get("/list_databases")
def list_databases():
    if not os.path.exists(DB_DIR):
        raise HTTPException(status_code=404, detail="Dossier db_duck non trouvé.")
    return [f for f in os.listdir(DB_DIR) if f.endswith(".db") or f.endswith(".duckdb")]

@app.post("/pose_question")
def pose_question(payload: QuestionPayload):
    try:
        db = charger_base_duckdb(payload.database)
        llm = ChatOpenAI(
            temperature=0,
            model=MODEL,
            openai_api_base=API_BASE,
            openai_api_key="fake"
        )
        ddl_schema = get_ddl_schema(db)
        prompt = PromptTemplate(
            input_variables=["schema", "question"],
            template="""
Tu es un assistant SQL. Voici la définition DDL (CREATE TABLE) de la base :

{schema}

En te basant uniquement sur cette définition, écris une requête SQL pour répondre à la question suivante :

{question}

Retourne uniquement la requête SQL entre balises ```sql ... ```
"""
        )
        chaine_sql = LLMChain(llm=llm, prompt=prompt)
        texte = chaine_sql.run(schema=ddl_schema, question=payload.question)
        requete_sql = extraire_sql_depuis_texte(texte)

        if not requete_sql:
            raise RuntimeError("❌ Impossible d'extraire la requête SQL.")

        list_of_dicts, columns_values = get_sql_results_two_formats(db, requete_sql)
        reponse = reponse_finale(llm, payload.question, requete_sql, columns_values)

        return {
            "requete_sql": requete_sql,
            "reponse_finale": reponse,
            "list_of_dicts": list_of_dicts,
            "columns_values": columns_values
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/schema/{database_name}")
def get_schema(database_name: str):
    db = charger_base_duckdb(database_name)
    print(f"Chargement de la base : {database_name}")
    if not db:
        raise HTTPException(status_code=404, detail="Base de données non trouvée.")
    print("Base chargée avec succès.")

    try:
        tables = db.get_usable_table_names()
        schema = {}
        for table in tables:
            columns_info = db._execute(f"PRAGMA table_info({table})")
            schema[table] = [col["name"] for col in columns_info]
        return schema
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'extraction du schéma : {e}")


if __name__ == "__main__":
    uvicorn.run("main_duck:app", host="0.0.0.0", port=8020, reload=False)
