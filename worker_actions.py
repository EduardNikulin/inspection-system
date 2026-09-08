from database import get_connection
from file_utils import open_file
from messenger import display_complaint_messages, send_message, get_recipient_id_for_complaint
import os

def ask_yes_no(prompt, default=False):
    if default:
        user_input = input(f"{prompt} (Да/нет): ").strip().lower()
        return user_input not in ['нет', 'no', 'n']
    else:
        user_input = input(f"{prompt} (да/Нет): ").strip().lower()
        return user_input in ['да', 'yes', 'y']

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def view_my_assigned_complaints(worker_id):
    """Просмотр жалоб, назначенных на работника"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            c.id,
            u_citizen.first_name + ' ' + u_citizen.last_name AS citizen_name,
            cat.name AS category_name,
            stat.name AS status_name,
            c.employer_name,
            c.description,
            c.file_path,
            c.created_at,
            c.is_archived,
            cw.has_new_messages_for_worker
        FROM complaints c
        JOIN users u_citizen ON c.user_id = u_citizen.id
        JOIN complaint_categories cat ON c.category_id = cat.id
        JOIN complaint_statuses stat ON c.status_id = stat.id
        JOIN complaints_with_new_messages cw ON c.id = cw.id
        WHERE c.assigned_to_id = ?
        ORDER BY c.is_archived, c.created_at DESC
    """, (worker_id,))
    
    complaints = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not complaints:
        print("\nВам не назначены жалобы")
        return
    
    print("\nМОИ НАЗНАЧЕННЫЕ ЖАЛОБЫ")
    print("=" * 60)
    for comp in complaints:
        archived_mark = " [АРХИВ]" if comp.is_archived else ""
        new_mark = " [ЕСТЬ НОВЫЕ СООБЩЕНИЯ]" if comp.has_new_messages_for_worker else ""
        print(f"\nЖАЛОБА #{comp.id}{archived_mark}{new_mark}")
        print(f"\tГражданин: {comp.citizen_name}")
        print(f"\tСтатус: {comp.status_name}")
        print(f"\tОрганизация: {comp.employer_name}")
        print(f"\tОписание: {comp.description[:200]}")
        print(f"\tДата: {comp.created_at}")
        if comp.file_path:
            print(f"\tФайл: {os.path.basename(comp.file_path)}")
            if ask_yes_no("\tОткрыть файл", default=False):
                open_file(comp.file_path)
        print("-" * 40)
    
    choice = input("\nВведите ID жалобы для работы (или 0 для выхода): ").strip()
    if not choice.isdigit() or int(choice) == 0:
        return
    
    complaint_id = int(choice)
    manage_complaint_worker(worker_id, complaint_id)

def manage_complaint_worker(worker_id, complaint_id):
    """Меню управления жалобой для работника"""
    while True:
        clear_screen()
        print(f"\nУПРАВЛЕНИЕ ЖАЛОБОЙ #{complaint_id}")
        print("=" * 50)
        print("1. Просмотр жалобы")
        print("2. Переписка с гражданином")
        print("3. Открыть файл")
        print("4. Закрыть жалобу (статус -> Закрыта)")
        print("0. Вернуться к списку")
        print("-" * 50)
        
        choice = input("Выберите действие: ").strip()
        
        if choice == '1':
            view_complaint_details_worker(complaint_id)
        elif choice == '2':
            view_complaint_messages_worker(worker_id, complaint_id)
        elif choice == '3':
            open_complaint_file_worker(complaint_id)
        elif choice == '4':
            close_complaint_worker(complaint_id)
            input("\nНажмите Enter для продолжения...")
            return
        elif choice == '0':
            return
        else:
            print("Неверный выбор")
            input("\nНажмите Enter для продолжения...")

def view_complaint_details_worker(complaint_id):
    """Просмотр полной информации о жалобе"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            c.id,
            u_citizen.first_name + ' ' + u_citizen.last_name AS citizen_name,
            cat.name AS category_name,
            stat.name AS status_name,
            c.employer_name,
            c.description,
            c.file_path,
            c.created_at,
            c.is_archived
        FROM complaints c
        JOIN users u_citizen ON c.user_id = u_citizen.id
        JOIN complaint_categories cat ON c.category_id = cat.id
        JOIN complaint_statuses stat ON c.status_id = stat.id
        WHERE c.id = ?
    """, (complaint_id,))
    
    comp = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not comp:
        print("Жалоба не найдена")
        return
    
    archived_mark = " [АРХИВ]" if comp.is_archived else ""
    print(f"\n=== ЖАЛОБА #{comp.id}{archived_mark} ===")
    print(f"Гражданин: {comp.citizen_name}")
    print(f"Категория: {comp.category_name}")
    print(f"Статус: {comp.status_name}")
    print(f"Организация: {comp.employer_name}")
    print(f"Описание: {comp.description}")
    if comp.file_path:
        print(f"Файл: {os.path.basename(comp.file_path)}")
    print(f"Дата: {comp.created_at}")
    print("-" * 40)
    input("\nНажмите Enter для продолжения...")

def open_complaint_file_worker(complaint_id):
    """Открыть файл, прикреплённый к жалобе"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT file_path FROM complaints WHERE id = ?", (complaint_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if row and row.file_path:
        open_file(row.file_path)
        print(f"Файл открыт: {os.path.basename(row.file_path)}")
    else:
        print("Файл не прикреплён к этой жалобе")
    input("\nНажмите Enter для продолжения...")

def view_complaint_messages_worker(worker_id, complaint_id):
    """Просмотр переписки и отправка сообщения гражданину"""
    display_complaint_messages(complaint_id, worker_id)
    
    if ask_yes_no("\nНаписать сообщение гражданину", default=False):
        text = input("Введите текст сообщения: ").strip()
        if text:
            recipient_id = get_recipient_id_for_complaint(complaint_id, 'worker', worker_id)
            if recipient_id:
                send_message(complaint_id, worker_id, recipient_id, text)
                print("Сообщение отправлено")
            else:
                print("Не удалось определить получателя")
        else:
            print("Сообщение не может быть пустым")
    input("\nНажмите Enter для продолжения...")

def close_complaint_worker(complaint_id):
    """Закрыть жалобу (статус -> Закрыта)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE complaints 
        SET status_id = 3 
        WHERE id = ? AND is_archived = 0
    """, (complaint_id,))
    conn.commit()
    cursor.close()
    conn.close()
    print(f"Жалоба #{complaint_id} закрыта (статус -> Закрыта)")