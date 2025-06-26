from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.agent_toolkits.sql.base import create_sql_agent

import re


def charger_base_sqlite(db_path: str) -> SQLDatabase:
    return SQLDatabase.from_uri(f"sqlite:///{db_path}")


def charger_llm(api_base: str, model_name: str = "mistral") -> ChatOpenAI:
    return ChatOpenAI(
        temperature=0,
        model=model_name,
        openai_api_base=api_base,
        openai_api_key="fake"
    )


def construire_agent(db: SQLDatabase, llm: ChatOpenAI, verbose: bool = True):
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    return create_sql_agent(llm=llm, toolkit=toolkit, verbose=verbose, handle_parsing_errors=True)


def extraire_sql_depuis_texte(texte: str) -> str:
    match = re.search(r"```sql\n(.*?)\n```", texte, re.DOTALL)
    return match.group(1).strip() if match else None


def afficher_reponse_llm_brute(llm_response):
    from rich.console import Console
    console = Console()

    content = llm_response.content.strip()

    # Nettoyage minimal (ex : double sauts de ligne → saut simple)
    content = content.replace('\n\n', '\n')

    console.print("\n[bold cyan]📊 Réponse de l'assistant :[/bold cyan]\n")
    console.print(content, style="white")

def reponse_finale(llm: ChatOpenAI, question: str, requete_sql: str, resultat_sql: str) -> str:
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
    # Config
    chemin_db = "/workspace/local_files_transfer/test_multi_tables.db"
    api_base = "http://localhost:8000/v1"
    modele = "/workspace/models/mistral-7b-instruct"

    # Chargement
    db = charger_base_sqlite(chemin_db)
    llm = charger_llm(api_base=api_base, model_name=modele)
    agent = construire_agent(db=db, llm=llm)

    # Question initiale
    question = "Quels sont les 5 produits les plus vendus en 2024 ?"
    agent_output = agent.invoke(question)

    texte_brut = agent_output.get("output", "") if isinstance(agent_output, dict) else agent_output
    requete_sql = extraire_sql_depuis_texte(texte_brut)

    if not requete_sql:
        raise RuntimeError("Impossible d'extraire la requête SQL depuis la réponse du LLM.")

    # Exécution réelle de la requête SQL
    try:
        resultat_sql = db.run(requete_sql)
    except Exception as e:
        resultat_sql = f"[ERREUR SQL] {e}"

    # Réponse finale reformulée
    reponse = reponse_finale(llm, question, requete_sql, resultat_sql)
    afficher_reponse_llm_brute(reponse)


if __name__ == "__main__":
    main()
