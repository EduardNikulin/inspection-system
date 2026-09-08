import os
import pyodbc
from dotenv import load_file


load_file()     # Загружаем переменные из файла .env в системное окружение

# Данные конфигурации считываются из переменных окружения.
# Если они не заданы, используются дефолтные безопасные значения.
SERVER = os.getenv("DB_SERVER", "localhost")
DATABASE = os.getenv("DB_NAME", "Никулин_ТрудИнспекция")

# Формирование строки подключения DSN для драйвера pyodbc с авторизацией Windows NT (Trusted_Connection).
# Encrypt=no отключает обязательное SSL-шифрование, что необходимо для локального тестирования на сервере разработки.
CONNECTION_STRING = (
    f"DRIVER={{ODBC Driver 18 for SQL Server}};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    f"Trusted_Connection=yes;"
    f"Encrypt=no;"
)

def get_connection():
    """Возвращает подключение к базе данных SQL Server."""
    return pyodbc.connect(CONNECTION_STRING)