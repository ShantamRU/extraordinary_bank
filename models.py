from datetime import datetime

from sqlalchemy import Table, Column, String, ForeignKey, Integer, Float, DateTime
from sqlalchemy.dialects.postgresql import JSON
from db import metadata

users = Table(
    'users',
    metadata,
    Column('id', String, primary_key=True),
    Column('first_name', String),
    Column('last_name', String),
    Column('middle_name', String),
    Column('email', String, unique=True, nullable=False),
    Column('password', String, nullable=False),
    Column('phone', String, unique=True, nullable=False),
    Column('confirmation_code', String))

update_requests = Table(
    'update_requests',
    metadata,
    Column('id', String, primary_key=True),
    Column('user_id', ForeignKey('users.id'), nullable=False),
    Column('conditions', JSON, nullable=False),
    Column('confirmation_code', String, nullable=False))

currencies = Table(
    'currencies',
    metadata,
    Column('char_code', String, primary_key=True),
    Column('name', String, nullable=False),
    Column('value', Float, nullable=False))

accounts = Table(
    'accounts',
    metadata,
    Column('id', String, primary_key=True),
    Column('user_id', ForeignKey('users.id'), nullable=False),
    Column('currency_code', ForeignKey('currencies.char_code'), nullable=False),
    Column('amount', Float, nullable=False))

account_operations = Table(
    'account_operations',
    metadata,
    Column('id', String, primary_key=True),
    Column('account_id', ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False),
    Column('amount_diff', Float, nullable=False),
    Column('created_at', DateTime, default=datetime.utcnow, nullable=False),
    Column('description', String))
