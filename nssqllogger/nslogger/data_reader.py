import os
import subprocess
import pandas as pd
from .file_util import FileUtil
from .history_data_manager import HistoryDataManager

class DataReader:   
    def __init__(self):
        self.data_folder = None
        self.file_util = FileUtil()   

    def get_db_filename_from_folder(self, source_folder, dest_folder):        
        folder_name = os.path.basename(os.path.normpath(source_folder))
        folder_path = os.path.join(dest_folder, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        return os.path.join(folder_path, f"{folder_name}-history.db")
           

    def get_table_name_from_prefix(self, filename):    
        match filename:
            case _ if "-bfo-data" in filename:
                return "bfo_data"
            case _ if "-index-nfo-data" in filename:
                return "nfo_data"
            case _ if "instrument_df_" in filename:
                return "instrument_data"
            case _ if "tick_data_" in filename:
                return "tick_data"
            case _:
                return None
    def save_df(self, df, save_file):
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d %H:%M:%S')
        if 'expiry' in df.columns:
            df['expiry'] = pd.to_datetime(df['expiry']).dt.strftime('%Y-%m-%d') 
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime']).dt.tz_localize(None).dt.strftime('%Y-%m-%d %H:%M:%S')
        if not self.save_to_db_only:       
            df.to_csv(save_file)
        table_name = self.get_table_name_from_prefix(save_file)
        df = df.reset_index(drop=True)        
        self.history_data_manager.insert_df_to_table(df, table=table_name)

    def read(self, fileName, save_file):
        df = pd.read_feather(fileName)  
        self.save_df(df, save_file)
    # end def

    def convert_csv(self, file_path, save_file):
        try:
            if "feather" in self.file_util.get_file_extension(file_path):
                self.read(file_path, save_file)
                return
            
            if "zip" in self.file_util.get_file_extension(file_path):
                return
            
            with open(file_path, 'rb') as file:
                df = pd.read_pickle(file)

            if isinstance(df, pd.DataFrame):
                self.save_df(df, save_file)
            elif isinstance(df, dict):
                dict_data = []
                for instrument, data in df.items():
                    for values in data:
                        if len(values) == 2:
                            d = {
                                'instrument': instrument,
                                'datetime': values[0],
                                'price': values[1]
                            }
                        elif len(values) == 4:
                            d = {
                                'instrument': instrument,
                                'datetime': values[0],
                                'price': values[1],
                                'volume': values[2],
                                'oi': values[3]
                            }
                        else:
                            raise ValueError(f"Unexpected data format for instrument '{instrument}' with values '{values}'")
                        dict_data.append(d)
                dict_df = pd.DataFrame(dict_data)
                self.save_df(dict_df, save_file)
            else:
                raise TypeError(f"Unexpected data type: {type(df)}")
        except FileNotFoundError:
            print(f"Error: File not found at '{file_path}'")
        except ValueError as e:
            print(f"Error at {file_path}: {e}")
        except Exception as e:
            print(f"Unexpected error occurred at {file_path}: {e}")
    # end def
    
    def unzip_with_winrar(self, zip_path, extract_to):
        winrar_path = r"C:\Program Files\WinRAR\WinRAR.exe"  # Adjust this if WinRAR is installed in a different location
        zip_path = os.path.abspath(zip_path)
        if not os.path.isfile(zip_path):
            raise FileNotFoundError(f"The zip file does not exist: {zip_path}")
        if not os.path.exists(extract_to):
            os.makedirs(extract_to, exist_ok=True)
        command = [winrar_path, 'x', '-inul', '-o+', zip_path, extract_to]
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)
        except subprocess.CalledProcessError as e:
            print(f"Error occurred: {e}")
            if e.stdout:
                print(f"stdout: {e.stdout}")
            if e.stderr:
                print(f"stderr: {e.stderr}")
    # end def
    
    def unzip_folder(self, data_folder):
        zip_files = self.file_util.get_all_files(data_folder)        
        for zip_file in zip_files:
            file_ext = self.file_util.get_file_extension(zip_file)
            if "zip" in file_ext:
                if data_folder == self.data_folder:
                    unzip_folder =  os.path.join(data_folder, "zip")
                    try:
                        self.unzip_with_winrar(zip_file, unzip_folder) 
                        zip_extracted_files = self.file_util.get_all_files(unzip_folder)
                        for uzip_extracted_file in zip_extracted_files:
                            try:
                                if "zip" in self.file_util.get_file_extension(uzip_extracted_file):
                                    self.unzip_with_winrar(uzip_extracted_file, unzip_folder) 
                                    os.remove(uzip_extracted_file) 
                            except:
                                print(f"corrupted :{uzip_extracted_file}")

                    except:
                        print(f"corrupted :{zip_file}")
                else:
                    try:
                        self.unzip_with_winrar(zip_file, data_folder) 
                        os.remove(zip_file) 
                    except:
                        print(f"corrupted :{zip_file}") 
    # end def

    def generate_csv_files(self, source_folder, dest_folder):
        os.makedirs(dest_folder, exist_ok=True)        
        self.data_folder = source_folder
        # Extract date folder name and initialize HistoryDataManager
        db_date = os.path.basename(os.path.normpath(source_folder))
        # Create HistoryDataManager with date-based filename (e.g., 07dec25_history.db)
        self.history_data_manager = HistoryDataManager("history.db")
        self.unzip_folder(source_folder)
        
        files = self.file_util.get_all_files(source_folder)
        for file in files:
            if self.file_util.get_file_extension(file) in [".csv", ".zip"]:
                continue
            else:
                file_name = self.file_util.get_file_name_without_extension(file)
                if "feather" in self.file_util.get_file_extension(file):
                    date_part = file_name[:10]
                else:
                    date_part = file_name[-10:]
                
                date_dest_folder = os.path.join(dest_folder, date_part)
                os.makedirs(date_dest_folder, exist_ok=True)
                print(f"Processing file: {file} to {date_dest_folder}/{file_name}.csv")
                self.convert_csv(file, f"{date_dest_folder}/{file_name}.csv")

        # cleanup source folder
        self.file_util.delete_dir(os.path.join(source_folder, "zip"))       

    def generate_data(self, source_folder, dest_folder, save_to_db_only=False):
        self.save_to_db_only = save_to_db_only
        dirs = self.file_util.get_all_directories(source_folder)
        for dir in dirs:
            print("Processing folder:", dir)
            self.generate_csv_files(dir, dest_folder)

if __name__ == "__main__":
    print("start")
    feather_reader = DataReader()
    data_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
    csv_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'csv'))
    feather_reader.generate_data(data_folder, csv_folder, save_to_db_only=True)
    print("end")
