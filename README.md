
## Запуск

### 1. Установка зависимостей

```bash
# Создание виртуального окружения (опционально)
python -m venv venv

# Активация виртуального окружения
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
```

### 2. Настройка базы данных
Убедитесь, что файл базы данных находится в корневой папке
```bash
Для создания таблиц, и загрузки данных нужно: python load_data.py
```

### 3. Запуск приложения

```bash
uvicorn main:app --reload     

streamlit run frontend.py   
```

### 4. Доступ к приложению

- **Frontend**: http://localhost:8000/docs
- **Backend API**: http://localhost:8000



---
