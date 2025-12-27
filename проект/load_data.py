#!/usr/bin/env python3
"""
Скрипт для загрузки данных в базу данных из CSV файлов
"""

import pandas as pd
import sqlite3
import os
from datetime import datetime
import numpy as np
import warnings

# Отключаем предупреждения о deprecated date adapter
warnings.filterwarnings('ignore', message='The default date adapter is deprecated')

def create_database(db_name="repair_service.db"):
    """Создание базы данных и таблиц"""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # Удаляем существующие таблицы (для чистого импорта)
    cursor.execute('DROP TABLE IF EXISTS comments')
    cursor.execute('DROP TABLE IF EXISTS requests')
    cursor.execute('DROP TABLE IF EXISTS users')
    conn.commit()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fio TEXT NOT NULL,
            phone TEXT NOT NULL,
            login TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица заявок
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_date DATE NOT NULL DEFAULT CURRENT_DATE,
            home_tech_type TEXT NOT NULL,
            home_tech_model TEXT NOT NULL,
            problem_description TEXT NOT NULL,
            request_status TEXT NOT NULL DEFAULT 'Новая заявка',
            completion_date DATE,
            repair_parts TEXT,
            master_id INTEGER,
            client_id INTEGER NOT NULL,
            FOREIGN KEY (master_id) REFERENCES users(user_id),
            FOREIGN KEY (client_id) REFERENCES users(user_id)
        )
    ''')
    
    # Таблица комментариев
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            master_id INTEGER NOT NULL,
            request_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (master_id) REFERENCES users(user_id),
            FOREIGN KEY (request_id) REFERENCES requests(request_id)
        )
    ''')
    
    # Создание индексов
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_requests_status ON requests(request_status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_requests_client ON requests(client_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_requests_master ON requests(master_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_comments_request ON comments(request_id)')
    
    conn.commit()
    conn.close()
    
    print(f"✓ База данных {db_name} создана успешно")
    return db_name

def clean_dataframe(df):
    """Очистка данных в DataFrame"""
    # Создаем копию DataFrame
    df = df.copy()
    
    # Замена NaN и 'null' на None
    df = df.replace({np.nan: None, 'null': None, 'None': None, '': None})
    
    # Для числовых колонок преобразуем в int, если возможно
    for col in df.columns:
        if 'ID' in col or 'id' in col.lower() or col.endswith('ID'):
            # Преобразуем в строку, затем в числовой формат
            df[col] = df[col].astype(str).str.strip()
            df[col] = pd.to_numeric(df[col], errors='coerce')
            # Преобразуем в целые числа, если нет NaN
            df[col] = df[col].apply(lambda x: int(x) if pd.notnull(x) else None)
    
    return df

def import_users_from_csv(file_path, db_name="repair_service.db"):
    """Импорт пользователей из CSV файла"""
    try:
        # Чтение CSV файла
        df = pd.read_csv(file_path, sep=';', encoding='utf-8')
        print(f"Найдено {len(df)} записей пользователей")
        
        # Очистка данных
        df = clean_dataframe(df)
        
        # Переименование колонок для единообразия
        df = df.rename(columns={
            'userID': 'user_id',
            'fio': 'fio',
            'phone': 'phone',
            'login': 'login',
            'password': 'password',
            'type': 'type'
        })
        
        # Подключение к базе данных
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        
        # Вставка данных
        inserted_count = 0
        skipped_count = 0
        
        for _, row in df.iterrows():
            try:
                # Проверяем, существует ли уже пользователь с таким ID
                cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (int(row['user_id']),))
                exists = cursor.fetchone()
                
                if exists:
                    # Обновляем существующего пользователя
                    cursor.execute('''
                        UPDATE users 
                        SET fio = ?, phone = ?, login = ?, password = ?, type = ?
                        WHERE user_id = ?
                    ''', (
                        str(row['fio']),
                        str(row['phone']),
                        str(row['login']),
                        str(row['password']),
                        str(row['type']),
                        int(row['user_id'])
                    ))
                    skipped_count += 1
                else:
                    # Вставляем нового пользователя
                    cursor.execute('''
                        INSERT INTO users (user_id, fio, phone, login, password, type)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        int(row['user_id']),
                        str(row['fio']),
                        str(row['phone']),
                        str(row['login']),
                        str(row['password']),
                        str(row['type'])
                    ))
                    inserted_count += 1
                    
            except Exception as e:
                print(f"  Ошибка при импорте пользователя ID {row.get('user_id', 'N/A')}: {e}")
                skipped_count += 1
        
        conn.commit()
        conn.close()
        
        print(f"✓ Пользователи импортированы: {inserted_count} новых, {skipped_count} обновлено/пропущено")
        return True
        
    except FileNotFoundError:
        print(f"✗ Файл {file_path} не найден")
        return False
    except Exception as e:
        print(f"✗ Ошибка при импорте пользователей: {e}")
        return False

def import_requests_from_csv(file_path, db_name="repair_service.db"):
    """Импорт заявок из CSV файла"""
    try:
        # Чтение CSV файла
        df = pd.read_csv(file_path, sep=';', encoding='utf-8')
        print(f"Найдено {len(df)} записей заявок")
        
        # Очистка данных
        df = clean_dataframe(df)
        
        # Переименование колонок
        df = df.rename(columns={
            'requestID': 'request_id',
            'startDate': 'start_date',
            'homeTechType': 'home_tech_type',
            'homeTechModel': 'home_tech_model',
            'problemDescryption': 'problem_description',
            'requestStatus': 'request_status',
            'completionDate': 'completion_date',
            'repairParts': 'repair_parts',
            'masterID': 'master_id',
            'clientID': 'client_id'
        })
        
        # Функция для безопасного преобразования дат
        def safe_date_conversion(date_str):
            if pd.isna(date_str) or date_str is None or str(date_str).strip() == '':
                return None
            try:
                return datetime.strptime(str(date_str).strip(), '%Y-%m-%d').date()
            except:
                return None
        
        # Преобразование дат
        df['start_date'] = df['start_date'].apply(safe_date_conversion)
        df['completion_date'] = df['completion_date'].apply(safe_date_conversion)
        
        # Подключение к базе данных
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        
        # Вставка данных
        inserted_count = 0
        skipped_count = 0
        
        for _, row in df.iterrows():
            try:
                # Проверяем, существует ли уже заявка с таким ID
                cursor.execute('SELECT request_id FROM requests WHERE request_id = ?', (int(row['request_id']),))
                exists = cursor.fetchone()
                
                # Получаем значения с проверкой на None
                master_id = int(row['master_id']) if pd.notnull(row['master_id']) else None
                client_id = int(row['client_id']) if pd.notnull(row['client_id']) else None
                
                if exists:
                    # Обновляем существующую заявку
                    cursor.execute('''
                        UPDATE requests 
                        SET start_date = ?, home_tech_type = ?, home_tech_model = ?, 
                            problem_description = ?, request_status = ?, completion_date = ?,
                            repair_parts = ?, master_id = ?, client_id = ?
                        WHERE request_id = ?
                    ''', (
                        row['start_date'],
                        str(row['home_tech_type']),
                        str(row['home_tech_model']),
                        str(row['problem_description']),
                        str(row['request_status']),
                        row['completion_date'],
                        str(row['repair_parts']) if pd.notnull(row['repair_parts']) else None,
                        master_id,
                        client_id,
                        int(row['request_id'])
                    ))
                    skipped_count += 1
                else:
                    # Вставляем новую заявку
                    cursor.execute('''
                        INSERT INTO requests 
                        (request_id, start_date, home_tech_type, home_tech_model, 
                         problem_description, request_status, completion_date, 
                         repair_parts, master_id, client_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        int(row['request_id']),
                        row['start_date'],
                        str(row['home_tech_type']),
                        str(row['home_tech_model']),
                        str(row['problem_description']),
                        str(row['request_status']),
                        row['completion_date'],
                        str(row['repair_parts']) if pd.notnull(row['repair_parts']) else None,
                        master_id,
                        client_id
                    ))
                    inserted_count += 1
                    
            except Exception as e:
                print(f"  Ошибка при импорте заявки ID {row.get('request_id', 'N/A')}: {e}")
                skipped_count += 1
        
        conn.commit()
        conn.close()
        
        print(f"✓ Заявки импортированы: {inserted_count} новых, {skipped_count} обновлено/пропущено")
        return True
        
    except FileNotFoundError:
        print(f"✗ Файл {file_path} не найден")
        return False
    except Exception as e:
        print(f"✗ Ошибка при импорте заявок: {e}")
        return False

def import_comments_from_csv(file_path, db_name="repair_service.db"):
    """Импорт комментариев из CSV файла"""
    try:
        # Чтение CSV файла
        df = pd.read_csv(file_path, sep=';', encoding='utf-8')
        print(f"Найдено {len(df)} записей комментариев")
        
        # Очистка данных
        df = clean_dataframe(df)
        
        # Переименование колонок
        df = df.rename(columns={
            'commentID': 'comment_id',
            'message': 'message',
            'masterID': 'master_id',
            'requestID': 'request_id'
        })
        
        # Проверяем существование заявок перед импортом комментариев
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT request_id FROM requests")
        existing_requests = {row[0] for row in cursor.fetchall()}
        conn.close()
        
        # Фильтруем комментарии только для существующих заявок
        valid_comments = []
        invalid_comments = []
        
        for _, row in df.iterrows():
            request_id = int(row['request_id']) if pd.notnull(row['request_id']) else None
            if request_id in existing_requests:
                valid_comments.append(row)
            else:
                invalid_comments.append(row['comment_id'])
        
        if invalid_comments:
            print(f"  Пропущено {len(invalid_comments)} комментариев (заявки не существуют): {invalid_comments}")
        
        # Подключение к базе данных для вставки
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        
        # Вставка данных
        inserted_count = 0
        skipped_count = 0
        
        for row in valid_comments:
            try:
                # Проверяем, существует ли уже комментарий с таким ID
                cursor.execute('SELECT comment_id FROM comments WHERE comment_id = ?', (int(row['comment_id']),))
                exists = cursor.fetchone()
                
                if exists:
                    # Обновляем существующий комментарий
                    cursor.execute('''
                        UPDATE comments 
                        SET message = ?, master_id = ?, request_id = ?
                        WHERE comment_id = ?
                    ''', (
                        str(row['message']),
                        int(row['master_id']),
                        int(row['request_id']),
                        int(row['comment_id'])
                    ))
                    skipped_count += 1
                else:
                    # Вставляем новый комментарий
                    cursor.execute('''
                        INSERT INTO comments (comment_id, message, master_id, request_id)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        int(row['comment_id']),
                        str(row['message']),
                        int(row['master_id']),
                        int(row['request_id'])
                    ))
                    inserted_count += 1
                    
            except Exception as e:
                print(f"  Ошибка при импорте комментария ID {row.get('comment_id', 'N/A')}: {e}")
                skipped_count += 1
        
        conn.commit()
        conn.close()
        
        print(f"✓ Комментарии импортированы: {inserted_count} новых, {skipped_count} обновлено/пропущено")
        return True
        
    except FileNotFoundError:
        print(f"✗ Файл {file_path} не найден")
        return False
    except Exception as e:
        print(f"✗ Ошибка при импорте комментариев: {e}")
        return False

def load_all_data(data_folder="import_data", db_name="repair_service.db"):
    """Загрузка всех данных из CSV файлов"""
    print("=" * 60)
    print("ЗАГРУЗКА ДАННЫХ В БАЗУ ДАННЫХ")
    print("=" * 60)
    
    # Создание базы данных, если не существует
    if not os.path.exists(db_name):
        print("База данных не найдена, создание новой...")
        create_database(db_name)
    else:
        print(f"База данных {db_name} уже существует, удаляю и создаю заново...")
        create_database(db_name)  # Это пересоздаст базу данных с чистыми таблицами
    
    # Пути к файлам
    users_file = os.path.join(data_folder, "InputDataUsers.csv")
    requests_file = os.path.join(data_folder, "InputDataRequests.csv")
    comments_file = os.path.join(data_folder, "InputDataComments.csv")
    
    # Проверка существования папки
    if not os.path.exists(data_folder):
        print(f"\nПапка {data_folder} не найдена. Создание папки...")
        os.makedirs(data_folder)
        print(f"✓ Папка {data_folder} создана")
        print("\nПожалуйста, поместите CSV файлы в папку import_data и запустите скрипт снова.")
        return False
    
    # Проверка существования файлов
    missing_files = []
    if not os.path.exists(users_file):
        missing_files.append("InputDataUsers.csv")
    if not os.path.exists(requests_file):
        missing_files.append("InputDataRequests.csv")
    if not os.path.exists(comments_file):
        missing_files.append("InputDataComments.csv")
    
    if missing_files:
        print(f"\n✗ Отсутствуют файлы: {', '.join(missing_files)}")
        print("Создаю примеры файлов...")
        create_sample_files(data_folder)
        print("\nТеперь файлы созданы. Пожалуйста, проверьте их и запустите скрипт снова.")
        return False
    
    print(f"\nПоиск файлов в папке {data_folder}...")
    
    # Загрузка данных в правильном порядке (сначала пользователи, потом заявки, потом комментарии)
    success_count = 0
    
    print(f"\n1. Загрузка пользователей из {users_file}")
    if import_users_from_csv(users_file, db_name):
        success_count += 1
    else:
        print("✗ Не удалось загрузить пользователей")
    
    print(f"\n2. Загрузка заявок из {requests_file}")
    if import_requests_from_csv(requests_file, db_name):
        success_count += 1
    else:
        print("✗ Не удалось загрузить заявки")
    
    print(f"\n3. Загрузка комментариев из {comments_file}")
    if import_comments_from_csv(comments_file, db_name):
        success_count += 1
    else:
        print("✗ Не удалось загрузить комментарии")
    
    # Сводка
    print("\n" + "=" * 60)
    print("ЗАГРУЗКА ДАННЫХ ЗАВЕРШЕНА")
    print("=" * 60)
    
    if success_count == 3:
        print("✓ Все файлы успешно загружены (3/3)")
        verify_database(db_name)
        return True
    elif success_count > 0:
        print(f"⚠ Частично успешно: {success_count}/3 файлов загружено")
        verify_database(db_name)
        return True
    else:
        print("✗ Загрузка не удалась: 0/3 файлов загружено")
        return False

def backup_database(db_name="repair_service.db"):
    """Создание резервной копии базы данных"""
    try:
        if not os.path.exists(db_name):
            print(f"✗ База данных {db_name} не найдена")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_folder = "backups"
        if not os.path.exists(backup_folder):
            os.makedirs(backup_folder)
        
        backup_name = os.path.join(backup_folder, f"backup_{timestamp}_{db_name}")
        
        # Простое копирование файла базы данных
        import shutil
        shutil.copy2(db_name, backup_name)
        
        # Получаем размер файла
        size = os.path.getsize(backup_name) / 1024  # Размер в КБ
        
        print(f"✓ Резервная копия создана: {backup_name} ({size:.1f} КБ)")
        return backup_name
    except Exception as e:
        print(f"✗ Ошибка при создании резервной копии: {e}")
        return None

def verify_database(db_name="repair_service.db"):
    """Проверка целостности базы данных"""
    try:
        if not os.path.exists(db_name):
            print(f"✗ База данных {db_name} не найдена")
            return False
        
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        
        print("\n" + "=" * 60)
        print("ПРОВЕРКА ЦЕЛОСТНОСТИ БАЗЫ ДАННЫХ")
        print("=" * 60)
        
        # Проверка таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        
        print(f"\nТаблицы в базе данных ({len(tables)}):")
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  - {table_name}: {count} записей")
        
        # Проверка внешних ключей
        cursor.execute("PRAGMA foreign_key_check")
        fk_errors = cursor.fetchall()
        
        if fk_errors:
            print(f"\n⚠ Найдены ошибки внешних ключей: {len(fk_errors)}")
            for error in fk_errors:
                print(f"  - Таблица: {error[0]}, строка: {error[1]}, таблица ссылки: {error[2]}, id: {error[3]}")
        else:
            print("\n✓ Внешние ключи в порядке")
        
        # Проверка индексов
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")
        indexes = cursor.fetchall()
        
        print(f"\nИндексы в базе данных ({len(indexes)}):")
        for index in indexes:
            print(f"  - {index[0]}")
        
        # Пример данных
        print("\nПример данных из таблиц:")
        
        print("\nПользователи (первые 3):")
        cursor.execute("SELECT user_id, fio, type FROM users LIMIT 3")
        for row in cursor.fetchall():
            print(f"  ID: {row[0]}, ФИО: {row[1]}, Роль: {row[2]}")
        
        print("\nЗаявки (первые 3):")
        cursor.execute("SELECT request_id, home_tech_type, request_status FROM requests LIMIT 3")
        for row in cursor.fetchall():
            print(f"  ID: {row[0]}, Техника: {row[1]}, Статус: {row[2]}")
        
        print("\nКомментарии (первые 3):")
        cursor.execute("SELECT comment_id, request_id, message FROM comments LIMIT 3")
        for row in cursor.fetchall():
            print(f"  ID: {row[0]}, Заявка: {row[1]}, Сообщение: {row[2][:30]}...")
        
        conn.close()
        print("\n✓ Проверка базы данных завершена успешно.")
        return True
    except Exception as e:
        print(f"✗ Ошибка при проверке базы данных: {e}")
        return False

def create_sample_files(data_folder="import_data"):
    """Создание примеров CSV файлов из данных в ТЗ"""
    if not os.path.exists(data_folder):
        os.makedirs(data_folder)
    
    # Данные пользователей из ТЗ
    users_data = """userID;fio;phone;login;password;type
1;Трубин Никита Юрьевич;89210563128;kasoo;root;Менеджер
2;Мурашов Андрей Юрьевич;89535078985;murashov123;qwerty;Мастер
3;Степанов Андрей Викторович;89210673849;test1;test1;Мастер
4;Перина Анастасия Денисовна;89990563748;perinaAD;250519;Оператор
5;Мажитова Ксения Сергеевна;89994563847;krutiha1234567;1234567890;Оператор
6;Семенова Ясмина Марковна;89994563847;login1;pass1;Мастер
7;Баранова Эмилия Марковна;89994563841;login2;pass2;Заказчик
8;Егорова Алиса Платоновна;89994563842;login3;pass3;Заказчик
9;Титов Максим Иванович;89994563843;login4;pass4;Заказчик
10;Иванов Марк Максимович;89994563844;login5;pass5;Мастер
"""
    
    # Данные заявок из ТЗ (убираем "null" из completionDate)
    requests_data = """requestID;startDate;homeTechType;homeTechModel;problemDescryption;requestStatus;completionDate;repairParts;masterID;clientID
1;2023-06-06;Фен;Ладомир ТА112 белый;Перестал работать;В процессе ремонта;;;2;7
2;2023-05-05;Тостер;Redmond RT-437 черный;Перестал работать;В процессе ремонта;;;3;7
3;2022-07-07;Холодильник;Indesit DS 316 W белый;Не морозит одна из камер холодильника;Готова к выдаче;2023-01-01;;2;8
4;2023-08-02;Стиральная машина;DEXP WM-F610NTMA/WW белый;Перестали работать многие режимы стирки;Новая заявка;;;8
5;2023-08-02;Мультиварка;Redmond RMC-M95 черный;Перестала включаться;Новая заявка;;;9
6;2023-08-02;Фен;Ладомир ТА113 чёрный;Перестал работать;Готова к выдаче;2023-08-03;;2;7
7;2023-07-09;Холодильник;Indesit DS 314 W серый;Гудит, но не замораживает;Готова к выдаче;2023-08-03;Мотор обдува морозильной камеры холодильника;2;8
"""
    
    # Данные комментариев из ТЗ
    comments_data = """commentID;message;masterID;requestID
1;Интересная поломка;2;1
2;Очень странно, будем разбираться!;3;2
3;Скорее всего потребуется мотор обдува!;2;7
4;Интересная проблема;2;1
5;Очень странно, будем разбираться!;3;6
"""
    
    # Сохранение файлов
    users_file = os.path.join(data_folder, "InputDataUsers.csv")
    requests_file = os.path.join(data_folder, "InputDataRequests.csv")
    comments_file = os.path.join(data_folder, "InputDataComments.csv")
    
    files_created = 0
    
    if not os.path.exists(users_file):
        with open(users_file, 'w', encoding='utf-8-sig') as f:
            f.write(users_data)
        print(f"✓ Создан файл: {users_file}")
        files_created += 1
    
    if not os.path.exists(requests_file):
        with open(requests_file, 'w', encoding='utf-8-sig') as f:
            f.write(requests_data)
        print(f"✓ Создан файл: {requests_file}")
        files_created += 1
    
    if not os.path.exists(comments_file):
        with open(comments_file, 'w', encoding='utf-8-sig') as f:
            f.write(comments_data)
        print(f"✓ Создан файл: {comments_file}")
        files_created += 1
    
    if files_created > 0:
        print(f"\n✓ Создано {files_created} примеров CSV файлов")
    else:
        print("\n✓ Все CSV файлы уже существуют")
    
    return files_created

if __name__ == "__main__":
    # Настройки
    DATA_FOLDER = "import_data"
    DB_NAME = "repair_service.db"
    
    print("=" * 60)
    print("СКРИПТ ЗАГРУЗКИ ДАННЫХ")
    print("Система учета заявок на ремонт бытовой техники")
    print("=" * 60)
    
    print("\nДоступные действия:")
    print("1. Создать новую базу данных и загрузить данные")
    print("2. Только загрузить данные из CSV файлов")
    print("3. Только создать примеры CSV файлов")
    print("4. Проверить целостность базы данных")
    print("5. Создать резервную копию базы данных")
    print("6. Выполнить все операции (создание + загрузка + проверка + резервная копия)")
    print("7. Выход")
    
    try:
        choice = input("\nВыберите действие (1-7): ").strip()
        
        if choice == "1":
            print("\n" + "=" * 60)
            print("СОЗДАНИЕ БАЗЫ ДАННЫХ И ЗАГРУЗКА ДАННЫХ")
            print("=" * 60)
            create_database(DB_NAME)
            create_sample_files(DATA_FOLDER)
            load_all_data(DATA_FOLDER, DB_NAME)
            
        elif choice == "2":
            print("\n" + "=" * 60)
            print("ЗАГРУЗКА ДАННЫХ ИЗ CSV ФАЙЛОВ")
            print("=" * 60)
            load_all_data(DATA_FOLDER, DB_NAME)
            
        elif choice == "3":
            print("\n" + "=" * 60)
            print("СОЗДАНИЕ ПРИМЕРОВ CSV ФАЙЛОВ")
            print("=" * 60)
            files_created = create_sample_files(DATA_FOLDER)
            if files_created > 0:
                print(f"\n✓ Готово! Создано {files_created} файлов в папке '{DATA_FOLDER}'")
            else:
                print("\n✓ Все файлы уже существуют")
            
        elif choice == "4":
            print("\n" + "=" * 60)
            print("ПРОВЕРКА ЦЕЛОСТНОСТИ БАЗЫ ДАННЫХ")
            print("=" * 60)
            verify_database(DB_NAME)
            
        elif choice == "5":
            print("\n" + "=" * 60)
            print("СОЗДАНИЕ РЕЗЕРВНОЙ КОПИИ БАЗЫ ДАННЫХ")
            print("=" * 60)
            backup_database(DB_NAME)
            
        elif choice == "6":
            print("\n" + "=" * 60)
            print("ВЫПОЛНЕНИЕ ВСЕХ ОПЕРАЦИЙ")
            print("=" * 60)
            create_database(DB_NAME)
            create_sample_files(DATA_FOLDER)
            load_all_data(DATA_FOLDER, DB_NAME)
            verify_database(DB_NAME)
            backup_database(DB_NAME)
            print("\n✓ Все операции выполнены успешно!")
            
        elif choice == "7":
            print("\nВыход из программы...")
            
        else:
            print("\n✗ Неверный выбор. Пожалуйста, выберите от 1 до 7.")
            
    except KeyboardInterrupt:
        print("\n\nПрограмма прервана пользователем.")
    except Exception as e:
        print(f"\n✗ Произошла ошибка: {e}")
    
    print("\n" + "=" * 60)
    print("РАБОТА ЗАВЕРШЕНА")
    print("=" * 60)