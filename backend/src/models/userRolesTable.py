from sqlalchemy import Column, Table, Uuid

from database.databaseBaseModel import Base

user_roles_table = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Uuid(as_uuid=True), primary_key=True),
    Column("role_id", Uuid(as_uuid=True), primary_key=True),
)
