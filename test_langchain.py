from langchain.sql_database import SQLDatabase
from langchain.chat_models import ChatOpenAI
from langchain.agents import create_sql_agent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit

# Chemin vers la base SQLite
db = SQLDatabase.from_uri("sqlite:///local_files_transfer/test_multi_tables.db")

# LLM local compatible OpenAI
llm = ChatOpenAI(
    temperature=0,
    model="/workspace/models/mistral-7b-instruct",
    openai_api_base="http://localhost:8000/v1/completions",
    openai_api_key="fake"
)

agent = create_sql_agent(llm=llm, toolkit=SQLDatabaseToolkit(db=db, llm=llm), verbose=True)

# Exécution
response = agent.run("Quels sont les 5 produits les plus vendus en 2024 ?")
print(response)
