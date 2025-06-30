import argparse
import re
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.agent_toolkits.sql.base import create_sql_agent
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

def construire_agent(db: SQLDatabase, llm: ChatOpenAI, verbose: bool = True):
    # Injecter directement la description des tables
    prefix = f"""Tu es un assistant SQL. Voici les tables de la base de données :

{db.get_table_info()}

Utilise uniquement les noms et colonnes présents ci-dessus pour répondre à la question suivante.
"""
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    return create_sql_agent(
        llm=llm,
        toolkit=toolkit,
        verbose=verbose,
        handle_parsing_errors=True,
        prefix=prefix
    )

def extraire_sql_depuis_texte(texte: str) -> str:
    match = re.search(r"```sql\n(.*?)\n```", texte, re.DOTALL)
    return match.group(1).strip() if match else None

def afficher_reponse_llm_brute(llm_response):
    if hasattr(llm_response, "content"):
        content = llm_response.content.strip().replace('\n\n', '\n')
        console.print("\n[bold cyan]📊 Réponse de l'assistant :[/bold cyan]\n")
        console.print(content, style="white")
    else:
        console.print("\n[bold red]❌ Réponse vide ou invalide du LLM[/bold red]")

def reponse_finale(llm: ChatOpenAI, question: str, requete_sql: str, resultat_sql: str):
    prompt = f"""
Tu es un assistant expert en base de données.

IMPORTANT :
- N'utilise pas de backslash (\\) dans les noms d'outils comme sql_db_query. Écris-les tels quels.
- Ne reformule pas les noms d'outils. Utilise uniquement : sql_db_query, sql_db_schema, sql_db_list_tables, sql_db_query_checker.

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
    agent = construire_agent(db=db, llm=llm)

    schema_info = db.get_table_info()
    question_modifiee = f"""Voici la structure de la base de données :

    {schema_info}

    Réponds à cette question en utilisant uniquement les noms de tables et colonnes présents : {question}
    """

    print("==== PROMPT UTILISÉ ====")
    print(question_modifiee)

    agent_output = agent.invoke(question_modifiee)
    texte_brut = agent_output.get("output", "") if isinstance(agent_output, dict) else str(agent_output)
    requete_sql = extraire_sql_depuis_texte(texte_brut)

    if not requete_sql:
        raise RuntimeError("❌ Impossible d'extraire la requête SQL depuis la réponse du LLM.")

    try:
        resultat_sql = db.run(requete_sql)
    except Exception as e:
        resultat_sql = f"[ERREUR SQL] {e}"

    console.print("\n[bold cyan]📊 Requête SQL générée :[/bold cyan]\n")

    
    reponse = reponse_finale(llm, question, requete_sql, resultat_sql)
    afficher_reponse_llm_brute(reponse)

if __name__ == "__main__":
    main()
