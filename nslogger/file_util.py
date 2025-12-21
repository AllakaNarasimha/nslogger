from datetime import datetime
import re
import os


class FileUtil:
    def __init__(self):
        pass
    def get_all_files(self, directory):
        file_list = []   
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                file_list.append(file_path)
        return file_list 
    # end def
    def get_all_directories(self, directory):
        dir_list = []   
        for root, dirs, files in os.walk(directory):
            for dir in dirs:
                file_path = os.path.join(root, dir)
                dir_list.append(file_path)
        return dir_list 
    # end def
    def get_file(self, directory, search_pattern):
        for root, dirs, files in os.walk(directory):
            for file in files:
                if search_pattern in file:
                    return os.path.join(root, search_pattern)
        return None
    # end def
    def get_all_status_files(self, symbol, data_folder, search_filer = "_status.csv" ):
        dirs = self.get_all_directories(data_folder)
        files = []
        for dir in dirs:
            file = self.get_file(dir, os.path.join(symbol +  search_filer))
            if file:
                files.append(file)
        return files
    # end def
    
    def get_matched_files(self, symbol, data_folder, search_filer):
        files = self.get_all_files(data_folder)
        res = []
        for file in files:            
            if file.endswith(search_filer):            
                res.append(file)
        return res
    # end def
    
    def get_file_name_without_extension(self, file_path):
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        return file_name
    # end def
    
    def get_file_extension(self, file_path):
        file_name, file_ext = os.path.splitext(file_path)
        return file_ext
    # end def
    
    def get_datetime_from_file(self, file_path):
        file_name = os.path.splitext(os.path.basename(file_path))[0]
        date_str = re.search(r'\d{4}-\d{2}-\d{2}', file_name).group()
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    # end def

    def delete_dir(self, dir_path):
        files = self.get_all_files(dir_path)
        for file in files:
           os.remove(file)
        os.rmdir(dir_path)
    # end def