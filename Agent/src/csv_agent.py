from database_manager import DatabaseManager
from prompts import *
from typing import Optional, Dict, Any
from langchain_mistralai import ChatMistralAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from dotenv import load_dotenv
import os
import json
import re

load_dotenv()

class CSVAgent:
    """Agente para análise de dados CSV usando LangChain e Mistral AI"""

    def __init__(self,
                 database_manager: DatabaseManager,
                 general_llm: Optional[ChatMistralAI] = None,
                 sql_llm: Optional[ChatMistralAI] = None):
        """
        Inicializa o agente CSV

        Args:
            database_manager: Instância do DatabaseManager
            general_llm: LLM para uso geral (opcional)
            sql_llm: LLM para geração de SQL (opcional)
        """
        self.db_manager = database_manager

        # Configura LLMs padrão se não fornecidos
        if general_llm is None:
            self.llm = ChatMistralAI(
                model="mistral-medium-latest",
                api_key=os.getenv('MISTRAL_API_KEY'),
                temperature=0.1
            )
        else:
            self.llm = general_llm

        if sql_llm is None:
            self.sql_llm = ChatMistralAI(
                model="codestral-latest",
                api_key=os.getenv('MISTRAL_API_KEY'),
                temperature=0.1
            )
        else:
            self.sql_llm = sql_llm

        # Configura ferramentas e agente
        self._setup_tools_and_agent()

    def _setup_tools_and_agent(self):
        """Configura ferramentas e agente do LangChain"""

        # Cria a ferramenta de consulta ao banco de dados
        @tool
        def consultar_banco_dados(consulta_linguagem_natural: str) -> str:
            """
            Executa consultas SQL nos dados CSV carregados.
            Use esta ferramenta quando o usuário pedir dados específicos, contagens, estatísticas,
            filtragem, análise ou qualquer operação que envolva os dados das tabelas.

            Args:
                consulta_linguagem_natural: A pergunta do usuário sobre os dados

            Returns:
                String JSON com os resultados da consulta
            """
            try:
                print(f"Executando consulta no banco para: {consulta_linguagem_natural}")

                # Gera consulta SQL usando Codestral
                sql_query = self._generate_sql_query(consulta_linguagem_natural)
                print(f"SQL gerado: {sql_query}")

                # Executa consulta
                results = self.db_manager.execute_sql_query(sql_query)
                print(f"Consulta retornou {len(results)} resultados")

                return json.dumps({
                    "sucesso": True,
                    "consulta_sql": sql_query,
                    "resultados": results,
                    "total_resultados": len(results),
                    "tabelas_disponiveis": self.db_manager.get_tables_list()
                }, indent=2, default=str, ensure_ascii=False)

            except Exception as e:
                print(f"Erro na consulta ao banco: {str(e)}")
                return json.dumps({
                    "sucesso": False,
                    "erro": str(e),
                    "consulta_sql": None,
                    "resultados": [],
                    "total_resultados": 0,
                    "tabelas_disponiveis": self.db_manager.get_tables_list()
                }, ensure_ascii=False)

        # Armazena a ferramenta
        self.database_tool = consultar_banco_dados

        # Cria prompt do sistema
        self.system_prompt = get_system_prompt(
            database_schema=self.db_manager.get_database_schema(),
            tables_list=', '.join(self.db_manager.get_tables_list())
        )
        # Cria lista de ferramentas
        self.tools = [self.database_tool]

        # Cria agente
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", self.system_prompt),
                ("human", "{input}"),
                MessagesPlaceholder("agent_scratchpad")
            ])

            self.agent = create_tool_calling_agent(self.llm, self.tools, prompt)
            self.agent_executor = AgentExecutor(
                agent=self.agent,
                tools=self.tools,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=3,
                return_intermediate_steps=True
            )

        except Exception as e:
            print(f"Aviso: Não foi possível criar o executor do agente: {e}")
            self.agent_executor = None

    def _generate_sql_query(self, user_query: str) -> str:
        """Gera consulta SQL a partir de linguagem natural usando LLM"""
        sql_prompt = get_sql_prompt(
            database_schema=self.db_manager.get_database_schema(),
            tables_list=', '.join(self.db_manager.get_tables_list()),
            user_query=user_query
        )

        try:
            response = self.sql_llm.invoke(sql_prompt)

            # Limpa a consulta SQL
            sql_query = response.content
            sql_query = re.sub(r'```sql\n?', '', sql_query)
            sql_query = re.sub(r'```\n?', '', sql_query)
            sql_query = sql_query.strip()

            # Remove ponto e vírgula final se presente
            if sql_query.endswith(';'):
                sql_query = sql_query[:-1]

            return sql_query

        except Exception as e:
            raise Exception(f"Erro ao gerar SQL: {str(e)}")

    def query(self, user_input: str) -> Dict[str, Any]:
        """
        Método principal para processar consultas do usuário

        Args:
            user_input: Consulta em linguagem natural do usuário

        Returns:
            Dicionário contendo resposta e metadados
        """
        try:
            if self.agent_executor:
                print(f"Processando consulta com agente Mistral: {user_input}")

                # Executa com agente
                result = self.agent_executor.invoke({"input": user_input})

                # Captura a consulta SQL dos intermediate_steps
                sql_query = None
                function_called = False

                for step in result.get("intermediate_steps", []):
                    if len(step) > 1 and "consultar_banco_dados" in str(step[0]):
                        function_called = True
                        try:
                            resposta = json.loads(step[1])
                            sql_query = resposta.get("consulta_sql")
                            break
                        except:
                            pass
                return {
                    "resposta": result["output"],
                    "tipo_consulta": "executor_agent",
                    "funcao_chamada": function_called,
                    "consulta_sql": sql_query,
                    "sucesso": True,
                    "modelo_usado": self.llm.model,
                    "tabelas_disponiveis": self.db_manager.get_tables_list(),
                    "resultado_agente_bruto": result
                }

        except Exception as e:
            error_msg = f"Encontrei um erro: {str(e)}"
            print(f"Erro no processamento da consulta: {str(e)}")

            return {
                "resposta": error_msg,
                "tipo_consulta": "erro",
                "funcao_chamada": False,
                "sucesso": False,
                "erro": str(e),
                "tabelas_disponiveis": self.db_manager.get_tables_list()
            }
