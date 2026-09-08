import os
import tkinter as tk
from tkinter import filedialog

UPLOAD_FOLDER = "Заявления БД"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def select_file():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    file_path = filedialog.askopenfilename(
        title="Выберите файл",
        filetypes=[("Документы", "*.pdf *.doc *.docx *.txt"), ("Все файлы", "*.*")]
    )
    root.destroy()
    return file_path if file_path else None

def save_file(original_path, complaint_id):
    if not original_path or not os.path.exists(original_path):
        return None
    
    filename = f"Заявление_{complaint_id}_{os.path.basename(original_path)}"
    dest_path = os.path.join(UPLOAD_FOLDER, filename)
    
    with open(original_path, 'rb') as src:
        with open(dest_path, 'wb') as dst:
            dst.write(src.read())
    
    return dest_path

def open_file(file_path):
    if file_path and os.path.exists(file_path):
        os.startfile(file_path)
        return True
    return False

def delete_file(file_path):
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
        return True
    return False