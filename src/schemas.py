import re
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

class UserCreate(BaseModel):
    username: str = Field(..., min_length=4, max_length=20, pattern=r'^[a-zA-Z0-9]+$')
    email: EmailStr
    password: str
    confirm_password: str
    age: int = Field(..., ge=18, le=100)

    # Валидация сложности пароля (кастомный field_validator)
    @field_validator('password')
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Пароль должен содержать минимум 8 символов')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Пароль должен содержать хотя бы одну заглавную букву')
        if not re.search(r'[0-9]', v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        if not re.search(r'[!@#$%^&*]', v):
            raise ValueError('Пароль должен содержать хотя бы один спецсимвол (!@#$%^&*)')
        return v

    # Валидация совпадения паролей (model_validator)
    @model_validator(mode='after')
    def check_passwords_match(self) -> 'UserCreate':
        if self.password != self.confirm_password:
            raise ValueError('Пароли не совпадают')
        return self
