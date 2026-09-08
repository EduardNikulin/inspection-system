import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auth import login, register
from citizen_actions import (
    submit_complaint, 
    view_my_complaints, 
    view_my_archived_complaints, 
    edit_complaint
)
from worker_actions import view_my_assigned_complaints
from admin_actions import (
    view_active_complaints,
    view_archived_complaints,
    view_all_complaints,
    search_complaints_by_citizen,
    manage_workers
)
from messenger import get_unread_count_for_user

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def register_user():
    clear_screen()
    print("\nРЕГИСТРАЦИЯ НОВОГО ПОЛЬЗОВАТЕЛЯ")
    print("-" * 40)
    
    login_input = input("Логин: ").strip()
    if not login_input:
        print("Логин обязателен")
        return False
    
    password = input("Пароль: ").strip()
    if not password:
        print("Пароль обязателен")
        return False
    
    first_name = input("Имя: ").strip()
    if not first_name:
        print("Имя обязательно")
        return False
    
    last_name = input("Фамилия: ").strip()
    if not last_name:
        print("Фамилия обязательна")
        return False
    
    success, message = register(login_input, password, first_name, last_name)
    print(message)
    return success

def citizen_menu(user_id, login):
    while True:
        clear_screen()
        
        unread_count = get_unread_count_for_user(user_id)
        unread_msg = f" [✉ {unread_count} новых]" if unread_count > 0 else ""
        
        print("\n" + "=" * 50)
        print(f"ГРАЖДАНИН: {login}{unread_msg}")
        print("=" * 50)
        print("1. Подать жалобу")
        print("2. Мои активные жалобы")
        print("3. Мои архивные жалобы")
        print("4. Редактировать жалобу")
        print("0. Выйти")
        print("-" * 50)

        choice = input("Выберите действие: ").strip()

        if choice == '1':
            submit_complaint(user_id)
            input("\nНажмите Enter для продолжения...")
        elif choice == '2':
            view_my_complaints(user_id)
            input("\nНажмите Enter для продолжения...")
        elif choice == '3':
            view_my_archived_complaints(user_id)
            input("\nНажмите Enter для продолжения...")
        elif choice == '4':
            edit_complaint(user_id)
            input("\nНажмите Enter для продолжения...")
        elif choice == '0':
            break
        else:
            print("Неверный выбор")
            input("\nНажмите Enter для продолжения...")

def worker_menu(user_id, login):
    while True:
        clear_screen()
        
        unread_count = get_unread_count_for_user(user_id)
        unread_msg = f" [✉ {unread_count} новых]" if unread_count > 0 else ""
        
        print("\n" + "=" * 50)
        print(f"РАБОТНИК: {login}{unread_msg}")
        print("=" * 50)
        print("1. Мои назначенные жалобы")
        print("0. Выйти")
        print("-" * 50)

        choice = input("Выберите действие: ").strip()

        if choice == '1':
            view_my_assigned_complaints(user_id)
            input("\nНажмите Enter для продолжения...")
        elif choice == '0':
            break
        else:
            print("Неверный выбор")
            input("\nНажмите Enter для продолжения...")

def admin_menu():
    while True:
        clear_screen()
        print("\n" + "=" * 50)
        print("АДМИНИСТРАТОР ТРУДОВОЙ ИНСПЕКЦИИ")
        print("=" * 50)
        print("ЖАЛОБЫ:")
        print("\t1. Активные жалобы")
        print("\t2. Архивные жалобы")
        print("\t3. Все жалобы")
        print("\t4. Поиск по гражданину")
        print("---")
        print("ПЕРСОНАЛ:")
        print("\t5. Управление работниками")
        print("---")
        print("\t0. Выйти")
        print("-" * 50)

        choice = input("Выберите действие: ").strip()

        if choice == '1':
            view_active_complaints()
        elif choice == '2':
            view_archived_complaints()
        elif choice == '3':
            view_all_complaints()
        elif choice == '4':
            search_complaints_by_citizen()
        elif choice == '5':
            manage_workers()
        elif choice == '0':
            break
        else:
            print("Неверный выбор")
            input("\nНажмите Enter для продолжения...")

def main():
    while True:
        clear_screen()
        print("\n" + "=" * 50)
        print("ТРУДОВАЯ ИНСПЕКЦИЯ - Система приёма жалоб")
        print("=" * 50)
        print("\n1. Вход")
        print("2. Регистрация")
        print("0. Выход")
        print("-" * 50)

        choice = input("Выберите действие: ").strip()

        if choice == '1':
            clear_screen()
            print("\nАВТОРИЗАЦИЯ")
            print("-" * 30)
            login_input = input("Логин: ").strip()
            password_input = input("Пароль: ").strip()

            user = login(login_input, password_input)

            if user:
                print(f"\nДобро пожаловать, {user['login']}!")
                input("\nНажмите Enter для продолжения...")
                if user['role'] == 'citizen':
                    citizen_menu(user['id'], user['login'])
                elif user['role'] == 'worker':
                    worker_menu(user['id'], user['login'])
                elif user['role'] == 'admin':
                    admin_menu()
            else:
                print("\nНеверный логин или пароль")
                input("\nНажмите Enter для продолжения...")
        elif choice == '2':
            register_user()
            input("\nНажмите Enter для продолжения...")
        elif choice == '0':
            break
        else:
            print("Неверный выбор")
            input("\nНажмите Enter для продолжения...")

    print("\nДо свидания!")

if __name__ == "__main__":
    main()