from langchain_community.utilities import SQLDatabase
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType

db = SQLDatabase.from_uri("sqlite:////workspace/local_files_transfer/test_multi_tables.db")
llm = ChatOpenAI(temperature=0, model="/workspace/models/mistral-7b-instruct", openai_api_base="http://localhost:8000/v1", openai_api_key="fake")

# Outil SQL
sql_tool = QuerySQLDataBaseTool(db=db)
sql_tool.name = "query_sql"  # 🔧 nom simple et sûr

# Création d’un agent avec les outils
agent = initialize_agent(
    tools=[sql_tool],
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# Pose de la question
reponse = agent.run("Quels sont les 5 produits les plus vendus en 2024 ?")
print("\n📊 Résultat réel :\n", reponse)