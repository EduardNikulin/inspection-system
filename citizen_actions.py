from database import get_connection
from file_utils import select_file, save_file, open_file
from messenger import display_complaint_messages, send_message, get_recipient_id_for_complaint
import os

def ask_yes_no(prompt, default=False):
    if default:
        user_input = input(f"{prompt} (Да/нет): ").strip().lower()
        return user_input not in ['нет', 'no', 'n']
    else:
        user_input = input(f"{prompt} (да/Нет): ").strip().lower()
        return user_input in ['да', 'yes', 'y']

def get_categories():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM complaint_categories")
    categories = cursor.fetchall()
    cursor.close()
    conn.close()
    return categories

def submit_complaint(user_id):
    print("\nПОДАЧА НОВОЙ ЖАЛОБЫ")
    print("-" * 40)

    categories = get_categories()
    print("\nКатегории:")
    for cat in categories:
        print(f"\t{cat.id}. {cat.name}")

    while True:
        cat_id = input("Выберите номер категории: ").strip()
        if not cat_id.isdigit():
            print("Ошибка: введите число")
            continue
        cat_id = int(cat_id)
        if any(c.id == cat_id for c in categories):
            break
        print("Неверная категория")

    employer = input("Название организации: ").strip()
    while not employer:
        print("Название обязательно")
        employer = input("Название организации: ").strip()

    description = input("Описание жалобы: ").strip()
    while not description:
        print("Описание обязательно")
        description = input("Описание жалобы: ").strip()

    selected = None
    if ask_yes_no("Прикрепить файл", default=False):
        selected = select_file()
        if selected:
            print(f"Выбран файл: {os.path.basename(selected)}")
        else:
            print("Файл не выбран")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO complaints (user_id, category_id, status_id, employer_name, description)
        VALUES (?, ?, 1, ?, ?)
    """, (user_id, cat_id, employer, description))
    conn.commit()

    cursor.execute("SELECT @@IDENTITY AS id")
    complaint_id = cursor.fetchone().id

    if selected:
        saved_path = save_file(selected, complaint_id)
        if saved_path:
            cursor.execute("UPDATE complaints SET file_path = ? WHERE id = ?", (saved_path, complaint_id))
            conn.commit()
            print("Файл сохранён")

    cursor.close()
    conn.close()
    print(f"Жалоба #{complaint_id} подана")

def view_my_complaints(user_id):
    """Просмотр своих активных жалоб с возможностью открыть переписку"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            c.id,
            cat.name AS category_name,
            stat.name AS status_name,
            c.employer_name,
            c.description,
            c.file_path,
            c.created_at,
            cw.has_new_messages_for_citizen,
            u_worker.first_name + ' ' + u_worker.last_name AS worker_name
        FROM complaints c
        JOIN complaint_categories cat ON c.category_id = cat.id
        JOIN complaint_statuses stat ON c.status_id = stat.id
        JOIN complaints_with_new_messages cw ON c.id = cw.id
        LEFT JOIN users u_worker ON c.assigned_to_id = u_worker.id
        WHERE c.user_id = ? AND c.is_archived = 0
        ORDER BY c.created_at DESC
    """, (user_id,))
    
    complaints = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not complaints:
        print("\nУ вас нет активных жалоб")
        return
    
    print("\nМОИ АКТИВНЫЕ ЖАЛОБЫ")
    print("=" * 60)
    for comp in complaints:
        new_mark = " [✉ ЕСТЬ НОВЫЕ СООБЩЕНИЯ]" if comp.has_new_messages_for_citizen else ""
        worker_info = f" (Работник: {comp.worker_name})" if comp.worker_name else " (Назначен: не назначен)"
        print(f"\nЖАЛОБА #{comp.id}{new_mark}")
        print(f"\tКатегория: {comp.category_name}")
        print(f"\tСтатус: {comp.status_name}{worker_info}")
        print(f"\tОрганизация: {comp.employer_name}")
        print(f"\tОписание: {comp.description[:200]}")
        print(f"\tДата: {comp.created_at}")
        if comp.file_path:
            print(f"\tФайл: {os.path.basename(comp.file_path)}")
            if ask_yes_no("\tОткрыть файл", default=False):
                open_file(comp.file_path)
        print("-" * 40)
    
    choice = input("\nВведите ID жалобы для просмотра переписки (или 0 для выхода): ").strip()
    if not choice.isdigit() or int(choice) == 0:
        return
    
    complaint_id = int(choice)
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM complaints WHERE id = ?", (complaint_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not row or row[0] != user_id:
        print("Жалоба не найдена или не принадлежит вам")
        return
    
    view_complaint_messages_citizen(user_id, complaint_id)

def view_complaint_messages_citizen(user_id, complaint_id):
    """Просмотр переписки по жалобе для гражданина"""
    display_complaint_messages(complaint_id, user_id)
    
    if ask_yes_no("\nНаписать сообщение", default=False):
        text = input("Введите текст сообщения: ").strip()
        if text:
            recipient_id = get_recipient_id_for_complaint(complaint_id, 'citizen', user_id)
            if recipient_id:
                send_message(complaint_id, user_id, recipient_id, text)
                print("Сообщение отправлено")
            else:
                print("Не удалось определить получателя")
        else:
            print("Сообщение не может быть пустым")

def view_my_archived_complaints(user_id):
    """Просмотр архивных жалоб"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            c.id, 
            cat.name AS category_name, 
            stat.name AS status_name, 
            c.employer_name, 
            c.description,
            c.file_path, 
            c.created_at,
            u_worker.first_name + ' ' + u_worker.last_name AS worker_name
        FROM complaints c
        JOIN complaint_categories cat ON c.category_id = cat.id
        JOIN complaint_statuses stat ON c.status_id = stat.id
        LEFT JOIN users u_worker ON c.assigned_to_id = u_worker.id
        WHERE c.user_id = ? AND c.is_archived = 1
        ORDER BY c.created_at DESC
    """, (user_id,))

    complaints = cursor.fetchall()
    cursor.close()
    conn.close()

    if not complaints:
        print("\nНет архивных жалоб")
        return

    print("\nМОИ АРХИВНЫЕ ЖАЛОБЫ")
    print("=" * 60)
    for comp in complaints:
        worker_info = f" (Работник: {comp.worker_name})" if comp.worker_name else ""
        print(f"\nЖАЛОБА #{comp.id}")
        print(f"\tКатегория: {comp.category_name}")
        print(f"\tСтатус: {comp.status_name}{worker_info}")
        print(f"\tОрганизация: {comp.employer_name}")
        print(f"\tДата: {comp.created_at}")
        if comp.file_path:
            print(f"\tФайл: {os.path.basename(comp.file_path)}")
            if ask_yes_no("\tОткрыть файл", default=False):
                open_file(comp.file_path)
        print("-" * 40)

def edit_complaint(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, employer_name, description, status_id
        FROM complaints
        WHERE user_id = ? AND is_archived = 0 AND status_id = 1
        ORDER BY created_at DESC
    """, (user_id,))

    complaints = cursor.fetchall()
    cursor.close()
    conn.close()

    if not complaints:
        print("\nНет жалоб в статусе 'Новая' для редактирования")
        return

    print("\nВАШИ ЖАЛОБЫ (статус 'Новая'):")
    for comp in complaints:
        print(f"\t#{comp.id}. {comp.employer_name[:50]}")

    while True:
        comp_id = input("\nВведите ID жалобы для редактирования: ").strip()
        if not comp_id.isdigit():
            print("Ошибка: введите число")
            continue
        comp_id = int(comp_id)
        break

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT employer_name, description, status_id, is_archived
        FROM complaints
        WHERE id = ? AND user_id = ?
    """, (comp_id, user_id))
    comp = cursor.fetchone()

    if not comp:
        print("Жалоба не найдена")
        cursor.close()
        conn.close()
        return

    if comp.is_archived == 1:
        print("Нельзя редактировать архивную жалобу")
        cursor.close()
        conn.close()
        return

    if comp.status_id != 1:
        print("Можно редактировать только жалобы в статусе 'Новая'")
        cursor.close()
        conn.close()
        return

    print(f"\nТекущая организация: {comp.employer_name}")
    new_employer = input("Новое название (Enter - без изменений): ").strip()
    if not new_employer:
        new_employer = comp.employer_name

    print(f"Текущее описание: {comp.description[:100]}")
    new_description = input("Новое описание (Enter - без изменений): ").strip()
    if not new_description:
        new_description = comp.description

    cursor.execute("""
        UPDATE complaints
        SET employer_name = ?, description = ?
        WHERE id = ? AND user_id = ? AND status_id = 1 AND is_archived = 0
    """, (new_employer, new_description, comp_id, user_id))
    conn.commit()

    cursor.close()
    conn.close()
    print(f"Жалоба #{comp_id} отредактирована")