import argparse
import re
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from rich.console import Console

console = Console()

def charger_base_sqlite(db_path: str) -> SQLDatabase:
    return SQLDatabase.from_uri(f"sqlite:///{db_path}")

def charger_llm(api_base: str, model_name: str = "mistral") -> ChatOpenAI:
    return ChatOpenAI(
        temperature=0,
        model=model_name,
        openai_api_base=api_base,
        openai_api_key="fake"
    )

def extraire_sql_depuis_texte(texte: str) -> str:
    match = re.search(r"```sql\n(.*?)\n```", texte, re.DOTALL)
    return match.group(1).strip() if match else None

def afficher_reponse_llm_brute(llm_response):
    content = llm_response.content.strip().replace('\n\n', '\n') if hasattr(llm_response, "content") else llm_response
    console.print("\n[bold cyan]📊 Réponse de l'assistant :[/bold cyan]\n")
    console.print(content, style="white")

def reponse_finale(llm: ChatOpenAI, question: str, requete_sql: str, resultat_sql: str):
    prompt = f"""
Tu es un assistant expert en base de données.

QUESTION POSÉE :
{question}

REQUÊTE SQL GÉNÉRÉE :
{requete_sql}

RÉSULTAT OBTENU :
{resultat_sql}

Formule une réponse synthétique et claire à la question en t'appuyant sur les données retournées.
"""
    return llm.invoke(prompt)

def main():
    parser = argparse.ArgumentParser(description="Pose une question SQL à une base via LLM.")
    parser.add_argument("--db", required=True, help="Chemin absolu vers la base SQLite (.db)")
    parser.add_argument("--question", required=True, help="Question à poser à l'assistant SQL")

    args = parser.parse_args()
    chemin_db = args.db
    question = args.question

    api_base = "http://localhost:8010/v1"
    modele = "/workspace/models/mistral-7b-instruct"

    db = charger_base_sqlite(chemin_db)
    llm = charger_llm(api_base=api_base, model_name=modele)

    # Génération SQL via LLMChain avec prompt explicite
    schema = db.get_table_info()
    prompt = PromptTemplate(
        input_variables=["schema", "question"],
        template="""
Tu es un assistant SQL. Voici la structure de la base :

{schema}

En te basant uniquement sur cette structure, écris une requête SQL pour répondre à la question suivante :

{question}

Retourne uniquement la requête SQL entre balises ```sql ... ```

Toutes les comparaisons de chaînes (dans les clauses WHERE) doivent être insensibles à la casse.
Utilise UPPER(colonne) = UPPER('valeur')
"""
    )
    chaine_sql = LLMChain(llm=llm, prompt=prompt)
    texte = chaine_sql.run(schema=schema, question=question)
    requete_sql = extraire_sql_depuis_texte(texte)

    if not requete_sql:
        raise RuntimeError("❌ Impossible d'extraire la requête SQL depuis la réponse du LLM.")

    try:
        print("==== REQUÊTE SQL GÉNÉRÉE ====")
        print(requete_sql)
        resultat_sql = db.run(requete_sql)
    except Exception as e:
        resultat_sql = f"[ERREUR SQL] {e}"

    reponse = reponse_finale(llm, question, requete_sql, resultat_sql)
    afficher_reponse_llm_brute(reponse)

if __name__ == "__main__":
    main()
