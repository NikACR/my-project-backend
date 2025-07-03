# app/api/__init__.py

from flask_smorest import Blueprint

# jednou definujeme blueprint
api_bp = Blueprint("api", __name__, url_prefix="/api")

# import routes spustí decorators, které registrují všechny endpointy
from . import routes  # noqa
