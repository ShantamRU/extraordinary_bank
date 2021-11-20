# Незаурядный банк

### Используемые технологии
- Сервер: Python FastAPI
- База данных: Postgres + Alembic + SQLAlchemy
- Брокер сообщений: RabbitMQ
- Менеджер фоновых задач: Celery
- Среда выполнения: Docker

### Настройка окружения
Задайте значения GOOGLE_USERNAME и GOOGLE_PASSWORD в файле .env - логин и пароль гугл аккаунта, с которого Вы планируете
осуществлять email рассылку. Аккаунт должен иметь разрешение на использование стронними приложениями 
(посмотрите пункт Setting up a Gmail Account for Development https://medium.com/paul-zhao-projects/sending-emails-with-python-c084b55a2857)

### Запуск проекта
Выполните команды в терминале:
```
cd extraordinary_bank
docker-compose build
docker-compose up
```
Swagger документация будет доступна по адресу http://127.0.0.1:8000/docs

### Начало работы с API

- Изначально база данных будет пустая, перейдите к эндпоинту POST /currencies/ (http://127.0.0.1:8000/docs#/default/currency_create_currencies__post)
и отравьте поочередно три запроса со значениями: RUB, USD, EUR. Курсы валют будут автоматически взяты с сайта 
Центрального Банка Российской Федерации.
- Регистрация пользователя http://127.0.0.1:8000/docs#/default/register_user_users__post
- Подтвердите почту по коду, отправленному Вам на почту (http://127.0.0.1:8000/docs#/default/user_email_confirmation_users_email_confirmation__post), без этого аутентификация не будет работать для вашего пользователя.
- Авторизуйтесь через кнопку 'Authorize' в верхнем правом углу (в поле username можно ввести как email, так и номер телефона).

### Доступные сценарии:
- **Изменение данных пользователя**
    
  Используйте один из четырех эндпоинтов:
  - http://127.0.0.1:8000/docs#/default/user_update_password_users_me_update_password_post
  - http://127.0.0.1:8000/docs#/default/user_update_email_users_me_update_email_post
  - http://127.0.0.1:8000/docs#/default/user_update_email_users_me_update_phone_post
  - http://127.0.0.1:8000/docs#/default/user_update_fio_users_me_update__post
  
  При обновлении email и телефона, данные не будут изменены сразу, Вам на почту придет письмо с кодом подтверждения.
  Для подтверждения операции используйте эндпоинт http://127.0.0.1:8000/docs#/default/user_update_confirmation_users_me_update_confirmation_post

  После смены email, Ваш токен перестанет действовать, перелогиньтесь, чтобы восстановить доступ.


- **Работа со своими лицевыми счетами**
  - Чтобы создать счет, используйте эндпоинт http://127.0.0.1:8000/docs#/default/account_create_accounts__post
    
    Вы можете создать несколько счетов для одного пользователя с разными валютами. 
  - Чтобы просмотреть все свои счета используйте эндпоинт http://127.0.0.1:8000/docs#/default/account_get_accounts__get с 
    нулевым полем account_id 
  - Чтобы закрыть лицевой счет, используйте эндпоинт http://127.0.0.1:8000/docs#/default/account_delete_accounts_delete__post
  - Чтобы снять деньги со счета, используйте эндпоинт http://127.0.0.1:8000/docs#/default/account_operation_create_accounts_operations__post
  с отрицательным значением amount_diff и удалите поле recipient_account. 
  - Чтобы пополнить счет, используйте эндпоинт http://127.0.0.1:8000/docs#/default/account_operation_create_accounts_operations__post
  с положительным значением amount_diff и удалите поле recipient_account. 
  - Чтобы перевести деньги между своими счетами используйте эндпоинт http://127.0.0.1:8000/docs#/default/account_operation_create_accounts_operations__post
  c отрицательным значением amount_diff и используйте идентификатор своего счета, на который переводятся средства, в поле 
  recipient_account 
  - Вы можете посмотреть операции по счету здесь: http://127.0.0.1:8000/docs#/default/account_operation_get_accounts_operations__get
    
    и изменение состояние счета здесь: http://127.0.0.1:8000/docs#/default/account_get_accounts__get
- **Перевод другому пользователю**
  - Чтобы перевести деньги другому клиенту банка используйте эндпоинт http://127.0.0.1:8000/docs#/default/account_operation_create_accounts_operations__post
  c отрицательным значением amount_diff и используйте идентификатор счета другого клиента, на который переводятся средства, в поле 
  recipient_account 
  - Вы можете посмотреть операции по счету здесь: http://127.0.0.1:8000/docs#/default/account_operation_get_accounts_operations__get
    
    и изменение состояние счета здесь: http://127.0.0.1:8000/docs#/default/account_get_accounts__get
- **Добавление новых валют**
  - Чтобы добавить валюту, используйте эндпоинт http://127.0.0.1:8000/docs#/default/currency_create_currencies__post

    Посмотреть доступные значения для поля char_code можно здесь: https://www.cbr-xml-daily.ru/daily_json.js
    в поле Valute