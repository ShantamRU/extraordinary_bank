from typing import List

import uvicorn
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from starlette import status

from controller import User as UserController, Account as AccountController, Currency as CurrencyController, \
    AccountOperation as AccountOperationController
from schema import UserCreate, UserEntry, Token, AccountCreate, CurrencyCreate, AccountOperationCreate, AccountEntry, \
    UserUpdatePassword, UserUpdateEmail, UserUpdatePhone, UserConfirmation, UserUpdate, UserResponse
from app import app


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Users

@app.post("/users/")
async def register_user(user: UserCreate):
    """
    Регистрация пользователя в системе (для регистрации используется почта, пароль и номер телефона (также можно
    передать ФИО). Пароль состоит не менее, чем из 8 знаков, обязательно содержит минимум одну заглавную букву и
    одну цифру), после регистрации пользователь должен подтвердить свою почту через 6-ти значный цифровой код,
    который будет отправлен ему после завершения регистрации на почту.
    """
    if await UserController.get_user(email=user.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already in use ")
    if await UserController.get_user(phone=user.phone):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number is already in use ")
    user_id = await UserController.register(user)
    return {"user_id": user_id}


@app.post("/users/email_confirmation/")
async def user_email_confirmation(data: UserConfirmation):
    """
    Эндпоинт для подтверждения почты через 6-ти значный цифровой код.
    """
    user_id = await UserController.email_confirmation(data.confirmation_code)
    if not user_id:
        raise HTTPException(status_code=400, detail='Incorrect confirmation code')
    return {"user_id": user_id}


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Внутренняя функция для получения аутентифицированного пользователя по токену из Куков
    """
    user = await UserController.get_current_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"})
    return user


@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Пользователь имеет возможность входа в систему. Для входа используется почта или номер телефона и пароль.
    """
    user = await UserController.authenticate_user(form_data.username, form_data.password)
    access_token = UserController.create_access_token(email=user.email)
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me/", response_model=UserResponse)
async def read_users_me(current_user: UserEntry = Depends(get_current_user)):
    """Возвращает данные аутентифицированного пользователя: Имя Фамилия Отчество, электронная почта, номер телефона"""
    return UserResponse(**current_user.dict())


@app.post("/users/me/update/password")
async def user_update_password(data: UserUpdatePassword, current_user: UserEntry = Depends(get_current_user)):
    """
    Пользователь имеет возможность изменить пароль (изменение пароля происходит с использованием предыдущего пароля).
    """
    user_id = await UserController.update_password(current_user, data.old_password, data.new_password)
    return {"user_id": user_id}


@app.post("/users/me/update/email")
async def user_update_email(data: UserUpdateEmail, current_user: UserEntry = Depends(get_current_user)):
    """
    Пользователь имеет возможность изменить электронную почту (пользователь должен подтвердить почту перед изменением).
    """
    await UserController.update_email(current_user, data.email)
    return {'status': 'ok'}


@app.post("/users/me/update/phone")
async def user_update_email(data: UserUpdatePhone, current_user: UserEntry = Depends(get_current_user)):
    """
    Пользователь имеет возможность изменить телефон (пользователь должен подтвердить телефон перед изменением).
    Отправка кода подтверждения происходит на почту пользователя, т.к. у разработчика были проблемы с поиском
    бесплатного сервиса отправки СМС.
    """
    await UserController.update_phone(current_user, data.phone)
    return {'status': 'ok'}


@app.post("/users/me/update/confirmation")
async def user_update_confirmation(data: UserConfirmation, current_user: UserEntry = Depends(get_current_user)):
    """
    Эндпоинт для подтверждения пользователем изменения почты или телефона по отправленному коду.
    """
    user_id = await UserController.confirm_update_request(current_user, data.confirmation_code)
    return {'user_id': user_id}


@app.post("/users/me/update/")
async def user_update_fio(data: UserUpdate, current_user: UserEntry = Depends(get_current_user)):
    """
    Пользователь имеет возможность изменить свои данные (Имя Фамилия Отчество).
    """
    user_id = await UserController.update_fio(current_user, data.first_name, data.last_name, data.middle_name)
    return {'user_id': user_id}

# Accounts

@app.post("/accounts/")
async def account_create(data: AccountCreate, current_user: UserEntry = Depends(get_current_user)):
    """
    Пользователь имеет возможность открыть лицевой счет (в один момент не более одного счета на валюту),
    но у пользователя может быть много счетов.
    """
    account_id = await AccountController.create(data=data, user=current_user)
    return {'account_id': account_id}


@app.get("/accounts/")
async def account_get(account_id: str = None, current_user: UserEntry = Depends(get_current_user)):
    """
    Пользователь имеет возможность посмотреть состояние лицевого счета/лицевых счетов.
    """
    if account_id:
        return await AccountController.get_by_id(account_id=account_id, user=current_user)
    else:
        return await AccountController.get_by_user(user=current_user)


@app.post("/accounts/delete/")
async def account_delete(account_id: str, current_user: UserEntry = Depends(get_current_user)):
    """
    Пользователь имеет возможность закрыть лицевой счет.
    """
    await AccountController.delete(account_id=account_id, user=current_user)
    return {'status': 'ok'}

# Account operations

@app.post("/accounts/operations/")
async def account_operation_create(data: AccountOperationCreate, current_user: UserEntry = Depends(get_current_user)):
    """
    Пользователь имеет возможность пополнить лицевой счет, снять деньги с лицевого счета, отправить определенную
    денежную сумму другому пользователю банка на его банковский счет (для этого заполните поле recipient_account).
    При переводе с одного счета на другой учитываются валюты.
    """
    account_operation_id = await AccountOperationController.create(data=data, user=current_user)
    return {'account_operation_id': account_operation_id}


@app.get("/accounts/operations/")
async def account_operation_get(account_id: str = None, current_user: UserEntry = Depends(get_current_user)):
    """
    Пользователь имеет возможность посмотреть историю операций по счету (в том числе, кому перевел, сколько перевел,
    в какой валюте), по всем счетам.
    """
    if account_id:
        await AccountController.get_by_id(account_id=account_id, user=current_user)
        account_operations = await AccountOperationController.get_by_account(account_id=account_id)
    else:
        account_operations = await AccountOperationController.get_by_user(user=current_user)
    return account_operations


# Currencies
# Administrator role is not implemented, therefore user authorization is not required for operations with currencies.

@app.post("/currencies/")
async def currency_create(data: CurrencyCreate):
    """
    Эндпоинт для добавления новых валют.
    """
    currency_id = await CurrencyController.create(char_code=data.char_code)
    return {'currency_id': currency_id}


@app.post("/currencies/fetch/")
async def currency_fetch():
    """
    Эндпоинт для определения валютного курса, если лень ждать автоматической задачи, исполняемой раз в 24 часа.
    """
    await CurrencyController.fetch_currencies(is_schedule_task=False)
    return {'status': 'ok'}

# Entry point

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
