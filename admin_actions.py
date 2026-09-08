from database import get_connection
from file_utils import open_file, delete_file
from messenger import display_complaint_messages, send_message, get_recipient_id_for_complaint
import os
import hashlib
from auth import hash_password

def ask_yes_no(prompt, default=False):
    if default:
        user_input = input(f"{prompt} (Да/нет): ").strip().lower()
        return user_input not in ['нет', 'no', 'n']
    else:
        user_input = input(f"{prompt} (да/Нет): ").strip().lower()
        return user_input in ['да', 'yes', 'y']

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_admin_id():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT TOP 1 id FROM users WHERE role = 'admin'")
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row else None

def print_complaint_short(comp):
    archived_mark = " [АРХИВ]" if comp.is_archived else ""
    new_mark = " [НОВЫЕ СООБЩЕНИЯ]" if comp.has_new_messages_for_admin else ""
    worker_name = comp.worker_name if comp.worker_name else "не назначен"
    print(f"\t#{comp.id}{archived_mark}{new_mark}")
    print(f"\t\tГражданин: {comp.citizen_name}")
    print(f"\t\tРаботник: {worker_name}")
    print(f"\t\tСтатус: {comp.status_name}")
    print(f"\t\tОрганизация: {comp.employer_name}")
    print(f"\t\tДата: {comp.created_at}")

def print_complaint_full(comp):
    archived_mark = " [АРХИВ]" if comp.is_archived else ""
    new_mark = " [НОВЫЕ СООБЩЕНИЯ]" if comp.has_new_messages_for_admin else ""
    worker_name = comp.worker_name if comp.worker_name else "не назначен"
    print(f"\n=== ЖАЛОБА #{comp.id}{archived_mark}{new_mark} ===")
    print(f"Гражданин: {comp.citizen_name}")
    print(f"Работник: {worker_name}")
    print(f"Категория: {comp.category_name}")
    print(f"Статус: {comp.status_name}")
    print(f"Организация: {comp.employer_name}")
    print(f"Описание: {comp.description}")
    if comp.file_path:
        print(f"Файл: {os.path.basename(comp.file_path)}")
    print(f"Дата: {comp.created_at}")
    print("-" * 40)

# -------------------- УПРАВЛЕНИЕ ЖАЛОБОЙ --------------------

def manage_complaint(complaint_id):
    admin_id = get_admin_id()
    if not admin_id:
        print("Администратор не найден")
        return
    
    while True:
        clear_screen()
        print(f"\nУПРАВЛЕНИЕ ЖАЛОБОЙ #{complaint_id}")
        print("=" * 50)
        print("1. Просмотр жалобы")
        print("2. Изменить статус")
        print("3. Назначить работника")
        print("4. Переписка (просмотр и ответ)")
        print("5. Открыть файл")
        print("6. Удалить жалобу")
        print("0. Вернуться к списку")
        print("-" * 50)
        
        choice = input("Выберите действие: ").strip()
        
        if choice == '1':
            view_complaint_details(complaint_id)
        elif choice == '2':
            change_complaint_status_by_id(complaint_id)
        elif choice == '3':
            assign_worker_to_complaint(complaint_id)
        elif choice == '4':
            view_complaint_messages_admin(complaint_id)
        elif choice == '5':
            open_complaint_file(complaint_id)
        elif choice == '6':
            if ask_yes_no("Вы уверены, что хотите удалить жалобу?", default=False):
                delete_complaint_by_id(complaint_id)
                print("Жалоба удалена")
                input("\nНажмите Enter для продолжения...")
                return
        elif choice == '0':
            return
        else:
            print("Неверный выбор")
            input("\nНажмите Enter для продолжения...")

def view_complaint_details(complaint_id):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            c.id,
            u_citizen.first_name + ' ' + u_citizen.last_name AS citizen_name,
            u_worker.first_name + ' ' + u_worker.last_name AS worker_name,
            cat.name AS category_name,
            stat.name AS status_name,
            c.employer_name,
            c.description,
            c.file_path,
            c.created_at,
            c.is_archived,
            cw.has_new_messages_for_admin
        FROM complaints c
        JOIN users u_citizen ON c.user_id = u_citizen.id
        LEFT JOIN users u_worker ON c.assigned_to_id = u_worker.id
        JOIN complaint_categories cat ON c.category_id = cat.id
        JOIN complaint_statuses stat ON c.status_id = stat.id
        JOIN complaints_with_new_messages cw ON c.id = cw.id
        WHERE c.id = ?
    """, (complaint_id,))
    
    comp = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not comp:
        print("Жалоба не найдена")
        return
    
    print_complaint_full(comp)
    input("\nНажмите Enter для продолжения...")

def open_complaint_file(complaint_id):
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

def change_complaint_status_by_id(complaint_id):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT is_archived, status_id FROM complaints WHERE id = ?", (complaint_id,))
    row = cursor.fetchone()
    
    if not row:
        print("Жалоба не найдена")
        cursor.close()
        conn.close()
        return
    
    if row.is_archived == 1:
        print("Нельзя изменить статус архивной жалобы")
        cursor.close()
        conn.close()
        return
    
    current_status = row.status_id
    status_names = {1: 'Новая', 2: 'В работе', 3: 'Закрыта'}
    print(f"\nТекущий статус: {status_names.get(current_status, 'Неизвестен')}")
    print("\nНовый статус:")
    print("\t1. Новая")
    print("\t2. В работе")
    print("\t3. Закрыта")
    
    while True:
        new_status = input("Выберите статус (1-3): ").strip()
        if new_status in ['1', '2', '3']:
            break
        print("Введите 1, 2 или 3")
    
    if int(new_status) == current_status:
        print("Статус не изменился")
        cursor.close()
        conn.close()
        return
    
    cursor.execute("UPDATE complaints SET status_id = ? WHERE id = ?", (int(new_status), complaint_id))
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"Статус жалобы #{complaint_id} изменён на '{status_names.get(int(new_status))}'")
    input("\nНажмите Enter для продолжения...")

def assign_worker_to_complaint(complaint_id):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT is_archived, assigned_to_id FROM complaints WHERE id = ?", (complaint_id,))
    row = cursor.fetchone()
    if not row:
        print("Жалоба не найдена")
        cursor.close()
        conn.close()
        return
    
    if row.is_archived == 1:
        print("Нельзя назначить работника на архивную жалобу")
        cursor.close()
        conn.close()
        return
    
    current_assigned = row.assigned_to_id
    if current_assigned:
        cursor.execute("SELECT first_name + ' ' + last_name FROM users WHERE id = ?", (current_assigned,))
        name_row = cursor.fetchone()
        print(f"Текущий работник: {name_row[0] if name_row else 'неизвестен'}")
    else:
        print("Текущий работник: не назначен")
    
    cursor.execute("""
        SELECT id, first_name + ' ' + last_name AS full_name, login
        FROM users 
        WHERE role = 'worker'
        ORDER BY first_name
    """)
    workers = cursor.fetchall()
    
    if not workers:
        print("\nНет доступных работников. Сначала добавьте работника через 'Управление персоналом'.")
        cursor.close()
        conn.close()
        return
    
    print("\nДоступные работники:")
    for w in workers:
        print(f"\t{w.id}. {w.full_name} ({w.login})")
    
    while True:
        worker_id = input("\nВведите ID работника (или 0 для отмены): ").strip()
        if not worker_id.isdigit():
            print("Введите число")
            continue
        worker_id = int(worker_id)
        if worker_id == 0:
            cursor.close()
            conn.close()
            return
        if any(w.id == worker_id for w in workers):
            break
        print("Работник не найден")
    
    cursor.execute("""
        UPDATE complaints 
        SET assigned_to_id = ?, status_id = 2
        WHERE id = ?
    """, (worker_id, complaint_id))
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"Работник назначен на жалобу #{complaint_id}, статус изменён на 'В работе'")
    input("\nНажмите Enter для продолжения...")

def view_complaint_messages_admin(complaint_id):
    admin_id = get_admin_id()
    if not admin_id:
        print("Администратор не найден")
        return
    
    display_complaint_messages(complaint_id, admin_id)
    
    if ask_yes_no("\nНаписать сообщение", default=False):
        text = input("Введите текст сообщения: ").strip()
        if text:
            recipient_id = get_recipient_id_for_complaint(complaint_id, 'admin', admin_id)
            if recipient_id:
                send_message(complaint_id, admin_id, recipient_id, text)
                print("Сообщение отправлено")
            else:
                print("Не удалось определить получателя")
        else:
            print("Сообщение не может быть пустым")
    input("\nНажмите Enter для продолжения...")

def delete_complaint_by_id(complaint_id):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Удаляем сообщения (на случай, если нет каскадного удаления)
    cursor.execute("DELETE FROM messages WHERE complaint_id = ?", (complaint_id,))
    
    cursor.execute("SELECT file_path FROM complaints WHERE id = ?", (complaint_id,))
    row = cursor.fetchone()
    if row and row.file_path:
        delete_file(row.file_path)
    
    cursor.execute("DELETE FROM complaints WHERE id = ?", (complaint_id,))
    conn.commit()
    cursor.close()
    conn.close()

# -------------------- ПРОСМОТР ЖАЛОБ --------------------

def view_all_complaints():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            c.id,
            u_citizen.first_name + ' ' + u_citizen.last_name AS citizen_name,
            u_worker.first_name + ' ' + u_worker.last_name AS worker_name,
            cat.name AS category_name,
            stat.name AS status_name,
            c.employer_name,
            c.description,
            c.file_path,
            c.created_at,
            c.is_archived,
            cw.has_new_messages_for_admin
        FROM complaints c
        JOIN users u_citizen ON c.user_id = u_citizen.id
        LEFT JOIN users u_worker ON c.assigned_to_id = u_worker.id
        JOIN complaint_categories cat ON c.category_id = cat.id
        JOIN complaint_statuses stat ON c.status_id = stat.id
        JOIN complaints_with_new_messages cw ON c.id = cw.id
        ORDER BY c.is_archived, c.created_at DESC
    """)
    
    complaints = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not complaints:
        print("\nЖалоб нет")
        return
    
    print("\nВСЕ ЖАЛОБЫ")
    print("=" * 60)
    for comp in complaints:
        print_complaint_short(comp)
        print("-" * 40)
    
    choice = input("\nВведите ID жалобы для работы (или 0 для выхода): ").strip()
    if not choice.isdigit() or int(choice) == 0:
        return
    
    manage_complaint(int(choice))

def view_active_complaints():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            c.id,
            u_citizen.first_name + ' ' + u_citizen.last_name AS citizen_name,
            u_worker.first_name + ' ' + u_worker.last_name AS worker_name,
            cat.name AS category_name,
            stat.name AS status_name,
            c.employer_name,
            c.description,
            c.file_path,
            c.created_at,
            cw.has_new_messages_for_admin
        FROM complaints c
        JOIN users u_citizen ON c.user_id = u_citizen.id
        LEFT JOIN users u_worker ON c.assigned_to_id = u_worker.id
        JOIN complaint_categories cat ON c.category_id = cat.id
        JOIN complaint_statuses stat ON c.status_id = stat.id
        JOIN complaints_with_new_messages cw ON c.id = cw.id
        WHERE c.is_archived = 0
        ORDER BY c.created_at DESC
    """)
    
    complaints = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not complaints:
        print("\nАктивных жалоб нет")
        return
    
    print("\nАКТИВНЫЕ ЖАЛОБЫ")
    print("=" * 60)
    for comp in complaints:
        new_mark = " [НОВЫЕ СООБЩЕНИЯ]" if comp.has_new_messages_for_admin else ""
        worker_name = comp.worker_name if comp.worker_name else "не назначен"
        print(f"\t#{comp.id}{new_mark}")
        print(f"\t\tГражданин: {comp.citizen_name}")
        print(f"\t\tРаботник: {worker_name}")
        print(f"\t\tСтатус: {comp.status_name}")
        print(f"\t\tОрганизация: {comp.employer_name}")
        print(f"\t\tДата: {comp.created_at}")
        print("-" * 40)
    
    choice = input("\nВведите ID жалобы для работы (или 0 для выхода): ").strip()
    if choice.isdigit() and int(choice) > 0:
        manage_complaint(int(choice))

def view_archived_complaints():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            c.id,
            u_citizen.first_name + ' ' + u_citizen.last_name AS citizen_name,
            u_worker.first_name + ' ' + u_worker.last_name AS worker_name,
            cat.name AS category_name,
            stat.name AS status_name,
            c.employer_name,
            c.description,
            c.file_path,
            c.created_at
        FROM complaints c
        JOIN users u_citizen ON c.user_id = u_citizen.id
        LEFT JOIN users u_worker ON c.assigned_to_id = u_worker.id
        JOIN complaint_categories cat ON c.category_id = cat.id
        JOIN complaint_statuses stat ON c.status_id = stat.id
        WHERE c.is_archived = 1
        ORDER BY c.created_at DESC
    """)
    
    complaints = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not complaints:
        print("\nАрхив пуст")
        return
    
    print("\nАРХИВНЫЕ ЖАЛОБЫ")
    print("=" * 60)
    for comp in complaints:
        worker_name = comp.worker_name if comp.worker_name else "не назначен"
        print(f"\t#{comp.id} [АРХИВ]")
        print(f"\t\tГражданин: {comp.citizen_name}")
        print(f"\t\tРаботник: {worker_name}")
        print(f"\t\tСтатус: {comp.status_name}")
        print(f"\t\tОрганизация: {comp.employer_name}")
        print(f"\t\tДата: {comp.created_at}")
        if comp.file_path:
            print(f"\t\tФайл: {os.path.basename(comp.file_path)}")
        print("-" * 40)

def search_complaints_by_citizen():
    print("\nПОИСК ЖАЛОБ ПО ГРАЖДАНИНУ")
    print("-" * 40)
    
    search_name = input("Введите часть имени или фамилии: ").strip()
    if not search_name:
        print("Пустой поисковый запрос")
        return
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            c.id,
            u_citizen.first_name + ' ' + u_citizen.last_name AS citizen_name,
            u_worker.first_name + ' ' + u_worker.last_name AS worker_name,
            cat.name AS category_name,
            stat.name AS status_name,
            c.employer_name,
            c.description,
            c.created_at,
            c.is_archived,
            cw.has_new_messages_for_admin
        FROM complaints c
        JOIN users u_citizen ON c.user_id = u_citizen.id
        LEFT JOIN users u_worker ON c.assigned_to_id = u_worker.id
        JOIN complaint_categories cat ON c.category_id = cat.id
        JOIN complaint_statuses stat ON c.status_id = stat.id
        JOIN complaints_with_new_messages cw ON c.id = cw.id
        WHERE u_citizen.first_name LIKE ? OR u_citizen.last_name LIKE ?
        ORDER BY c.created_at DESC
    """, (f'%{search_name}%', f'%{search_name}%'))
    
    complaints = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not complaints:
        print(f"\nЖалоб от граждан с именем/фамилией '{search_name}' не найдено")
        input("\nНажмите Enter для продолжения...")
        return
    
    print(f"\nРЕЗУЛЬТАТЫ ПОИСКА: {search_name}")
    print("=" * 60)
    for comp in complaints:
        mark = " [АРХИВ]" if comp.is_archived else ""
        new_mark = " [НОВЫЕ СООБЩЕНИЯ]" if comp.has_new_messages_for_admin else ""
        worker_name = comp.worker_name if comp.worker_name else "не назначен"
        print(f"\nЖАЛОБА #{comp.id}{mark}{new_mark}")
        print(f"\tГражданин: {comp.citizen_name}")
        print(f"\tРаботник: {worker_name}")
        print(f"\tКатегория: {comp.category_name}")
        print(f"\tСтатус: {comp.status_name}")
        print(f"\tОрганизация: {comp.employer_name}")
        print(f"\tДата: {comp.created_at}")
        print("-" * 40)
    
    choice = input("\nВведите ID жалобы для работы (или 0 для выхода): ").strip()
    if choice.isdigit() and int(choice) > 0:
        manage_complaint(int(choice))

# -------------------- УПРАВЛЕНИЕ ПЕРСОНАЛОМ --------------------

def manage_workers():
    while True:
        clear_screen()
        print("\nУПРАВЛЕНИЕ ПЕРСОНАЛОМ")
        print("=" * 50)
        print("1. Список работников")
        print("2. Добавить работника")
        print("3. Редактировать работника")
        print("4. Удалить работника")
        print("5. Сменить пароль работника")
        print("0. Вернуться в главное меню")
        print("-" * 50)
        
        choice = input("Выберите действие: ").strip()
        
        if choice == '1':
            list_workers()
        elif choice == '2':
            add_worker()
        elif choice == '3':
            edit_worker()
        elif choice == '4':
            delete_worker()
        elif choice == '5':
            change_worker_password()
        elif choice == '0':
            return
        else:
            print("Неверный выбор")
            input("\nНажмите Enter для продолжения...")

def list_workers():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, login, first_name, last_name,
               (SELECT COUNT(*) FROM complaints WHERE assigned_to_id = users.id) AS assigned_count
        FROM users
        WHERE role = 'worker'
        ORDER BY first_name
    """)
    workers = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not workers:
        print("\nРаботников нет")
        input("\nНажмите Enter для продолжения...")
        return
    
    print("\nСПИСОК РАБОТНИКОВ")
    print("=" * 50)
    for w in workers:
        print(f"ID: {w.id}")
        print(f"Логин: {w.login}")
        print(f"ФИО: {w.first_name} {w.last_name}")
        print(f"Жалоб в работе: {w.assigned_count}")
        print("-" * 30)
    input("\nНажмите Enter для продолжения...")

def add_worker():
    conn = get_connection()
    cursor = conn.cursor()
    
    print("\nДОБАВЛЕНИЕ РАБОТНИКА")
    print("-" * 40)
    
    last_name = input("Фамилия (будет использована как логин): ").strip()
    if not last_name:
        print("Фамилия обязательна")
        return
    
    first_name = input("Имя: ").strip()
    if not first_name:
        print("Имя обязательно")
        return
    
    # Очищаем логин от пробелов и спецсимволов
    login = last_name.lower().replace(' ', '_').replace('-', '_')
    
    cursor.execute("SELECT id FROM users WHERE login = ?", (login,))
    if cursor.fetchone():
        print(f"Ошибка: работник с логином '{login}' уже существует")
        cursor.close()
        conn.close()
        return
    
    password_hash = hash_password('123')  # 123- это пароль для нового созданного работника.
    
    cursor.execute("""
        INSERT INTO users (login, password_hash, role, first_name, last_name)
        VALUES (?, ?, 'worker', ?, ?)
    """, (login, password_hash, first_name, last_name))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    print(f"Работник добавлен!")
    print(f"Логин: {login}")
    print(f"Пароль: 123")
    input("\nНажмите Enter для продолжения...")

def edit_worker():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, first_name, last_name, login
        FROM users
        WHERE role = 'worker'
        ORDER BY first_name
    """)
    workers = cursor.fetchall()
    
    if not workers:
        print("\nНет работников для редактирования")
        cursor.close()
        conn.close()
        input("\nНажмите Enter для продолжения...")
        return
    
    print("\nВЫБЕРИТЕ РАБОТНИКА ДЛЯ РЕДАКТИРОВАНИЯ")
    print("-" * 40)
    for w in workers:
        print(f"ID: {w.id} | {w.first_name} {w.last_name} ({w.login})")
    
    while True:
        worker_id = input("\nВведите ID работника (или 0 для отмены): ").strip()
        if not worker_id.isdigit():
            print("Введите число")
            continue
        worker_id = int(worker_id)
        if worker_id == 0:
            cursor.close()
            conn.close()
            return
        if any(w.id == worker_id for w in workers):
            break
        print("Работник не найден")
    
    cursor.execute("""
        SELECT first_name, last_name, login
        FROM users
        WHERE id = ? AND role = 'worker'
    """, (worker_id,))
    worker = cursor.fetchone()
    
    if not worker:
        print("Работник не найден")
        cursor.close()
        conn.close()
        return
    
    print("\nТЕКУЩИЕ ДАННЫЕ")
    print("-" * 40)
    print(f"Имя: {worker.first_name}")
    print(f"Фамилия: {worker.last_name}")
    print(f"Логин: {worker.login}")
    print("-" * 40)
    
    print("\nВведите новые данные (Enter - оставить без изменений)")
    
    new_first_name = input(f"Имя [{worker.first_name}]: ").strip()
    if not new_first_name:
        new_first_name = worker.first_name
    
    new_last_name = input(f"Фамилия [{worker.last_name}]: ").strip()
    if not new_last_name:
        new_last_name = worker.last_name
    
    new_login = input(f"Логин [{worker.login}]: ").strip()
    if not new_login:
        new_login = worker.login
    
    # Очищаем логин
    new_login = new_login.lower().replace(' ', '_').replace('-', '_')
    
    if new_login != worker.login:
        cursor.execute("SELECT id FROM users WHERE login = ? AND id != ?", (new_login, worker_id))
        if cursor.fetchone():
            print(f"Ошибка: логин '{new_login}' уже занят другим пользователем")
            cursor.close()
            conn.close()
            input("\nНажмите Enter для продолжения...")
            return
    
    change_password = ask_yes_no("\nСменить пароль?", default=False)
    new_password = None
    if change_password:
        new_password = input("Введите новый пароль: ").strip()
        if not new_password:
            print("Пароль не может быть пустым. Оставляем старый.")
            change_password = False
    
    cursor.execute("""
        UPDATE users
        SET first_name = ?, last_name = ?, login = ?
        WHERE id = ? AND role = 'worker'
    """, (new_first_name, new_last_name, new_login, worker_id))
    
    if change_password and new_password:
        password_hash = hashlib.sha256(new_password.encode()).hexdigest()
        cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, worker_id))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("\nДанные работника обновлены")
    print(f"Имя: {new_first_name}")
    print(f"Фамилия: {new_last_name}")
    print(f"Логин: {new_login}")
    if change_password:
        print(f"Пароль: {new_password}")
    input("\nНажмите Enter для продолжения...")

def delete_worker():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, first_name, last_name, login,
               (SELECT COUNT(*) FROM complaints WHERE assigned_to_id = users.id) AS assigned_count
        FROM users
        WHERE role = 'worker'
        ORDER BY first_name
    """)
    workers = cursor.fetchall()
    
    if not workers:
        print("\nНет работников для удаления")
        cursor.close()
        conn.close()
        input("\nНажмите Enter для продолжения...")
        return
    
    print("\nВЫБЕРИТЕ РАБОТНИКА ДЛЯ УДАЛЕНИЯ")
    print("-" * 40)
    for w in workers:
        print(f"ID: {w.id} | {w.first_name} {w.last_name} ({w.login}) | Жалоб: {w.assigned_count}")
    
    while True:
        worker_id = input("\nВведите ID работника (или 0 для отмены): ").strip()
        if not worker_id.isdigit():
            print("Введите число")
            continue
        worker_id = int(worker_id)
        if worker_id == 0:
            cursor.close()
            conn.close()
            return
        if any(w.id == worker_id for w in workers):
            break
        print("Работник не найден")
    
    cursor.execute("SELECT COUNT(*) FROM complaints WHERE assigned_to_id = ?", (worker_id,))
    count = cursor.fetchone()[0]
    
    if count > 0:
        print(f"У этого работника назначено {count} жалоб(а). Удалите назначения перед удалением.")
        cursor.close()
        conn.close()
        input("\nНажмите Enter для продолжения...")
        return
    
    cursor.execute("DELETE FROM users WHERE id = ? AND role = 'worker'", (worker_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    print("Работник удалён")
    input("\nНажмите Enter для продолжения...")

def change_worker_password():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, first_name, last_name, login
        FROM users
        WHERE role = 'worker'
        ORDER BY first_name
    """)
    workers = cursor.fetchall()
    
    if not workers:
        print("\nНет работников")
        cursor.close()
        conn.close()
        input("\nНажмите Enter для продолжения...")
        return
    
    print("\nВЫБЕРИТЕ РАБОТНИКА ДЛЯ СМЕНЫ ПАРОЛЯ")
    print("-" * 40)
    for w in workers:
        print(f"ID: {w.id} | {w.first_name} {w.last_name} ({w.login})")
    
    while True:
        worker_id = input("\nВведите ID работника (или 0 для отмены): ").strip()
        if not worker_id.isdigit():
            print("Введите число")
            continue
        worker_id = int(worker_id)
        if worker_id == 0:
            cursor.close()
            conn.close()
            return
        if any(w.id == worker_id for w in workers):
            break
        print("Работник не найден")
    
    new_password = input("Введите новый пароль (Enter для '123'): ").strip()
    if not new_password:
        new_password = '123'
    
    password_hash = hashlib.sha256(new_password.encode()).hexdigest()
    
    cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, worker_id))
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"Пароль изменён на '{new_password}'")
    input("\nНажмите Enter для продолжения...")