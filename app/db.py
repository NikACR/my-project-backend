# app/db.py

from flask_sqlalchemy import SQLAlchemy    # importuje SQLAlchemy ORM pro Flask
# importuje Migrate pro správu databázových migrací
from flask_migrate import Migrate

# vytvoří instanci ORM, kterou budeme registrovat v create_app
db = SQLAlchemy()
# vytvoří instanci migrací, také registrovanou v create_app
migrate = Migrate()
