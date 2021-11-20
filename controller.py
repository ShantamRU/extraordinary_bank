import json
import os
import random
import smtplib
import string
import uuid
from datetime import timedelta, datetime

import requests
from fastapi import HTTPException
from jose import JWTError, jwt
from starlette import status

from db import db
from passlib.context import CryptContext
from schema import UserCreate, UserEntry, AccountCreate, AccountEntry, CurrencyEntry, AccountOperationCreate, \
    AccountOperationEntry, TokenData, UpdateRequestEntry

from models import users, update_requests, currencies, accounts, account_operations


class User:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    @classmethod
    async def get_user(cls, user_id: str = None, email: str = None, phone: str = None):
        """
        Returns user data
        :param user_id: user id (optional)
        :param email: user email (optional)
        :param phone: user phone (optional)
        :return: user data if user exists and None otherwise
        """
        query = users.select()
        if user_id:
            query = query.where(users.c.id == user_id)
        if email:
            query = query.where(users.c.email == email)
        if phone:
            query = query.where(users.c.email == phone)

        user = await db.fetch_one(query)
        if user:
            return UserEntry(**user)
        else:
            return None

    @staticmethod
    def send_email(recipients, subject, body):
        """
        Sends email via google smtp server
        :param recipients: email recipients
        :param subject: email title
        :param body: email body
        :return: None
        """
        email_sender = os.environ['GOOGLE_USERNAME']
        message = """From: %s\nTo: %s\nSubject: %s\n\n%s
        """ % (email_sender, ", ".join(recipients), subject, body)
        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.ehlo()
            server.starttls()
            server.login(email_sender, os.environ['GOOGLE_PASSWORD'])
            server.sendmail(email_sender, recipients, message)
            server.close()
            print('successfully sent the mail')
        except:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Email service error')

    @classmethod
    async def register(cls, data: UserCreate):
        """
        Register new user
        :param data: user data
        :return: created user id
        """
        letters = string.ascii_lowercase + string.ascii_uppercase + string.digits
        user = UserEntry(
            id=str(uuid.uuid4()),
            first_name=data.first_name,
            last_name=data.last_name,
            middle_name=data.middle_name,
            email=data.email,
            password=cls.pwd_context.hash(data.password),
            phone=data.phone,
            confirmation_code=''.join(random.choice(letters) for _ in range(6)))

        query = users.insert().values(user.dict())
        await db.execute(query)

        # Send confirmation code to the user email
        cls.send_email(
            recipients=[user.email],
            subject='Email confirmation',
            body='Please confirm your email using this code: {}'.format(user.confirmation_code))
        return user.id

    @classmethod
    async def authenticate_user(cls, username: str, password: str):
        """
        User authentication
        :param username: user email or phone
        :param password: user password (not hashed)
        :return: user data
        """
        def raise_401_exception(detail):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=detail,
                headers={"WWW-Authenticate": "Bearer"})

        query = users.select().where((users.c.email == username) | (users.c.phone == username))
        user = await db.fetch_one(query)
        user_data = UserEntry(**user) if user else None
        if user_data and cls.pwd_context.verify(password, user_data.password):
            if not user_data.confirmation_code:
                return user_data
            else:
                raise_401_exception("User email not confirmed yet")
        else:
            raise_401_exception("Incorrect username or password")

    @staticmethod
    def create_access_token(email: str):
        """
        Returns new access token for authenticated user
        :param email: user email
        :return: access token
        """
        to_encode = {"sub": email}
        expire = datetime.utcnow() + timedelta(minutes=int(os.environ['ACCESS_TOKEN_EXPIRE_MINUTES']))
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, os.environ['SECRET_KEY'], algorithm=os.environ['ALGORITHM'])
        return encoded_jwt

    @classmethod
    async def get_current_user(cls, token: str):
        """
        Returns data of user by access token
        :param token: access token
        :return: user data if user authenticated or None otherwise
        """
        try:
            payload = jwt.decode(token, os.environ['SECRET_KEY'], algorithms=[os.environ['ALGORITHM']])
            username: str = payload.get("sub")
            if username is None:
                return None
            token_data = TokenData(username=username)
        except JWTError:
            return None
        query = users.select().where(users.c.email == token_data.username)
        user = await db.fetch_one(query)
        if user is None:
            return None
        else:
            return UserEntry(**user)

    @classmethod
    async def email_confirmation(cls, confirmation_code: str):
        """
        Email confirmation after registration
        :param confirmation_code: email confirmation code
        :return: confirmed user id
        """
        query = users.update().\
            where(users.c.confirmation_code == confirmation_code).\
            values(confirmation_code=None). \
            returning(users.c.id)
        user_id = await db.execute(query)
        return user_id

    @classmethod
    async def update_password(cls, user: UserEntry, old_password: str, new_password: str):
        """
        Updates user password
        :param user: current user data
        :param old_password: old user password
        :param new_password: new user password
        :return: updated user id
        """
        if not cls.pwd_context.verify(old_password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Incorrect password',
                headers={"WWW-Authenticate": "Bearer"})
        query = users.update(). \
            where(users.c.id == user.id). \
            values(password=cls.pwd_context.hash(new_password)). \
            returning(users.c.id)
        user_id = await db.execute(query)
        return user_id

    @classmethod
    async def update_email(cls, user: UserEntry, email: str):
        """
        Creates a request to update the user email
        :param user: current user data
        :param email: new user email
        :return: None
        """
        data = UpdateRequestEntry(
            id=str(uuid.uuid4()),
            user_id=user.id,
            conditions={'email': email},
            confirmation_code=''.join(random.choice(string.digits) for _ in range(6)))

        query = update_requests.insert().values(data.dict())
        await db.execute(query)
        cls.send_email(
            recipients=[user.email],
            subject='Email changing',
            body='Please confirm your email changing using this code: {}'.format(data.confirmation_code))

    @classmethod
    async def update_phone(cls, user: UserEntry, phone: str):
        """
        Creates a request to update the user phone number
        :param user: current user data
        :param phone: new user phone
        :return: None
        """
        data = UpdateRequestEntry(
            id=str(uuid.uuid4()),
            user_id=user.id,
            conditions={'phone': phone},
            confirmation_code=''.join(random.choice(string.digits) for _ in range(6)))

        query = update_requests.insert().values(data.dict())
        await db.execute(query)
        cls.send_email(
            recipients=[user.email],
            subject='Phone changing',
            body='Please confirm your phone changing using this code: {}'.format(data.confirmation_code))

    @classmethod
    async def confirm_update_request(cls, user: UserEntry, confirmation_code: str):
        """
        Confirmation of changes
        :param user: current user data
        :param confirmation_code: confirmation code
        :return: updated user id
        """
        query = update_requests.delete(). \
            where(update_requests.c.user_id == user.id, update_requests.c.confirmation_code == confirmation_code). \
            returning(update_requests.c.conditions)
        conditions = await db.execute(query)
        if conditions:
            query = users.update(). \
                where(users.c.id == user.id). \
                values(json.loads(conditions)). \
                returning(users.c.id)
            user_id = await db.execute(query)
            return user_id
        else:
            return None

    @classmethod
    async def update_fio(cls, user: UserEntry, first_name: str, last_name: str, middle_name: str):
        """
        Updates user fio
        :param user: current user data
        :param first_name: new first name
        :param last_name: new last name
        :param middle_name: new middle name
        :return: updated user id
        """
        query = users.update(). \
            where(users.c.id == user.id). \
            values(first_name=first_name, last_name=last_name, middle_name=middle_name). \
            returning(users.c.id)
        user_id = await db.execute(query)
        return user_id


class Account:
    @classmethod
    async def create(cls, data: AccountCreate, user: UserEntry):
        """
        Creates new bank account
        :param data: bank account data
        :param user: current user data
        :return: created account id
        """
        await Currency.get_by_char_code(char_code=data.currency_code)
        account_data = AccountEntry(
            id=str(uuid.uuid4()),
            user_id=user.id,
            currency_code=data.currency_code,
            amount=data.amount)

        query = accounts.select().where(accounts.c.user_id == user.id, accounts.c.currency_code == data.currency_code)
        account = await db.fetch_one(query)
        if not account:
            query = accounts.insert().values(account_data.dict())
            await db.execute(query)
            return account_data.id
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Account with the same currency already exists')

    @classmethod
    async def get_by_id(cls, account_id: str, user: UserEntry = None):
        """
        Returns bank account by account id
        :param account_id: account id
        :param user: current user data
        :return: account data
        """
        if user:
            query = accounts.select().where(accounts.c.id == account_id, accounts.c.user_id == user.id)
        else:
            query = accounts.select().where(accounts.c.id == account_id)
        account = await db.fetch_one(query)
        if account:
            return AccountEntry(**account)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Account not found')

    @classmethod
    async def get_by_user(cls, user: UserEntry):
        """
        Returns all bank accounts of the user
        :param user: current user data
        :return: list of accounts data
        """
        query = accounts.select().where(accounts.c.user_id == user.id)
        response = await db.fetch_all(query)
        accounts_list = [AccountEntry(**item) for item in response]
        return accounts_list

    @classmethod
    async def delete(cls, account_id: str, user: UserEntry):
        """
        Closes bank account (full delete, archive not implemented)
        :param account_id: account id
        :param user: current user data
        :return: deleted account id
        """
        query = accounts.delete(). \
            where(accounts.c.id == account_id, accounts.c.user_id == user.id). \
            returning(accounts.c.id)
        account_id = await db.execute(query)
        if account_id:
            return account_id
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Account not found')


class AccountOperation:
    @classmethod
    async def create(cls, data: AccountOperationCreate, user: UserEntry):
        """
        Creates bank account operation (replenish a personal account, withdraw money from a personal account, send
        a certain amount of money to another bank user to his bank account).
        :param data: account operation data
        :param user: current user data
        :return: created account operation data
        """
        account = await Account.get_by_id(account_id=data.account_id, user=user)

        if data.recipient_account:
            sender_currency = await Currency.get_by_char_code(account.currency_code)
            recipient_account = await Account.get_by_id(account_id=data.recipient_account)
            recipient_user = await User.get_user(user_id=recipient_account.user_id)
            recipient_currency = await Currency.get_by_char_code(char_code=recipient_account.currency_code)
            recipient_amount_diff = -data.amount_diff * sender_currency.value / recipient_currency.value

            sender_description = 'Денежный перевод на сумму {} {}. Получатель: {}.'.\
                format(abs(data.amount_diff), sender_currency.char_code, recipient_user.get_fio())
            recipient_description = 'Денежный перевод на сумму {} {}. Отправитель: {}.'.\
                format(abs(recipient_amount_diff), recipient_currency.char_code, user.get_fio())

            # Sender
            account_operation_data = AccountOperationEntry(
                id=str(uuid.uuid4()),
                account_id=data.account_id,
                amount_diff=data.amount_diff,
                created_at=datetime.utcnow(),
                description=sender_description)
            query = account_operations.insert().values(account_operation_data.dict())
            await db.execute(query)

            query = accounts.update(). \
                where(accounts.c.id == account.id). \
                values(amount=accounts.c.amount + data.amount_diff)
            await db.execute(query)

            # Recipient
            recipient_account_operation_data = AccountOperationEntry(
                id=str(uuid.uuid4()),
                account_id=data.recipient_account,
                amount_diff=recipient_amount_diff,
                created_at=datetime.utcnow(),
                description=recipient_description)
            query = account_operations.insert().values(recipient_account_operation_data.dict())
            await db.execute(query)

            query = accounts.update(). \
                where(accounts.c.id == recipient_account_operation_data.account_id). \
                values(amount=accounts.c.amount + recipient_amount_diff)
            await db.execute(query)

        else:
            account_operation_data = AccountOperationEntry(
                id=str(uuid.uuid4()),
                account_id=data.account_id,
                amount_diff=data.amount_diff,
                created_at=datetime.utcnow(),
                description=data.description)
            query = account_operations.insert().values(account_operation_data.dict())
            await db.execute(query)

            query = accounts.update().\
                where(accounts.c.id == account.id).\
                values(amount=accounts.c.amount + data.amount_diff)
            await db.execute(query)

        return account_operation_data.id

    @classmethod
    async def get_by_account(cls, account_id: str):
        """
        Returns all bank account operations.
        :param account_id: account id
        :return: list of account operations
        """
        query = account_operations.select().\
            where(account_operations.c.account_id == account_id).\
            order_by(account_operations.c.created_at)
        response = await db.fetch_all(query)
        account_operations_list = [AccountOperationEntry(**item) for item in response]
        return account_operations_list

    @classmethod
    async def get_by_user(cls, user: UserEntry):
        """
        Returns all bank account operations of all user accounts.
        :param user: current user data
        :return: dict of entries like ('account_id': list of account operations)
        """
        accounts_list = await Account.get_by_user(user=user)
        response = {}
        for account in accounts_list:
            account_operations_list = await cls.get_by_account(account_id=account.id)
            response[account.id] = account_operations_list
        return response


class Currency:
    @classmethod
    async def create(cls, char_code: str):
        """
        Add currency from the Central Bank of Russian Federation to the system
        :param char_code: currency char code
        :return: data of the created currency
        """
        response = requests.get(os.environ['CURRENCIES_BANK_URL'])
        json_data = response.json()

        if char_code in json_data['Valute'] or char_code == 'RUB':
            currency_data = CurrencyEntry(
                char_code=char_code,
                name='Российский рубль' if char_code == 'RUB' else json_data['Valute'][char_code]['Name'],
                value=1. if char_code == 'RUB' else json_data['Valute'][char_code]['Value'])
            query = currencies.insert().values(currency_data.dict())
            await db.execute(query)
            return currency_data
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid currency')

    @classmethod
    async def get_by_char_code(cls, char_code: str):
        """
        Returns data of currency
        :param char_code: currency char code
        :return: currency data
        """
        query = currencies.select().where(currencies.c.char_code == char_code)
        currency = await db.fetch_one(query)
        if currency:
            return CurrencyEntry(**currency)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Currency not found')

    @classmethod
    async def get_all(cls):
        """
        Returns data of all currencies
        :return: list of currencies data
        """
        query = currencies.select()
        currency = await db.fetch_all(query)
        return [CurrencyEntry(**item) for item in currency]

    @classmethod
    async def fetch_currencies(cls, is_schedule_task: bool = False):
        """
        Updates currency values from outer bank
        :return: None
        """
        response = requests.get(os.environ['CURRENCIES_BANK_URL'])
        json_data = response.json()
        if is_schedule_task:
            await db.connect()

        currencies_list = await cls.get_all()
        for currency in currencies_list:
            if currency.char_code not in json_data['Valute']:
                continue
            currency_data = json_data['Valute'][currency.char_code]
            query = currencies.update().\
                where(currencies.c.char_code == currency.char_code).\
                values(value=currency_data['Value'])
            await db.execute(query)
        if is_schedule_task:
            await db.disconnect()
