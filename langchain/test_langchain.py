from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI  # ⚠️ nécessite `pip install -U langchain-openai`
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.agent_toolkits.sql.base import create_sql_agent  # ✅ nouvelle importation


def charger_base_sqlite(db_path: str) -> SQLDatabase:
    """Charge la base SQLite depuis un chemin absolu."""
    return SQLDatabase.from_uri(f"sqlite:///{db_path}")


def charger_llm(api_base: str, model_name: str = "mistral") -> ChatOpenAI:
    """Configure un LLM local compatible OpenAI API (vLLM)."""
    return ChatOpenAI(
        temperature=0,
        model=model_name,
        openai_api_base=api_base,
        openai_api_key="fake"  # requis même si bidon
    )


def construire_agent(db: SQLDatabase, llm: ChatOpenAI, verbose: bool = True):
    """Construit un agent SQL LangChain avec les bons outils."""
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    return create_sql_agent(llm=llm, toolkit=toolkit, verbose=verbose, handle_parsing_errors=True)


def executer_question(agent, question: str):
    result = agent.invoke(question)
    return result['output'] if isinstance(result, dict) and 'output' in result else result


def main():
    chemin_db = "/workspace/local_files_transfer/test_multi_tables.db"
    api_base = "http://localhost:8000/v1"
    modele = "/workspace/models/mistral-7b-instruct"

    db = charger_base_sqlite(chemin_db)
    llm = charger_llm(api_base=api_base, model_name=modele)
    agent = construire_agent(db=db, llm=llm)

    question = "Quels sont les 5 produits les plus vendus en 2024 ?"
    reponse = executer_question(agent, question)

    print("\n📊 Réponse de l'agent :\n", reponse)


if __name__ == "__main__":
    main()
