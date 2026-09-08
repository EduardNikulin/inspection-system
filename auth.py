import hashlib
from database import get_connection

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login(login, password):
    conn = get_connection()
    cursor = conn.cursor()
    
    password_hash = hash_password(password)
    cursor.execute(
        "SELECT id, login, role FROM users WHERE login = ? AND password_hash = ?",
        (login, password_hash)
    )
    user = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if user:
        return {'id': user.id, 'login': user.login, 'role': user.role}
    return None

def register(login, password, first_name, last_name):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Проверяем, существует ли уже такой логин
    cursor.execute("SELECT id FROM users WHERE login = ?", (login,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return False, "Логин уже существует"
    
    password_hash = hash_password(password)
    cursor.execute("""
        INSERT INTO users (login, password_hash, role, first_name, last_name)
        VALUES (?, ?, 'citizen', ?, ?)
    """, (login, password_hash, first_name, last_name))
    conn.commit()
    
    cursor.close()
    conn.close()
    return True, "Регистрация успешна"