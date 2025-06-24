from database_manager import DatabaseManager
from csv_agent import CSVAgent
import gradio as gr

def create_agent() -> CSVAgent:
    """
    Função auxiliar para criar um agente CSV completo

    Args:
        csv_sources: Arquivo CSV, lista de arquivos, ou diretório com CSVs
        db_path: Caminho para o banco de dados SQLite

    Returns:
        Instância configurada do CSVAgent
    """
    # Cria gerenciador de banco de dados
    db_manager = DatabaseManager('./Agent/data', 'data.db')

    # Cria e retorna agente
    agent = CSVAgent(db_manager)

    return agent

def chat(message, history):
    result = agent.query(message)
    response = result['resposta']
    if result['funcao_chamada']:
        response += f"\n\nSQL Utilizado: {result['consulta_sql']}"
    return response

agent = create_agent()

example_questions = [
    "Qual foi o valor total de notas emitidas em janeiro de 2024?",
    "Quais foram os produtos mais vendidos em quantidade?",
    "Qual empresa mais emitiu notas fiscais no período?",
    "Quais notas fiscais foram emitidas para o estado de Minas Gerais?",
    "Qual o ticket médio por nota fiscal emitida?",
    "Quais produtos vendidos tiveram valor unitário acima de R$ 1.000?",
    "Quantas operações foram realizadas com consumidor final?",
    "Liste as notas fiscais com presença do comprador em operação presencial."
]

gr.ChatInterface(chat, type="messages", examples=example_questions).launch()