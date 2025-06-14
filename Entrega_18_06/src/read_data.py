import pandas as pd
import zipfile
import yaml
import os


ROOT_PATH = ".."
# Function to load the configuration file in YAML
def load_config(config_path=os.path.join(ROOT_PATH,'config.yaml')):
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)
    
# Function to unzip files
def unzip_file(zip_path, dest_folder):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(dest_folder)

# Function to load CSV files
def load_data(csv_path):
    return pd.read_csv(csv_path)

# Main function to load data based on the configuration
def load_data_from_config(config):
    data_path = config['data_directory']
    
    # Ensure the data directory exists
    if not os.path.exists(data_path):
        print(f"Error: The data directory '{data_path}' does not exist.")
        return None
    
    # Load CSV files based on the configuration
    files = config['files']
    data = {}
    for name, file in files.items():
        full_path = os.path.join(data_path, file)
        
        # Check if the file is a zip file
        if file.endswith('.zip'):
            unzip_folder = data_path
            if not os.path.exists(unzip_folder):
                os.makedirs(unzip_folder)
            unzip_file(full_path, unzip_folder)
            
            # Find the CSV file inside the unzipped folder
            csv_file = [f for f in os.listdir(unzip_folder) if f.endswith('.csv')]
            if csv_file:
                full_path = os.path.join(unzip_folder, csv_file[0])
            else:
                print(f"Warning: No CSV file found in the zip file '{file}'")
                continue

        if os.path.exists(full_path):
            data[name] = load_data(full_path)
        else:
            print(f"Warning: The file '{file}' was not found in '{data_path}'")
    
    return data

# Example usage
config = load_config(os.path.join(ROOT_PATH,'config.yaml'))
loaded_data = load_data_from_config(config)

if loaded_data:
    df_fornecedores = loaded_data.get('header', None)
    df_itens = loaded_data.get('items', None)
    
    # Example print
    if df_fornecedores is not None:
        print(df_fornecedores.head())
    
    if df_itens is not None:
        print(df_itens.head())