import sqlite3
import pandas as pd
from datetime import datetime
from typing import List, Optional, Dict, Any
import os

class Database:
    def __init__(self, db_name: str = "repair_service.db"):
        self.db_name = db_name
        self.init_database()
    
    def get_connection(self):
        return sqlite3.connect(self.db_name)
    
    def init_database(self):
        """Инициализация базы данных и создание таблиц"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
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
            
            # Создание индексов для ускорения поиска
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_requests_status ON requests(request_status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_requests_client ON requests(client_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_requests_master ON requests(master_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_comments_request ON comments(request_id)')
            
            conn.commit()
    
    def import_from_csv(self, folder_path: str = "import_data"):
        """Импорт данных из CSV файлов при старте сервера"""
        print("Загрузка данных из CSV файлов...")
        
        # Используем функции из load_data.py или свою логику
        try:
            # Удаляем существующие данные
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM comments')
                cursor.execute('DELETE FROM requests')
                cursor.execute('DELETE FROM users')
                conn.commit()
            
            # Загружаем пользователей
            users_file = os.path.join(folder_path, "InputDataUsers.csv")
            if os.path.exists(users_file):
                df_users = pd.read_csv(users_file, sep=';')
                with self.get_connection() as conn:
                    for _, row in df_users.iterrows():
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT OR REPLACE INTO users (user_id, fio, phone, login, password, type)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            int(row['userID']),
                            str(row['fio']),
                            str(row['phone']),
                            str(row['login']),
                            str(row['password']),
                            str(row['type'])
                        ))
                    conn.commit()
                print(f"✓ Загружено {len(df_users)} пользователей")
            
            # Загружаем заявки
            requests_file = os.path.join(folder_path, "InputDataRequests.csv")
            if os.path.exists(requests_file):
                df_requests = pd.read_csv(requests_file, sep=';')
                with self.get_connection() as conn:
                    for _, row in df_requests.iterrows():
                        cursor = conn.cursor()
                        
                        # Преобразуем даты
                        start_date = datetime.strptime(str(row['startDate']), '%Y-%m-%d').date()
                        
                        completion_date = None
                        if str(row['completionDate']) != 'null' and pd.notna(row['completionDate']):
                            try:
                                completion_date = datetime.strptime(str(row['completionDate']), '%Y-%m-%d').date()
                            except:
                                completion_date = None
                        
                        master_id = None
                        if str(row['masterID']) != 'null' and pd.notna(row['masterID']):
                            master_id = int(row['masterID'])
                        
                        cursor.execute('''
                            INSERT OR REPLACE INTO requests 
                            (request_id, start_date, home_tech_type, home_tech_model, 
                            problem_description, request_status, completion_date, 
                            repair_parts, master_id, client_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            int(row['requestID']),
                            start_date,
                            str(row['homeTechType']),
                            str(row['homeTechModel']),
                            str(row['problemDescryption']),
                            str(row['requestStatus']),
                            completion_date,
                            str(row['repairParts']) if str(row['repairParts']) != 'null' else None,
                            master_id,
                            int(row['clientID'])
                        ))
                    conn.commit()
                print(f"✓ Загружено {len(df_requests)} заявок")
            
            # Загружаем комментарии
            comments_file = os.path.join(folder_path, "InputDataComments.csv")
            if os.path.exists(comments_file):
                df_comments = pd.read_csv(comments_file, sep=';')
                with self.get_connection() as conn:
                    for _, row in df_comments.iterrows():
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT OR REPLACE INTO comments (comment_id, message, master_id, request_id)
                            VALUES (?, ?, ?, ?)
                        ''', (
                            int(row['commentID']),
                            str(row['message']),
                            int(row['masterID']),
                            int(row['requestID'])
                        ))
                    conn.commit()
                print(f"✓ Загружено {len(df_comments)} комментариев")
            
            print("✓ Данные успешно загружены")
            return True
            
        except Exception as e:
            print(f"✗ Ошибка при загрузке данных: {e}")
            return False
    
    def authenticate_user(self, login: str, password: str) -> Optional[Dict]:
        """Аутентификация пользователя"""
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id, fio, phone, login, type FROM users WHERE login = ? AND password = ?",
                (login, password)
            )
            user = cursor.fetchone()
            return dict(user) if user else None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Получение пользователя по ID"""
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, fio, phone, login, type FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()
            return dict(user) if user else None
    
    def create_user(self, user_data: Dict) -> int:
        """Создание нового пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (fio, phone, login, password, type)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                user_data['fio'],
                user_data['phone'],
                user_data['login'],
                user_data['password'],
                user_data['type']
            ))
            conn.commit()
            return cursor.lastrowid
    
    def create_request(self, request_data: Dict) -> int:
        """Создание новой заявки"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO requests 
                (home_tech_type, home_tech_model, problem_description, client_id, master_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                request_data['home_tech_type'],
                request_data['home_tech_model'],
                request_data['problem_description'],
                request_data['client_id'],
                request_data.get('master_id')
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_requests(self, filters: Dict = None) -> List[Dict]:
        """Получение списка заявок с фильтрами"""
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = '''
                SELECT r.*, 
                       c.fio as client_fio,
                       m.fio as master_fio
                FROM requests r
                LEFT JOIN users c ON r.client_id = c.user_id
                LEFT JOIN users m ON r.master_id = m.user_id
                WHERE 1=1
            '''
            params = []
            
            if filters:
                if filters.get('request_id'):
                    query += " AND r.request_id = ?"
                    params.append(filters['request_id'])
                if filters.get('client_id'):
                    query += " AND r.client_id = ?"
                    params.append(filters['client_id'])
                if filters.get('master_id'):
                    query += " AND r.master_id = ?"
                    params.append(filters['master_id'])
                if filters.get('status'):
                    query += " AND r.request_status = ?"
                    params.append(filters['status'])
                if filters.get('search'):
                    query += " AND (r.home_tech_type LIKE ? OR r.home_tech_model LIKE ? OR r.problem_description LIKE ?)"
                    search_term = f"%{filters['search']}%"
                    params.extend([search_term, search_term, search_term])
            
            query += " ORDER BY r.start_date DESC"
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def update_request(self, request_id: int, update_data: Dict) -> bool:
        """Обновление заявки"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            set_clause = []
            params = []
            
            for key, value in update_data.items():
                if value is not None:
                    set_clause.append(f"{key} = ?")
                    params.append(value)
            
            if not set_clause:
                return False
            
            params.append(request_id)
            query = f"UPDATE requests SET {', '.join(set_clause)} WHERE request_id = ?"
            
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
    
    def add_comment(self, comment_data: Dict) -> int:
        """Добавление комментария к заявке"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO comments (message, master_id, request_id)
                VALUES (?, ?, ?)
            ''', (
                comment_data['message'],
                comment_data['master_id'],
                comment_data['request_id']
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_comments(self, request_id: int) -> List[Dict]:
        """Получение комментариев к заявке"""
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT c.*, u.fio as master_fio
                FROM comments c
                JOIN users u ON c.master_id = u.user_id
                WHERE c.request_id = ?
                ORDER BY c.created_at DESC
            ''', (request_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_statistics(self) -> Dict:
        """Получение статистики"""
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Общее количество заявок
            cursor.execute("SELECT COUNT(*) as count FROM requests")
            total_requests = cursor.fetchone()['count']
            
            # Выполненные заявки
            cursor.execute("SELECT COUNT(*) as count FROM requests WHERE request_status = 'Готова к выдаче'")
            completed_requests = cursor.fetchone()['count']
            
            # Среднее время ремонта (в днях)
            cursor.execute('''
                SELECT AVG(julianday(completion_date) - julianday(start_date)) as avg_days
                FROM requests 
                WHERE completion_date IS NOT NULL
            ''')
            avg_result = cursor.fetchone()
            average_time = round(avg_result['avg_days'], 2) if avg_result['avg_days'] else None
            
            # Заявки по статусам
            cursor.execute('''
                SELECT request_status, COUNT(*) as count
                FROM requests
                GROUP BY request_status
            ''')
            status_stats = {row['request_status']: row['count'] for row in cursor.fetchall()}
            
            # Заявки по типам техники
            cursor.execute('''
                SELECT home_tech_type, COUNT(*) as count
                FROM requests
                GROUP BY home_tech_type
            ''')
            tech_stats = {row['home_tech_type']: row['count'] for row in cursor.fetchall()}
            
            return {
                'total_requests': total_requests,
                'completed_requests': completed_requests,
                'average_repair_time_days': average_time,
                'requests_by_status': status_stats,
                'requests_by_tech_type': tech_stats
            }
    
    def get_users_by_role(self, role: str) -> List[Dict]:
        """Получение пользователей по роли"""
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE type = ? ORDER BY fio", (role,))
            return [dict(row) for row in cursor.fetchall()]
         
    def update_user(self, user_id: int, update_data: Dict) -> bool:
        """Обновление данных пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            set_clause = []
            params = []
            
            for key, value in update_data.items():
                if value is not None:
                    set_clause.append(f"{key} = ?")
                    params.append(value)
            
            if not set_clause:
                return False
            
            params.append(user_id)
            query = f"UPDATE users SET {', '.join(set_clause)} WHERE user_id = ?"
            
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0

    def delete_user(self, user_id: int) -> bool:
        """Удаление пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            conn.commit()
            return cursor.rowcount > 0
        
    def get_all_users(self):
        """Получение всех пользователей"""
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, fio, phone, login, type FROM users ORDER BY fio")
            results = cursor.fetchall()
            return [dict(row) for row in results]
        
    def get_users_by_role(self, role: str) -> List[Dict]:
        """Получение пользователей по роли"""
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, fio, phone, login, type FROM users WHERE type = ? ORDER BY fio", (role,))
            results = cursor.fetchall()
            return [dict(row) for row in results]