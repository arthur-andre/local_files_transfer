from langchain_community.utilities import SQLDatabase
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType

# Connexion à la base SQLite
db = SQLDatabase.from_uri("sqlite:////workspace/local_files_transfer/test_multi_tables.db")

# LLM local via vLLM
llm = ChatOpenAI(
    temperature=0,
    model="/workspace/models/mistral-7b-instruct",
    openai_api_base="http://localhost:8000/v1",
    openai_api_key="fake"
)

# Définition manuelle du nom et description du tool
sql_tool = QuerySQLDataBaseTool(db=db)
sql_tool.name = "query_sql"  # 👈 nom exact que le modèle doit utiliser
sql_tool.description = (
    "Use this tool to answer questions by executing SQL queries "
    "on a SQLite database containing tables such as 'ventes'. "
    "Always use 'query_sql' as the tool name — do not use backslashes or other symbols."
)

# Affichage pour contrôle
print("🛠️ Outils enregistrés :", [tool.name for tool in [sql_tool]])

# Agent avec le bon type
agent = initialize_agent(
    tools=[sql_tool],
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# Question à poser
question = "Quels sont les 5 produits les plus vendus en 2024 ?"
reponse = agent.run(question)

print("\n📊 Résultat réel :\n", reponse)
