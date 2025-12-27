from pydantic import BaseModel, EmailStr, Field
from datetime import date, datetime
from typing import Optional, List
from enum import Enum

class RequestStatus(str, Enum):
    NEW = "Новая заявка"
    IN_PROGRESS = "В процессе ремонта"
    WAITING_PARTS = "Ожидание запчастей"
    READY = "Готова к выдаче"

class UserRole(str, Enum):
    MANAGER = "Менеджер"
    MASTER = "Мастер"
    OPERATOR = "Оператор"
    CLIENT = "Заказчик"
    QUALITY_MANAGER = "Менеджер по качеству"

class UserCreate(BaseModel):
    fio: str = Field(..., description="ФИО пользователя")
    phone: str = Field(..., description="Номер телефона")
    login: str = Field(..., description="Логин")
    password: str = Field(..., description="Пароль")
    type: UserRole = Field(..., description="Роль пользователя")

class UserResponse(BaseModel):
    user_id: int
    fio: str
    phone: str
    login: str
    type: UserRole
    
    class Config:
        from_attributes = True

class RequestCreate(BaseModel):
    home_tech_type: str = Field(..., description="Вид бытовой техники")
    home_tech_model: str = Field(..., description="Модель бытовой техники")
    problem_description: str = Field(..., description="Описание проблемы")
    client_id: int = Field(..., description="ID клиента")
    master_id: Optional[int] = Field(None, description="ID мастера")

class RequestUpdate(BaseModel):
    request_status: Optional[RequestStatus] = None
    problem_description: Optional[str] = None
    master_id: Optional[int] = None
    repair_parts: Optional[str] = None
    completion_date: Optional[date] = None

class RequestResponse(BaseModel):
    request_id: int
    start_date: date
    home_tech_type: str
    home_tech_model: str
    problem_description: str
    request_status: RequestStatus
    completion_date: Optional[date] = None
    repair_parts: Optional[str] = None
    master_id: Optional[int] = None
    client_id: int
    client_fio: Optional[str] = None
    master_fio: Optional[str] = None
    
    class Config:
        from_attributes = True

class CommentCreate(BaseModel):
    message: str = Field(..., description="Текст комментария")
    request_id: int = Field(..., description="ID заявки")

class CommentResponse(BaseModel):
    comment_id: int
    message: str
    master_id: int
    request_id: int
    master_fio: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class StatisticsResponse(BaseModel):
    total_requests: int
    completed_requests: int
    average_repair_time_days: Optional[float]
    requests_by_status: dict
    requests_by_tech_type: dict

class UserUpdate(BaseModel):
    fio: Optional[str] = None
    phone: Optional[str] = None
    login: Optional[str] = None
    password: Optional[str] = None
    type: Optional[UserRole] = None

class Permission:
    """Класс для проверки прав доступа"""
    
    @staticmethod
    def can_view_all_requests(user_role: UserRole) -> bool:
        """Может ли пользователь просматривать все заявки"""
        return user_role in [UserRole.MANAGER, UserRole.OPERATOR, UserRole.QUALITY_MANAGER, UserRole.MASTER]
    
    @staticmethod
    def can_create_request(user_role: UserRole) -> bool:
        """Может ли пользователь создавать заявки"""
        return user_role in [UserRole.CLIENT, UserRole.MANAGER, UserRole.OPERATOR]
    
    @staticmethod
    def can_edit_request(user_role: UserRole) -> bool:
        """Может ли пользователь редактировать заявки"""
        return user_role in [UserRole.MANAGER, UserRole.OPERATOR, UserRole.QUALITY_MANAGER, UserRole.MASTER]
    
    @staticmethod
    def can_manage_users(user_role: UserRole) -> bool:
        """Может ли пользователь управлять пользователями"""
        return user_role in [UserRole.MANAGER]
    
    @staticmethod
    def can_view_client_requests(user_role: UserRole) -> bool:
        """Может ли пользователь просматривать заявки клиента"""
        return user_role == UserRole.CLIENT
    
    @staticmethod
    def can_view_master_requests(user_role: UserRole) -> bool:
        """Может ли мастер просматривать свои заявки"""
        return user_role == UserRole.MASTER
    
    @staticmethod
    def can_add_comments(user_role: UserRole) -> bool:
        """Может ли пользователь добавлять комментарии"""
        return user_role in [UserRole.MASTER, UserRole.MANAGER, UserRole.QUALITY_MANAGER, UserRole.OPERATOR]
    
class CommentCreateRequest(BaseModel):
    message: str = Field(..., description="Текст комментария")
    request_id: int = Field(..., description="ID заявки")
    master_id: int = Field(..., description="ID мастера")