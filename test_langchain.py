from langchain_community.utilities import SQLDatabase
from langchain_community.chat_models import ChatOpenAI
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain.agents import create_sql_agent


def charger_base_sqlite(db_path: str) -> SQLDatabase:
    """Charge la base SQLite depuis un chemin absolu."""
    return SQLDatabase.from_uri(f"sqlite:///{db_path}")


def charger_llm(api_base: str, model_name: str = "mistral") -> ChatOpenAI:
    """Configure un LLM local compatible OpenAI API (vLLM)."""
    return ChatOpenAI(
        temperature=0,
        model=model_name,
        openai_api_base=api_base,
        openai_api_key="fake"  # valeur bidon, requise par interface
    )


def construire_agent(db: SQLDatabase, llm: ChatOpenAI, verbose: bool = True):
    """Construit un agent SQL LangChain avec les bons outils."""
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    tools = toolkit.get_tools()
    return create_sql_agent(llm=llm, tools=tools, verbose=verbose)


def executer_question(agent, question: str):
    """Exécute une question via l'agent et retourne la réponse."""
    return agent.invoke(question)


def main():
    # Chemins et config
    chemin_db = "/root/local_files_transfer/test_multi_tables.db"
    api_base = "http://localhost:8000/v1"
    modele = "mistral"  # ou nom du modèle listé dans /v1/models

    # Chargement des composants
    db = charger_base_sqlite(chemin_db)
    llm = charger_llm(api_base=api_base, model_name=modele)
    agent = construire_agent(db=db, llm=llm)

    # Question à poser
    question = "Quels sont les 5 produits les plus vendus en 2024 ?"
    reponse = executer_question(agent, question)

    print("\n📊 Réponse de l'agent :\n", reponse)


if __name__ == "__main__":
    main()
