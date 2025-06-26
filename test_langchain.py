from langchain_community.utilities import SQLDatabase
from langchain_community.chat_models import ChatOpenAI
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit

# Chemin vers la base SQLite
db = SQLDatabase.from_uri("sqlite:////root/local_files_transfer/test_multi_tables.db")

# LLM local compatible OpenAI
llm = ChatOpenAI(
    temperature=0,
    model="/workspace/models/mistral-7b-instruct",
    openai_api_base="http://localhost:8000/v1/",
    openai_api_key="fake"
)

agent = create_sql_agent(llm=llm, toolkit=SQLDatabaseToolkit(db=db, llm=llm), verbose=True)

# Exécution
response = agent.run("Quels sont les 5 produits les plus vendus en 2024 ?")
print(response)
