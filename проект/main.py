from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import date, datetime
import uvicorn
from typing import List, Optional
from models import *
from database import Database
from models import CommentCreateRequest

app = FastAPI(
    title="Система учета заявок на ремонт бытовой техники",
    description="API для управления заявками на ремонт",
    version="1.0.0"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Инициализация базы данных
db = Database()

# Функция для получения текущего пользователя (упрощенная версия)
def get_current_user(auth_header: Optional[str] = None):
    """Упрощенная функция для получения текущего пользователя"""
    # В реальном приложении здесь была бы проверка JWT токена
    # Для упрощения используем заглушку
    async def dummy_dependency():
        # Возвращаем None, так как реальная аутентификация будет через отдельный эндпоинт
        return None
    
    return dummy_dependency

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    print("Сервер запущен")

# ========== Аутентификация (без зависимости get_current_user) ==========
@app.post("/auth/login", response_model=UserResponse)
async def login(login_data: dict):
    """Аутентификация пользователя"""
    login_str = login_data.get('login')
    password = login_data.get('password')
    
    if not login_str or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Требуется логин и пароль"
        )
    
    user = db.authenticate_user(login_str, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль"
        )
    
    return user

# ========== Пользователи ==========
@app.post("/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
    """Создание нового пользователя"""
    try:
        user_id = db.create_user(user.dict())
        created_user = db.get_user_by_id(user_id)
        return created_user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка при создании пользователя: {str(e)}"
        )

@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int):
    """Получение пользователя по ID"""
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    return user

@app.get("/users/role/{role}", response_model=List[UserResponse])
async def get_users_by_role(role: str):
    """Получение пользователей по роли"""
    users = db.get_users_by_role(role)
    return users

# ========== Заявки (упрощенная версия без проверки прав) ==========
@app.post("/requests/", response_model=RequestResponse, status_code=status.HTTP_201_CREATED)
async def create_request(request: RequestCreate):
    """Создание новой заявки"""
    try:
        # Проверка существования клиента
        client = db.get_user_by_id(request.client_id)
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Клиент не найден"
            )
        
        # Проверка мастера, если указан
        if request.master_id:
            master = db.get_user_by_id(request.master_id)
            if not master or master['type'] != 'Мастер':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Указанный мастер не найден или не является мастером"
                )
        
        request_data = request.dict()
        request_id = db.create_request(request_data)
        
        # Получение созданной заявки
        requests = db.get_requests({'request_id': request_id})
        if not requests:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при получении созданной заявки"
            )
        
        return requests[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка при создании заявки: {str(e)}"
        )

@app.get("/requests/", response_model=List[RequestResponse])
async def get_requests(
    request_id: Optional[int] = None,
    client_id: Optional[int] = None,
    master_id: Optional[int] = None,
    status: Optional[str] = None,
    search: Optional[str] = None
):
    """Получение списка заявок с фильтрами"""
    filters = {}
    if request_id:
        filters['request_id'] = request_id
    if client_id:
        filters['client_id'] = client_id
    if master_id:
        filters['master_id'] = master_id
    if status:
        filters['status'] = status
    if search:
        filters['search'] = search
    
    requests = db.get_requests(filters)
    return requests

@app.get("/requests/{request_id}", response_model=RequestResponse)
async def get_request(request_id: int):
    """Получение заявки по ID"""
    requests = db.get_requests({'request_id': request_id})
    if not requests:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заявка не найдена"
        )
    return requests[0]

@app.put("/requests/{request_id}", response_model=RequestResponse)
async def update_request(request_id: int, update_data: RequestUpdate):
    """Обновление заявки"""
    # Проверка существования заявки
    existing_request = db.get_requests({'request_id': request_id})
    if not existing_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заявка не найдена"
        )
    
    # Проверка мастера, если указан
    if update_data.master_id:
        master = db.get_user_by_id(update_data.master_id)
        if not master or master['type'] != 'Мастер':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Указанный мастер не найден или не является мастером"
            )
    
    # Обновление заявки
    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
    
    if not db.update_request(request_id, update_dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось обновить заявку"
        )
    
    # Получение обновленной заявки
    updated_request = db.get_requests({'request_id': request_id})[0]
    return updated_request

# ========== Комментарии ==========
@app.post("/comments/", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(comment: CommentCreateRequest):
    """Добавление комментария к заявке"""
    # Проверка существования заявки
    request = db.get_requests({'request_id': comment.request_id})
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Заявка не найдена"
        )
    
    # Проверка пользователя (может быть мастером, менеджером, оператором и т.д.)
    user = db.get_user_by_id(comment.master_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    # Проверяем, может ли пользователь добавлять комментарии
    allowed_roles = ['Мастер', 'Менеджер', 'Оператор', 'Менеджер по качеству']
    if user['type'] not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет прав для добавления комментариев"
        )
    
    try:
        comment_data = comment.dict()
        comment_id = db.add_comment(comment_data)
        
        # Получение созданного комментария
        comments = db.get_comments(comment.request_id)
        created_comment = next((c for c in comments if c['comment_id'] == comment_id), None)
        
        if not created_comment:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при получении созданного комментария"
            )
        
        return created_comment
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка при создании комментария: {str(e)}"
        )
    
@app.get("/comments/{request_id}", response_model=List[CommentResponse])
async def get_request_comments(request_id: int):
    """Получение комментариев к заявке"""
    comments = db.get_comments(request_id)
    return comments

# ========== Статистика ==========
@app.get("/statistics/", response_model=StatisticsResponse)
async def get_statistics():
    """Получение статистики"""
    stats = db.get_statistics()
    return stats

# ========== QR код для оценки ==========
@app.get("/qrcode/")
async def get_qrcode_info():
    """Получение информации для QR кода оценки качества"""
    return {
        "message": "QR код для оценки качества сервиса",
        "url": "https://docs.google.com/forms/d/e/1FAIpQLSeNVa-Ma908dPVd9sdQaOzNlfmW2iag8DAfGBFaVRiQZcwWxA/viewform?usp=sharing&ouid=109286482311707845178",
        "instruction": "Отсканируйте QR код для оценки качества выполненных работ"
    }

# ========== Управление пользователями (простые версии) ==========
@app.get("/users/", response_model=List[UserResponse])
async def get_all_users():
    """Получение списка всех пользователей"""
    users = db.get_all_users()
    return users

@app.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user_update: dict):
    """Обновление данных пользователя"""
    # Проверка существования пользователя
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    # Обновление пользователя
    if not db.update_user(user_id, user_update):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось обновить пользователя"
        )
    
    # Получение обновленного пользователя
    updated_user = db.get_user_by_id(user_id)
    return updated_user

@app.delete("/users/{user_id}")
async def delete_user(user_id: int):
    """Удаление пользователя"""
    # Удаление пользователя
    if not db.delete_user(user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    return {"message": "Пользователь успешно удален"}

# ========== Обработка ошибок ==========
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"Внутренняя ошибка сервера: {str(exc)}"},
    )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)