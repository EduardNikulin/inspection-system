import pyodbc

SERVER = 'localhost'
DATABASE = 'Никулин_проект_Б-ИСиТ-22'
CONNECTION_STRING = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;Encrypt=no;'

def get_connection():
    """Возвращает подключение к базе данных"""
    return pyodbc.connect(CONNECTION_STRING)