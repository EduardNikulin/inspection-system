from database import get_connection

def get_messages_for_complaint(complaint_id, user_id):
    """
    Получить все сообщения по жалобе.
    Помечает сообщения как прочитанные для текущего пользователя.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Помечаем как прочитанные все сообщения, где текущий пользователь - получатель
    cursor.execute("""
        UPDATE messages
        SET is_read = 1
        WHERE complaint_id = ? AND recipient_id = ?
    """, (complaint_id, user_id))
    conn.commit()
    
    # Получаем все сообщения
    cursor.execute("""
        SELECT 
            m.id,
            m.text,
            m.created_at,
            u_sender.first_name + ' ' + u_sender.last_name AS sender_full_name,
            u_sender.role AS sender_role,
            m.is_read
        FROM messages m
        JOIN users u_sender ON m.sender_id = u_sender.id
        WHERE m.complaint_id = ?
        ORDER BY m.created_at ASC
    """, (complaint_id,))
    
    messages = cursor.fetchall()
    cursor.close()
    conn.close()
    return messages

def send_message(complaint_id, sender_id, recipient_id, text):
    """Отправить новое сообщение"""
    if not text or not text.strip():
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO messages (complaint_id, sender_id, recipient_id, text)
        VALUES (?, ?, ?, ?)
    """, (complaint_id, sender_id, recipient_id, text.strip()))
    conn.commit()
    
    cursor.close()
    conn.close()
    return True

def get_recipient_id_for_complaint(complaint_id, sender_role, sender_id):
    """
    Определить получателя в зависимости от роли отправителя
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    if sender_role == 'citizen':
        # Гражданин пишет работнику, назначенному на жалобу
        cursor.execute("""
            SELECT assigned_to_id FROM complaints WHERE id = ?
        """, (complaint_id,))
        row = cursor.fetchone()
        if row and row[0]:
            recipient_id = row[0]
        else:
            # Если работник не назначен, пишем админу
            cursor.execute("SELECT TOP 1 id FROM users WHERE role = 'admin'")
            row = cursor.fetchone()
            recipient_id = row[0] if row else None
    elif sender_role == 'worker':
        # Работник пишет гражданину (автору жалобы)
        cursor.execute("SELECT user_id FROM complaints WHERE id = ?", (complaint_id,))
        row = cursor.fetchone()
        recipient_id = row[0] if row else None
    else:  # admin
        # Админ пишет гражданину
        cursor.execute("SELECT user_id FROM complaints WHERE id = ?", (complaint_id,))
        row = cursor.fetchone()
        recipient_id = row[0] if row else None
    
    cursor.close()
    conn.close()
    return recipient_id

def get_unread_count_for_user(user_id):
    """Количество непрочитанных сообщений у пользователя"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM messages
        WHERE recipient_id = ? AND is_read = 0
    """, (user_id,))
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return count

def display_complaint_messages(complaint_id, user_id):
    """Показать переписку по жалобе"""
    messages = get_messages_for_complaint(complaint_id, user_id)
    
    if not messages:
        print("\nСообщений по этой жалобе пока нет.")
        return
    
    print(f"\n=== ПЕРЕПИСКА ПО ЖАЛОБЕ #{complaint_id} ===")
    print("-" * 50)
    
    for msg in messages:
        sender_role_display = {
            'citizen': 'ГРАЖДАНИН',
            'worker': 'РАБОТНИК',
            'admin': 'АДМИНИСТРАТОР'
        }.get(msg.sender_role, msg.sender_role)
        read_mark = "✓" if msg.is_read else "●"
        print(f"[{msg.created_at}] {sender_role_display} {msg.sender_full_name} {read_mark}:")
        print(f"    {msg.text}")
        print("-" * 50)

def get_complaint_author(complaint_id):
    """Получить ID автора жалобы"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM complaints WHERE id = ?", (complaint_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row else None

def get_complaint_assigned_worker(complaint_id):
    """Получить ID назначенного работника на жалобу"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT assigned_to_id FROM complaints WHERE id = ?", (complaint_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row else None