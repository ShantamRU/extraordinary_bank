import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, validator


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class UserEntry(BaseModel):
    id: str
    first_name: str = None
    last_name: str = None
    middle_name: str = None
    email: str
    password: str
    phone: str
    confirmation_code: str = None

    def get_fio(cls):
        return '{}{}{}'.format(
            cls.first_name,
            ' ' + cls.last_name if cls.last_name else '',
            ' ' + cls.middle_name if cls.middle_name else '')

    class Config:
        orm_mode = True


class UserCreate(BaseModel):
    first_name: str = Field(None, example='Ivan')
    last_name: str = Field(None, example='Ivanov')
    middle_name: str = Field(None, example='Ivanovich')
    email: str = Field(..., example='ivan@example.com', regex=r'.+@.+[.].+')
    password: str = Field(...)
    phone: str = Field(..., example='89000000000')

    @validator('password')
    def check_password(cls, password):
        """
        The password consists of at least 8 characters and must contain at least one capital letter and one number.
        """
        if len(password) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.compile(r'.*[A-Z].*').match(password):
            raise ValueError('Password must contain at least one uppercase character')
        if not re.compile(r'.*\d.*').match(password):
            raise ValueError('Password must contain at least one number')
        return password

    class Config:
        orm_mode = True


class UserResponse(BaseModel):
    id: str
    first_name: str = Field(None, example='Ivan')
    last_name: str = Field(None, example='Ivanov')
    middle_name: str = Field(None, example='Ivanovich')
    email: str = Field(..., example='ivan@example.com')
    phone: str = Field(..., example='89000000000')


class UserConfirmation(BaseModel):
    confirmation_code: str = Field(..., example='123456')


class UserUpdatePassword(BaseModel):
    old_password: str = Field(..., example='123456')
    new_password: str = Field(..., example='234567')


class UserUpdateEmail(BaseModel):
    email: str = Field(..., example='new_ivan@example.com')


class UserUpdatePhone(BaseModel):
    phone: str = Field(..., example='89000000001')


class UserUpdate(BaseModel):
    first_name: str = Field(None, example='Ivan')
    last_name: str = Field(None, example='Ivanov')
    middle_name: str = Field(None, example='Ivanovich')


class UpdateRequestEntry(BaseModel):
    id: str
    user_id: str
    conditions: dict
    confirmation_code: str


class AccountCreate(BaseModel):
    currency_code: str = Field(..., example='RUB')
    amount: float = Field(..., example='10000000.00')

    @validator('amount')
    def check_amount(cls, amount):
        """
        Счёт нельзя создать с отрицательным балансом
        """
        if amount < 0.:
            raise ValueError('Amount must be positive')
        return amount

    class Config:
        orm_mode = True


class AccountOperationEntry(BaseModel):
    id: str
    account_id: str
    amount_diff: float
    created_at: datetime
    description: str = None

    class Config:
        orm_mode = True


class AccountOperationCreate(BaseModel):
    account_id: str = Field(..., example='66a5eabf-e55f-46b9-b6c7-bf01bc998ca3')
    amount_diff: float = Field(..., example='-100000.00')
    description: str = Field(..., example='Снятие наличных')
    recipient_account: str = Field(None, example='96a02225-c216-451b-8e9f-d8d4df452296')

    class Config:
        orm_mode = True


class AccountEntry(BaseModel):
    id: str
    user_id: str
    currency_code: str
    amount: float

    class Config:
        orm_mode = True


class CurrencyEntry(BaseModel):
    char_code: str
    name: str
    value: float

    class Config:
        orm_mode = True


class CurrencyCreate(BaseModel):
    char_code: str = Field(..., example='RUB')

    class Config:
        orm_mode = True
