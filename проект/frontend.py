import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date
import qrcode
from PIL import Image
import io
import time

# Настройки страницы
st.set_page_config(
    page_title="Учет заявок на ремонт бытовой техники",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Стили CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #3B82F6;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .status-new { background-color: #FEF3C7; color: #92400E; padding: 5px 10px; border-radius: 5px; }
    .status-in-progress { background-color: #DBEAFE; color: #1E40AF; padding: 5px 10px; border-radius: 5px; }
    .status-ready { background-color: #D1FAE5; color: #065F46; padding: 5px 10px; border-radius: 5px; }
    .status-waiting { background-color: #F3F4F6; color: #374151; padding: 5px 10px; border-radius: 5px; }
    .stButton > button {
        width: 100%;
        margin-top: 10px;
    }
    .role-badge {
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .role-manager { background-color: #FBBF24; color: #78350F; }
    .role-master { background-color: #60A5FA; color: #1E3A8A; }
    .role-operator { background-color: #34D399; color: #065F46; }
    .role-client { background-color: #A78BFA; color: #5B21B6; }
    .role-quality { background-color: #F87171; color: #7F1D1D; }
    .no-requests {
        text-align: center;
        padding: 40px;
        background-color: #F3F4F6;
        border-radius: 10px;
        margin: 20px 0;
    }
</style>
""", unsafe_allow_html=True)

# API URL
API_URL = "http://localhost:8000"

class RepairServiceApp:
    def __init__(self):
        self.session = requests.Session()
        self.current_user = None
    
    def login(self, login, password):
        """Аутентификация пользователя"""
        try:
            response = self.session.post(
                f"{API_URL}/auth/login",
                json={"login": login, "password": password}
            )
            if response.status_code == 200:
                self.current_user = response.json()
                st.session_state['user'] = self.current_user
                st.success(f"Добро пожаловать, {self.current_user['fio']}!")
                return True
            else:
                st.error("Неверный логин или пароль")
                return False
        except requests.exceptions.ConnectionError:
            st.error("Не удалось подключиться к серверу. Убедитесь, что сервер запущен.")
            return False
    
    def logout(self):
        """Выход из системы"""
        self.current_user = None
        st.session_state.clear()
        st.success("Вы успешно вышли из системы")
    
    def get_requests(self, filters=None):
        """Получение списка заявок"""
        try:
            params = filters or {}
            response = self.session.get(f"{API_URL}/requests/", params=params)
            if response.status_code == 200:
                return response.json()
            return []
        except:
            return []
    
    def create_request(self, request_data):
        """Создание новой заявки"""
        response = self.session.post(f"{API_URL}/requests/", json=request_data)
        return response
    
    def update_request(self, request_id, update_data):
        """Обновление заявки"""
        response = self.session.put(f"{API_URL}/requests/{request_id}", json=update_data)
        return response
    
    def add_comment(self, request_id, message):
        """Добавление комментария"""
        if not self.current_user:
            return None
        
        # Проверяем, может ли пользователь добавлять комментарии
        if not self.can_add_comments():
            st.warning("У вас нет прав для добавления комментариев")
            return None
        
        try:
            comment_data = {
                "message": message,
                "request_id": int(request_id),
                "master_id": int(self.current_user['user_id'])
            }
            
            response = self.session.post(
                f"{API_URL}/comments/",
                json=comment_data
            )
            
            return response
        except Exception as e:
            print(f"Ошибка при добавлении комментария: {e}")
            return None
    
    def get_comments(self, request_id):
        """Получение комментариев к заявке"""
        response = self.session.get(f"{API_URL}/comments/{request_id}")
        if response.status_code == 200:
            return response.json()
        return []
    
    def get_statistics(self):
        """Получение статистики"""
        response = self.session.get(f"{API_URL}/statistics/")
        if response.status_code == 200:
            return response.json()
        return None
    
    def get_users_by_role(self, role):
        """Получение пользователей по роли"""
        response = self.session.get(f"{API_URL}/users/role/{role}")
        if response.status_code == 200:
            return response.json()
        return []
    
    def create_user(self, user_data):
        """Создание пользователя"""
        response = self.session.post(f"{API_URL}/users/", json=user_data)
        return response
    
    def get_all_users(self):
        """Получение всех пользователей"""
        try:
            response = self.session.get(f"{API_URL}/users/")
            if response.status_code == 200:
                return response.json()
            return []
        except:
            return []
    
    def update_user(self, user_id, update_data):
        """Обновление пользователя"""
        response = self.session.put(f"{API_URL}/users/{user_id}", json=update_data)
        return response
    
    def delete_user(self, user_id):
        """Удаление пользователя"""
        response = self.session.delete(f"{API_URL}/users/{user_id}")
        return response
    
    # Методы проверки прав
    def can_create_request(self):
        """Может ли пользователь создавать заявки"""
        if not self.current_user:
            return False
        return self.current_user['type'] in ['Заказчик', 'Менеджер', 'Оператор']

    def can_edit_requests(self):
        """Может ли пользователь редактировать заявки"""
        if not self.current_user:
            return False
        return self.current_user['type'] in ['Менеджер', 'Оператор', 'Менеджер по качеству']

    def can_manage_users(self):
        """Может ли пользователь управлять пользователями"""
        if not self.current_user:
            return False
        return self.current_user['type'] in ['Менеджер']

    def can_view_all_requests(self):
        """Может ли пользователь просматривать все заявки"""
        if not self.current_user:
            return False
        return self.current_user['type'] in ['Менеджер', 'Оператор', 'Менеджер по качеству', 'Мастер']

    def is_client(self):
        """Является ли пользователь клиентом"""
        if not self.current_user:
            return False
        return self.current_user['type'] == 'Заказчик'

    def is_master(self):
        """Является ли пользователь мастером"""
        if not self.current_user:
            return False
        return self.current_user['type'] == 'Мастер'

    def can_add_comments(self):
        """Может ли пользователь добавлять комментарии"""
        if not self.current_user:
            return False
        return self.current_user['type'] in ['Мастер', 'Менеджер', 'Оператор', 'Менеджер по качеству']
    
    def can_view_statistics(self):
        """Может ли пользователь просматривать статистику"""
        if not self.current_user:
            return False
        return self.current_user['type'] in ['Менеджер', 'Оператор', 'Менеджер по качеству']

    def can_search_requests(self):
        """Может ли пользователь искать заявки"""
        if not self.current_user:
            return False
        return self.current_user['type'] in ['Менеджер', 'Оператор', 'Менеджер по качеству', 'Мастер']

    def get_role_badge(self):
        """Получение бейджа роли"""
        if not self.current_user:
            return ""
        
        # Для отображения "Заказчик" как "Клиент"
        role_display = self.current_user['type']
        if role_display == 'Заказчик':
            role_display = 'Клиент'
        
        role_class = {
            'Менеджер': 'role-manager',
            'Мастер': 'role-master',
            'Оператор': 'role-operator',
            'Заказчик': 'role-client',
            'Клиент': 'role-client',  # Дублирование для отображения
            'Менеджер по качеству': 'role-quality'
        }.get(self.current_user['type'], '')
        
        return f'<span class="role-badge {role_class}">{role_display}</span>'
def main():
    app = RepairServiceApp()
    
    # Инициализация сессии
    if 'user' not in st.session_state:
        st.session_state.user = None
    else:
        app.current_user = st.session_state.user
    
    # Главный заголовок
    st.markdown('<h1 class="main-header"> Система учета заявок на ремонт техники</h1>', unsafe_allow_html=True)
    
    # Если пользователь не авторизован - показываем форму входа
    if not app.current_user:
        show_login_form(app)
    else:
        show_main_interface(app)

def show_login_form(app):
    """Форма входа в систему"""
    st.markdown("### Вход в систему")
    
    with st.form("login_form"):
        login = st.text_input("Логин")
        password = st.text_input("Пароль", type="password")
        
        # Просто кнопка без колонок - будет слева по умолчанию
        submit = st.form_submit_button("Войти")
        
        if submit:
            with st.spinner("Выполняется вход..."):
                if app.login(login, password):
                    time.sleep(1)
                    st.rerun()
    
    # Тестовые учетные данные
    with st.expander("Тестовые учетные данные"):
        st.write("""
        **Менеджер:** kasoo / root
        **Мастер:** murashov123 / qwerty
        **Оператор:** perinaAD / 250519
        **Клиент:** login2 / pass2
        **Менеджер по качеству:** login5 / pass5
        """)

def show_main_interface(app):
    """Основной интерфейс после входа"""
    user = app.current_user
    
    # Боковая панель
    with st.sidebar:
        st.markdown(f"**{user['fio']}**")
        st.markdown(app.get_role_badge(), unsafe_allow_html=True)
        st.markdown(f"*Логин: {user['login']}*")
        st.markdown("---")
        
        # Меню в зависимости от роли
        if app.is_client():
            # Меню для клиента
            menu_options = ["Мои заявки"]
            if app.can_create_request():
                menu_options.append("Новая заявка")
            menu_options.append("Оценка качества")
        else:
            # Меню для других ролей
            menu_options = ["Дашборд"]
            if app.can_search_requests():
                menu_options.append("Поиск заявок")
            if app.can_view_statistics():
                menu_options.append("Статистика")
            if app.can_create_request():
                menu_options.insert(1, "Новая заявка")
            if app.can_manage_users():
                menu_options.append("Управление пользователями")
            menu_options.append("Оценка качества")
        
        selected_menu = st.radio("Меню", menu_options)
        
        st.markdown("---")
        
        if st.button("Выйти", use_container_width=True):
            app.logout()
            st.rerun()
    
    # Основное содержимое
    if selected_menu == "Дашборд" or selected_menu == "Мои заявки":
        show_dashboard(app)
    elif selected_menu == "Новая заявка":
        show_new_request_form(app)
    elif selected_menu == "Поиск заявок":
        if app.can_search_requests():
            show_search_requests(app)
        else:
            st.warning("У вас нет прав для поиска заявок")
    elif selected_menu == "Статистика":
        if app.can_view_statistics():
            show_statistics(app)
        else:
            st.warning("У вас нет прав для просмотра статистики")
    elif selected_menu == "Управление пользователями":
        if app.can_manage_users():
            show_user_management(app)
        else:
            st.warning("У вас нет прав для управления пользователями")
    elif selected_menu == "Оценка качества":
        show_quality_assessment()

def show_dashboard(app):
    """Дашборд с заявками"""
    if app.is_client():
        st.markdown('<h2 class="sub-header">Мои заявки</h2>', unsafe_allow_html=True)
    else:
        st.markdown('<h2 class="sub-header">Активные заявки</h2>', unsafe_allow_html=True)
    
    # Получение заявок в зависимости от роли
    if app.is_client():
        # Клиент видит только свои заявки
        requests_data = app.get_requests({"client_id": app.current_user['user_id']})
        
        if not requests_data:
            # Если нет заявок, показываем сообщение
            st.markdown('<div class="no-requests">', unsafe_allow_html=True)
            st.markdown("### У вас пока нет заявок")
            st.markdown("Нажмите **'+ Новая заявка'** в меню, чтобы создать первую заявку")
            st.markdown("</div>", unsafe_allow_html=True)
            return
    elif app.is_master():
        # Мастер видит только назначенные ему заявки
        st.info("Вы видите только назначенные вам заявки")
        requests_data = app.get_requests({"master_id": app.current_user['user_id']})
    elif app.can_view_all_requests():
        # Остальные роли видят все заявки
        requests_data = app.get_requests()
    else:
        requests_data = []
        st.warning("У вас нет прав для просмотра заявок")
    
    # Для не-клиентов показываем фильтры
    if not app.is_client():
        col1, col2 = st.columns(2)
        with col1:
            status_filter = st.selectbox(
                "Фильтр по статусу",
                ["Все", "Новая заявка", "В процессе ремонта", "Ожидание запчастей", "Готова к выдаче"]
            )
        with col2:
            search_term = st.text_input("Поиск по названию или модели")
        
        # Применение фильтров
        if status_filter != "Все":
            filtered_requests = [r for r in requests_data if r['request_status'] == status_filter]
        else:
            filtered_requests = requests_data
        
        if search_term:
            filtered_requests = [
                r for r in filtered_requests 
                if search_term.lower() in r['home_tech_type'].lower() 
                or search_term.lower() in r['home_tech_model'].lower()
            ]
    else:
        # Для клиента не показываем фильтры
        filtered_requests = requests_data
    
    # Отображение заявок
    if not filtered_requests:
        if app.is_client():
            st.info("У вас пока нет заявок")
        else:
            st.info("Заявки не найдены")
    else:
        # Показываем счетчик
        if app.is_client():
            st.info(f"У вас {len(filtered_requests)} заявок")
        else:
            st.info(f"Найдено заявок: {len(filtered_requests)}")
        
        for request in filtered_requests[:20]:  # Показываем первые 20
            with st.container():
                col1, col2, col3 = st.columns([3, 2, 1])
                
                with col1:
                    status_class = {
                        "Новая заявка": "status-new",
                        "В процессе ремонта": "status-in-progress",
                        "Готова к выдаче": "status-ready",
                        "Ожидание запчастей": "status-waiting"
                    }.get(request['request_status'], "")
                    
                    st.markdown(f"**{request['home_tech_type']}** - {request['home_tech_model']}")
                    st.markdown(f"<span class='{status_class}'>{request['request_status']}</span>", unsafe_allow_html=True)
                    st.markdown(f"*{request['problem_description'][:100]}...*" if len(request['problem_description']) > 100 else f"*{request['problem_description']}*")
                
                with col2:
                    if not app.is_client():
                        st.markdown(f"**Клиент:** {request['client_fio'] or 'Не указан'}")
                    st.markdown(f"**Мастер:** {request['master_fio'] or 'Не назначен'}")
                    st.markdown(f"**Дата:** {request['start_date']}")
                
                with col3:
                    if st.button("Подробнее", key=f"view_{request['request_id']}"):
                        st.session_state['selected_request'] = request['request_id']
                
                st.markdown("---")
        
        # Пагинация
        if len(filtered_requests) > 20:
            st.info(f"Показано 20 из {len(filtered_requests)} заявок")
    
    # Детальный просмотр заявки
    if 'selected_request' in st.session_state:
        show_request_details(app, st.session_state['selected_request'])

def show_new_request_form(app):
    """Форма создания новой заявки"""
    st.markdown('<h2 class="sub-header">Создание заявки</h2>', unsafe_allow_html=True)
    
    with st.form("new_request_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            home_tech_type = st.text_input("Вид бытовой техники *", placeholder="Например: Холодильник, Стиральная машина")
            home_tech_model = st.text_input("Модель техники *", placeholder="Например: Indesit DS 316 W")
            problem_description = st.text_area("Описание проблемы *", height=100, 
                                             placeholder="Подробно опишите проблему...")
        
        with col2:
            # Для клиента автоматически назначаем его как клиента
            if app.is_client():
                st.info("Заявка будет создана от вашего имени")
                client_id = app.current_user['user_id']
                
                # Клиенту не показываем выбор мастера
                st.info("Мастер будет назначен позже оператором сервиса")
                master_id = None
            else:
                # Получение списка клиентов для менеджера/оператора
                clients = app.get_users_by_role("Заказчик")
                client_options = {c['user_id']: f"{c['fio']} ({c['phone']})" for c in clients}
                
                if client_options:
                    client_id = st.selectbox("Клиент *", options=list(client_options.keys()), 
                                           format_func=lambda x: client_options[x])
                else:
                    st.warning("Клиенты не найдены в системе")
                    client_id = None
                
                # Получение списка мастеров для менеджера/оператора
                masters = app.get_users_by_role("Мастер")
                master_options = {m['user_id']: m['fio'] for m in masters}
                master_options[None] = "Не назначен"
                
                master_id = st.selectbox("Мастер (опционально)", options=list(master_options.keys()),
                                       format_func=lambda x: master_options[x])
        
        submitted = st.form_submit_button("Создать заявку")
        
        if submitted:
            if not all([home_tech_type, home_tech_model, problem_description]):
                st.error("Пожалуйста, заполните все обязательные поля (отмечены *)")
            elif not client_id:
                st.error("Не выбран клиент")
            else:
                request_data = {
                    "home_tech_type": home_tech_type,
                    "home_tech_model": home_tech_model,
                    "problem_description": problem_description,
                    "client_id": client_id,
                    "master_id": master_id if master_id != None else None
                }
                
                with st.spinner("Создание заявки..."):
                    response = app.create_request(request_data)
                    
                    if response.status_code == 201:
                        st.success("Заявка успешно создана!")
                        time.sleep(2)
                        st.rerun()
                    else:
                        try:
                            error_detail = response.json().get('detail', 'Неизвестная ошибка')
                            st.error(f"Ошибка при создании заявки: {error_detail}")
                        except:
                            st.error(f"Ошибка при создании заявки (код: {response.status_code})")
                            1
def show_search_requests(app):
    """Поиск заявок"""
    st.markdown('<h2 class="sub-header">Поиск заявок</h2>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        search_by = st.radio("Искать по:", ["ID заявки", "Типу техники", "Статусу", "Клиенту"])
    
    with col2:
        if search_by == "ID заявки":
            request_id = st.number_input("ID заявки", min_value=1, step=1, value=1)
            if st.button("Найти по ID"):
                requests = app.get_requests({"request_id": int(request_id)})
                if requests:
                    show_requests_table(requests, app)
                else:
                    st.info("Заявка не найдена")
        
        elif search_by == "Типу техники":
            tech_type = st.text_input("Тип техники", placeholder="Например: Холодильник")
            if st.button("Найти по типу"):
                requests = app.get_requests({"search": tech_type})
                show_requests_table(requests, app)
        
        elif search_by == "Статусу":
            status_options = ["Все", "Новая заявка", "В процессе ремонта", "Ожидание запчастей", "Готова к выдаче"]
            selected_status = st.selectbox("Статус", status_options)
            if st.button("Найти по статусу"):
                if selected_status != "Все":
                    requests = app.get_requests({"status": selected_status})
                else:
                    requests = app.get_requests()
                show_requests_table(requests, app)
        
        elif search_by == "Клиенту":
            clients = app.get_users_by_role("Клиент")
            if clients:
                client_options = {c['user_id']: f"{c['fio']} ({c['phone']})" for c in clients}
                selected_client = st.selectbox("Выберите клиента", options=list(client_options.keys()),
                                             format_func=lambda x: client_options[x])
                if st.button("Найти по клиенту"):
                    requests = app.get_requests({"client_id": selected_client})
                    show_requests_table(requests, app)
            else:
                st.info("Клиенты не найдены")

def show_requests_table(requests, app):
    """Отображение заявок в таблице"""
    if requests:
        df = pd.DataFrame(requests)
        # Выбор нужных колонок
        display_columns = ['request_id', 'home_tech_type', 'home_tech_model', 
                          'request_status', 'client_fio', 'start_date']
        df_display = df[display_columns]
        
        # Форматирование статуса
        def format_status(status):
            if status == "Новая заявка":
                return "" + status
            elif status == "В процессе ремонта":
                return "" + status
            elif status == "Готова к выдаче":
                return "" + status
            elif status == "Ожидание запчастей":
                return "" + status
            return status
        
        df_display['request_status'] = df_display['request_status'].apply(format_status)
        
        st.dataframe(df_display, use_container_width=True, height=400)
        
        # Кнопки для детального просмотра
        st.markdown("### Выберите заявку для детального просмотра:")
        cols = st.columns(3)
        for idx, request in enumerate(requests[:9]):  # Показываем максимум 9 кнопок
            with cols[idx % 3]:
                if st.button(f"Заявка #{request['request_id']}", key=f"detail_{request['request_id']}"):
                    st.session_state['selected_request'] = request['request_id']
                    st.rerun()
    else:
        st.info("Заявки не найдены")

def show_request_details(app, request_id):
    """Детальное отображение заявки"""
    st.markdown("---")
    st.markdown("### Детали заявки")
    
    requests = app.get_requests({"request_id": request_id})
    if not requests:
        st.error("Заявка не найдена")
        return
    
    request = requests[0]
    
    # Проверка прав доступа
    if app.is_client() and request['client_id'] != app.current_user['user_id']:
        st.warning("У вас нет доступа к этой заявке")
        return
    
    # Информация о заявке
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**ID заявки:** {request['request_id']}")
        st.markdown(f"**Тип техники:** {request['home_tech_type']}")
        st.markdown(f"**Модель:** {request['home_tech_model']}")
        st.markdown(f"**Описание проблемы:**")
        st.info(request['problem_description'])
        if request['repair_parts']:
            st.markdown(f"**Запчасти:** {request['repair_parts']}")
    
    with col2:
        status_class = {
            "Новая заявка": "status-new",
            "В процессе ремонта": "status-in-progress",
            "Готова к выдаче": "status-ready",
            "Ожидание запчастей": "status-waiting"
        }.get(request['request_status'], "")
        
        st.markdown(f"**Статус:** <span class='{status_class}'>{request['request_status']}</span>", unsafe_allow_html=True)
        if not app.is_client():
            st.markdown(f"**Клиент:** {request['client_fio']}")
        st.markdown(f"**Мастер:** {request['master_fio'] or 'Не назначен'}")
        st.markdown(f"**Дата создания:** {request['start_date']}")
        if request['completion_date']:
            st.markdown(f"**Дата завершения:** {request['completion_date']}")
    
    # Комментарии
    st.markdown("### Комментарии")
    comments = app.get_comments(request_id)
    
    if comments:
        for comment in comments:
            with st.container():
                st.markdown(f"**{comment['master_fio']}** ({comment['created_at']}):")
                st.markdown(f"> {comment['message']}")
                st.markdown("---")
    else:
        st.info("Комментариев пока нет")
    
    # Форма добавления комментария
    if app.can_add_comments():
        st.markdown("### Добавить комментарий")
        with st.form(f"add_comment_{request_id}"):
            new_comment = st.text_area("Текст комментария", height=100)
            if st.form_submit_button("Добавить комментарий"):
                if new_comment.strip():
                    response = app.add_comment(request_id, new_comment)
                    if response and response.status_code == 201:
                        st.success("Комментарий добавлен")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Ошибка при добавлении комментария")
                else:
                    st.warning("Введите текст комментария")
    
    # Полное изменение заявки (для Менеджера, Оператора, Менеджера по качеству)
    if app.can_edit_requests():
        show_full_update_form(app, request_id, request)
    else:
        st.info("Только менеджер, оператор или менеджер по качеству могут редактировать заявки")
    
    if st.button("Закрыть детали"):
        st.session_state.pop('selected_request', None)
        st.rerun()

def show_full_update_form(app, request_id, request):
    """Полная форма обновления заявки"""
    st.markdown("### Полное изменение заявки")
    
    with st.form(f"full_update_form_{request_id}"):
        col1, col2 = st.columns(2)
        
        with col1:
            new_status = st.selectbox("Новый статус *", [
                "Новая заявка", "В процессе ремонта", 
                "Ожидание запчастей", "Готова к выдаче"
            ], index=[
                "Новая заявка", "В процессе ремонта", 
                "Ожидание запчастей", "Готова к выдаче"
            ].index(request['request_status']) if request['request_status'] in [
                "Новая заявка", "В процессе ремонта", 
                "Ожидание запчастей", "Готова к выдаче"
            ] else 0)
            
            new_tech_type = st.text_input("Вид техники *", value=request['home_tech_type'])
            new_tech_model = st.text_input("Модель техники *", value=request['home_tech_model'])
            
            new_problem_description = st.text_area("Описание проблемы *", 
                                                 value=request['problem_description'], 
                                                 height=100)
        
        with col2:
            # Выбор клиента
            clients = app.get_users_by_role("Заказчик")  # Используем "Заказчик" для поиска
            client_options = {c['user_id']: f"{c['fio']} ({c['phone']})" for c in clients}
            current_client_id = request.get('client_id')
            
            if current_client_id in client_options:
                default_client_index = list(client_options.keys()).index(current_client_id)
            else:
                default_client_index = 0
            
            new_client_id = st.selectbox("Клиент *", 
                                       options=list(client_options.keys()),
                                       format_func=lambda x: client_options[x],
                                       index=default_client_index)
            
            # Выбор мастера
            masters = app.get_users_by_role("Мастер")
            master_options = {m['user_id']: m['fio'] for m in masters}
            master_options[None] = "Не назначен"
            
            current_master_id = request.get('master_id')
            if current_master_id in master_options:
                default_master_index = list(master_options.keys()).index(current_master_id)
            else:
                default_master_index = 0
            
            new_master_id = st.selectbox("Мастер", 
                                       options=list(master_options.keys()),
                                       format_func=lambda x: master_options[x],
                                       index=default_master_index)
            
            repair_parts = st.text_input("Запчасти", value=request.get('repair_parts', ''))
            
            # Дата завершения
            if new_status == "Готова к выдаче":
                if request['completion_date']:
                    default_completion_date = datetime.strptime(request['completion_date'], '%Y-%m-%d').date()
                else:
                    default_completion_date = date.today()
                new_completion_date = st.date_input("Дата завершения", value=default_completion_date)
            else:
                new_completion_date = None
        
        col1, col2 = st.columns(2)
        with col1:
            update_btn = st.form_submit_button("Сохранить изменения")
        with col2:
            cancel_btn = st.form_submit_button("Отменить изменения")
        
        if update_btn:
            # Проверка обязательных полей
            if not all([new_tech_type, new_tech_model, new_problem_description]):
                st.error("Заполните все обязательные поля (*)")
            else:
                update_data = {
                    "home_tech_type": new_tech_type,
                    "home_tech_model": new_tech_model,
                    "problem_description": new_problem_description,
                    "request_status": new_status,
                    "client_id": new_client_id,
                    "master_id": new_master_id if new_master_id != None else None
                }
                
                if repair_parts != request.get('repair_parts', ''):
                    update_data["repair_parts"] = repair_parts if repair_parts else None
                
                if new_status == "Готова к выдаче":
                    update_data["completion_date"] = str(new_completion_date)
                elif request['request_status'] == "Готова к выдаче" and new_status != "Готова к выдаче":
                    update_data["completion_date"] = None
                
                response = app.update_request(request_id, update_data)
                if response.status_code == 200:
                    st.success("Заявка успешно обновлена!")
                    time.sleep(1)
                    st.rerun()
                else:
                    try:
                        error_detail = response.json().get('detail', 'Неизвестная ошибка')
                        st.error(f"Ошибка при обновлении заявки: {error_detail}")
                    except:
                        st.error(f"Ошибка при обновлении заявки (код: {response.status_code})")

def show_statistics(app):
    """Отображение статистики"""
    st.markdown('<h2 class="sub-header">Статистика работы </h2>', unsafe_allow_html=True)
    
    with st.spinner("Загрузка статистики..."):
        stats = app.get_statistics()
    
    if not stats:
        st.error("Не удалось загрузить статистику")
        return
    
    # Основные метрики
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Всего заявок", stats['total_requests'])
    
    with col2:
        st.metric("Выполнено заявок", stats['completed_requests'])
    
    with col3:
        avg_time = stats['average_repair_time_days']
        if avg_time:
            st.metric("Среднее время ремонта (дней)", f"{avg_time:.1f}")
        else:
            st.metric("Среднее время ремонта", "Нет данных")
    
    # Графики
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Заявки по статусам**")
        if stats['requests_by_status']:
            status_df = pd.DataFrame(
                list(stats['requests_by_status'].items()),
                columns=['Статус', 'Количество']
            )
            # Форматирование для графика
            status_df['Статус'] = status_df['Статус'].apply(lambda x: {
                "Новая заявка": "Новая",
                "В процессе ремонта": "В работе",
                "Готова к выдаче": "Готово",
                "Ожидание запчастей": "Ожидание"
            }.get(x, x))
            
            st.bar_chart(status_df.set_index('Статус'))
        else:
            st.info("Нет данных по статусам")
    
    with col2:
        st.markdown("**Заявки по типам техники**")
        if stats['requests_by_tech_type']:
            tech_df = pd.DataFrame(
                list(stats['requests_by_tech_type'].items()),
                columns=['Тип техники', 'Количество']
            )
            st.bar_chart(tech_df.set_index('Тип техники'))
        else:
            st.info("Нет данных по типам техники")
    
    # Детальная таблица
    st.markdown("### Детальная статистика")
    
    if stats['requests_by_status']:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**По статусам:**")
            for status, count in stats['requests_by_status'].items():
                st.write(f"- {status}: {count}")
        
        with col2:
            st.markdown("**По типам техники:**")
            for tech_type, count in stats['requests_by_tech_type'].items():
                st.write(f"- {tech_type}: {count}")

def show_user_management(app):
    """Управление пользователями"""
    if not app.can_manage_users():
        st.warning("У вас нет прав для управления пользователями")
        return
    
    st.markdown('<h2 class="sub-header">Управление пользователями</h2>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["Список пользователей", "Добавить пользователя", "Редактировать пользователя"])
    
    with tab1:
        st.markdown("### Все пользователи системы")
        users = app.get_all_users()
        
        if users:
            # Создаем DataFrame с пользователями
            df = pd.DataFrame(users)
            
            # Добавляем цвет для ролей
            def format_role(role):
                role_colors = {
                    'Менеджер': '🟡',
                    'Мастер': '🔵', 
                    'Оператор': '🟢',
                    'Клиент': '🟣',
                    'Менеджер по качеству': '🔴'
                }
                return f"{role_colors.get(role, '⚪')} {role}"
            
            df['type'] = df['type'].apply(format_role)
            
            # Отображаем таблицу
            st.dataframe(df[['user_id', 'fio', 'type', 'phone', 'login']], 
                        use_container_width=True,
                        column_config={
                            'user_id': 'ID',
                            'fio': 'ФИО',
                            'type': 'Роль',
                            'phone': 'Телефон',
                            'login': 'Логин'
                        })
            
            st.info(f"Всего пользователей: {len(users)}")
        else:
            st.info("Пользователи не найдены")
    
    with tab2:
        st.markdown("### Создание нового пользователя")
        
        with st.form("add_user_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                fio = st.text_input("ФИО *", placeholder="Иванов Иван Иванович")
                phone = st.text_input("Номер телефона *", placeholder="89991234567")
                login = st.text_input("Логин *", placeholder="user123")
            
            with col2:
                password = st.text_input("Пароль *", type="password")
                confirm_password = st.text_input("Подтвердите пароль *", type="password")
                user_type = st.selectbox("Роль *", [
                    "Менеджер", "Мастер", "Оператор", "Клиент", "Менеджер по качеству"
                ])
            
            submitted = st.form_submit_button("Создать пользователя")
            
            if submitted:
                if not all([fio, phone, login, password, confirm_password]):
                    st.error("Заполните все обязательные поля (*)")
                elif password != confirm_password:
                    st.error("Пароли не совпадают")
                else:
                    user_data = {
                        "fio": fio,
                        "phone": phone,
                        "login": login,
                        "password": password,
                        "type": user_type
                    }
                    
                    with st.spinner("Создание пользователя..."):
                        response = app.create_user(user_data)
                        
                        if response.status_code == 201:
                            st.success("Пользователь успешно создан!")
                            time.sleep(2)
                            st.rerun()
                        else:
                            try:
                                error_detail = response.json().get('detail', 'Неизвестная ошибка')
                                st.error(f"Ошибка при создании пользователя: {error_detail}")
                            except:
                                st.error(f"Ошибка при создании пользователя (код: {response.status_code})")
    
    with tab3:
        st.markdown("### Редактирование пользователя")
        
        users = app.get_all_users()
        if not users:
            st.info("Нет пользователей для редактирования")
        else:
            user_options = {u['user_id']: f"{u['fio']} ({u['type']})" for u in users}
            selected_user_id = st.selectbox("Выберите пользователя", 
                                          options=list(user_options.keys()),
                                          format_func=lambda x: user_options[x])
            
            if selected_user_id:
                user = next((u for u in users if u['user_id'] == selected_user_id), None)
                
                if user:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**Текущие данные пользователя:**")
                        st.write(f"**ФИО:** {user['fio']}")
                        st.write(f"**Телефон:** {user['phone']}")
                        st.write(f"**Логин:** {user['login']}")
                        st.write(f"**Роль:** {user['type']}")
                    
                    with col2:
                        st.markdown("**Обновление данных:**")
                        
                        with st.form("edit_user_form"):
                            new_fio = st.text_input("Новое ФИО", value=user['fio'])
                            new_phone = st.text_input("Новый телефон", value=user['phone'])
                            new_login = st.text_input("Новый логин", value=user['login'])
                            new_password = st.text_input("Новый пароль (оставьте пустым, чтобы не менять)", 
                                                       type="password", value="")
                            
                            role_options = ["Менеджер", "Мастер", "Оператор", "Клиент", "Менеджер по качеству"]
                            current_role_index = role_options.index(user['type']) if user['type'] in role_options else 0
                            new_type = st.selectbox("Новая роль", role_options, index=current_role_index)
                            
                            col_btn1, col_btn2 = st.columns(2)
                            with col_btn1:
                                update_btn = st.form_submit_button("Обновить данные")
                            with col_btn2:
                                delete_btn = st.form_submit_button("Удалить пользователя")
                            
                            if update_btn:
                                update_data = {}
                                if new_fio != user['fio']:
                                    update_data['fio'] = new_fio
                                if new_phone != user['phone']:
                                    update_data['phone'] = new_phone
                                if new_login != user['login']:
                                    update_data['login'] = new_login
                                if new_password:
                                    update_data['password'] = new_password
                                if new_type != user['type']:
                                    update_data['type'] = new_type
                                
                                if update_data:
                                    response = app.update_user(selected_user_id, update_data)
                                    if response.status_code == 200:
                                        st.success("Данные пользователя обновлены!")
                                        time.sleep(2)
                                        st.rerun()
                                    else:
                                        try:
                                            error_detail = response.json().get('detail', 'Неизвестная ошибка')
                                            st.error(f"Ошибка при обновлении: {error_detail}")
                                        except:
                                            st.error(f"Ошибка при обновлении (код: {response.status_code})")
                                else:
                                    st.info("Нет изменений для сохранения")
                            
                            if delete_btn:
                                # Подтверждение удаления
                                st.warning("Внимание: это действие нельзя отменить!")
                                confirm = st.checkbox("Я подтверждаю удаление пользователя")
                                if confirm:
                                    response = app.delete_user(selected_user_id)
                                    if response.status_code == 200:
                                        st.success("Пользователь удален!")
                                        time.sleep(2)
                                        st.rerun()
                                    else:
                                        try:
                                            error_detail = response.json().get('detail', 'Неизвестная ошибка')
                                            st.error(f"Ошибка при удалении: {error_detail}")
                                        except:
                                            st.error(f"Ошибка при удалении (код: {response.status_code})")

def show_quality_assessment():
    """Оценка качества работы"""
    st.markdown('<h2 class="sub-header">Оценка качества работы сервиса</h2>', unsafe_allow_html=True)
    
    st.info("""
    Пожалуйста, оцените качество работы нашего сервисного центра.
    Ваше мнение поможет нам стать лучше!
    """)
    
    # Генерация QR кода
    qr_url = "https://docs.google.com/forms/d/e/1FAIpQLSeNVa-Ma908dPVd9sdQaOzNlfmW2iag8DAfGBFaVRiQZcwWxA/viewform?usp=sharing&ouid=109286482311707845178"
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Создание QR кода
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Конвертация в байты для Streamlit
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        
        st.image(img_byte_arr, caption="Отсканируйте QR код")
    
    with col2:
        st.markdown("### Инструкция:")
        st.markdown("""
        1. Откройте приложение камеры на вашем смартфоне
        2. Наведите камеру на QR код
        3. Перейдите по ссылке, которая откроется
        4. Заполните форму оценки качества
        
        **Форма содержит вопросы о:**
        - Качестве ремонта
        - Вежливости персонала
        - Соблюдении сроков
        - Общих впечатлениях
        
        **Спасибо за ваш отзыв!**
        """)
    
    st.markdown("---")
    st.markdown(f"[Или перейдите по ссылке]({qr_url})")

if __name__ == "__main__":
    main()