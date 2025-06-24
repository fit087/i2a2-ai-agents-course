from typing import Dict, List, Union
import sqlite3
from pathlib import Path
import re
import pandas as pd

class DatabaseManager:
    """Classe responsável por gerenciar o banco de dados SQLite com múltiplas tabelas"""

    def __init__(self, csv_sources: Union[str, List[str]], db_path: str = "data.db"):
        """
        Inicializa o gerenciador de banco de dados

        Args:
            csv_sources: Caminho para arquivo CSV, lista de caminhos, ou diretório contendo CSVs
            db_path: Caminho para o banco de dados SQLite
        """
        self.db_path = db_path
        self.tables_info = {}  # Dicionário {nome_tabela: info_tabela}

        # Processa as fontes CSV
        self.csv_files = self._process_csv_sources(csv_sources)

        # Carrega todos os CSVs no SQLite
        self._load_csvs_to_sqlite()

        # Obtém informações de todas as tabelas
        self._get_all_tables_schema()

    def _process_csv_sources(self, csv_sources: Union[str, List[str]]) -> Dict[str, str]:
        """
        Processa as fontes CSV e retorna dicionário {nome_tabela: caminho_arquivo}
        """
        csv_files = {}

        if isinstance(csv_sources, str):
            # Se é string, pode ser arquivo ou diretório
            path = Path(csv_sources)

            if path.is_file() and path.suffix.lower() == '.csv':
                # É um arquivo CSV único
                table_name = self._generate_table_name(path.stem)
                csv_files[table_name] = str(path)

            elif path.is_dir():
                # É um diretório, busca todos os CSVs
                for csv_file in path.glob("*.csv"):
                    table_name = self._generate_table_name(csv_file.stem)
                    csv_files[table_name] = str(csv_file)

            else:
                raise ValueError(f"Caminho não é arquivo CSV válido nem diretório: {csv_sources}")

        elif isinstance(csv_sources, list):
            # É uma lista de caminhos
            for csv_path in csv_sources:
                path = Path(csv_path)
                if path.is_file() and path.suffix.lower() == '.csv':
                    table_name = self._generate_table_name(path.stem)
                    csv_files[table_name] = str(path)
                else:
                    print(f"Ignorando arquivo não-CSV: {csv_path}")

        if not csv_files:
            raise ValueError("Nenhum arquivo CSV válido encontrado")

        print(f"Encontrados {len(csv_files)} arquivo(s) CSV:")
        for table_name, file_path in csv_files.items():
            print(f"   - {table_name} ← {file_path}")

        return csv_files

    def _generate_table_name(self, filename: str) -> str:
        """
        Gera nome de tabela válido a partir do nome do arquivo
        """
        # Remove caracteres especiais e espaços, converte para minúsculas
        table_name = re.sub(r'[^\w\s]', '', filename)
        table_name = re.sub(r'\s+', '_', table_name)
        table_name = table_name.lower().strip('_')

        # Garante que não comece com número
        if table_name[0].isdigit():
            table_name = f"tabela_{table_name}"

        return table_name

    def _load_csvs_to_sqlite(self):
      """Carrega todos os arquivos CSV no banco de dados SQLite"""
      try:
          conn = sqlite3.connect(self.db_path)

          for table_name, csv_path in self.csv_files.items():
              print(f"Carregando {csv_path} → tabela '{table_name}'...")

              # Lê CSV
              df = pd.read_csv(csv_path)

              # Renomeia colunas: espaços viram underscores
              df.columns = [col.strip().replace(" ", "_") for col in df.columns]

              # Carrega no SQLite
              df.to_sql(table_name, conn, if_exists='replace', index=False)

              print(f"{len(df)} linhas, {len(df.columns)} colunas")

          conn.close()
          print(f"Todos os CSVs carregados no banco: {self.db_path}")

      except Exception as e:
          raise Exception(f"Erro ao carregar CSVs no SQLite: {str(e)}")

    def _get_all_tables_schema(self):
        """Obtém informações do schema de todas as tabelas"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for table_name in self.csv_files.keys():
            # Obtém informações das colunas
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()

            # Obtém dados de exemplo
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
            sample_data = cursor.fetchall()

            # Obtém contagem total
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            total_rows = cursor.fetchone()[0]

            # Monta informações da tabela
            table_info = {
                'columns': columns,
                'sample_data': sample_data,
                'total_rows': total_rows,
                'csv_source': self.csv_files[table_name]
            }

            self.tables_info[table_name] = table_info

        conn.close()

    def get_database_schema(self) -> str:
        """Retorna schema completo do banco de dados"""
        schema_info = "=== ESQUEMA DO BANCO DE DADOS ===\n\n"

        for table_name, info in self.tables_info.items():
            schema_info += f"TABELA: {table_name}\n"
            schema_info += f"Fonte: {info['csv_source']}\n"
            schema_info += f"Total de registros: {info['total_rows']}\n"
            schema_info += "Colunas:\n"

            for col in info['columns']:
                schema_info += f"  - {col[1]} ({col[2]})\n"

            schema_info += "\nDados de exemplo:\n"
            column_names = [col[1] for col in info['columns']]
            schema_info += f"  {column_names}\n"

            for row in info['sample_data']:
                schema_info += f"  {list(row)}\n"

            schema_info += "\n" + "="*50 + "\n\n"

        return schema_info

    def get_tables_list(self) -> List[str]:
        """Retorna lista dos nomes das tabelas"""
        return list(self.tables_info.keys())

    def get_table_info(self, table_name: str) -> Dict:
        """Retorna informações de uma tabela específica"""
        return self.tables_info.get(table_name, {})

    def execute_sql_query(self, sql_query: str) -> List[Dict]:
        """Executa consulta SQL e retorna resultados"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(sql_query)
            results = cursor.fetchall()

            print(f'{results=}')
            print(f'{cursor.description=}')

            # Obtém nomes das colunas
            column_names = [description[0] for description in cursor.description]

            print(f'{column_names=}')
            conn.close()

            # Converte para lista de dicionários
            result_dicts = []
            for row in results:
                result_dicts.append(dict(zip(column_names, row)))

            return result_dicts

        except Exception as e:
            raise Exception(f"Erro ao executar SQL: {str(e)}")