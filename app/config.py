# app/config.py

# modul pro práci s OS a proměnnými prostředí
import os
from dotenv import load_dotenv                # funkce pro načtení .env souboru
from datetime import timedelta                # přidáno pro expiraci tokenů

# ── Sestavení cesty k .env ───────────────────────────────────────────────────
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DOTENV_PATH = os.path.join(BASE_DIR, "..", ".env")

# ── Načteme proměnné z .env do os.environ (všechny proměnné), přepišeme i stávající ──
load_dotenv(DOTENV_PATH, override=True)


class Config:
    """Základní nastavení společné pro všechny režimy."""

    JSON_AS_ASCII = False
    #   False = povolíme české znaky v JSON odpovědích (nebudou eskapovány)

    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "vychozi_slabý_klíč_pro_vývoj"
    )
    #   klíč pro Flask session, CSRF tokeny, cookies…

    JWT_SECRET_KEY = os.environ.get(
        "JWT_SECRET_KEY",
        "tajnyklictoken"
    )
    #   klíč, kterým se podepisují a ověřují JWT tokeny

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    #   vypíná sledování změn ORM → lepší výkon, méně varování

    SQLALCHEMY_ECHO = False
    #   False = nevypisovat raw SQL dotazy do konzole

    # ── Metadata API pro Swagger/OpenAPI ────────────────────────────────
    API_TITLE = "Informační Systém REST API"
    API_VERSION = "v1"

    # ── Cesty a zdroje pro Swagger UI ─────────────────────────────────
    OPENAPI_VERSION = "3.0.2"
    OPENAPI_URL_PREFIX = "/api/docs"
    OPENAPI_SWAGGER_UI_PATH = "/swagger"
    OPENAPI_SWAGGER_UI_URL = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"

    # ── Definice zabezpečení v dokumentaci ───────────────────────────────
    # změna na apiKey, aby Swagger UI přijalo celý řetězec „Bearer <token>“
    OPENAPI_COMPONENTS = {
        "securitySchemes": {
            "bearerAuth": {
                "type":        "apiKey",
                "in":          "header",
                "name":        "Authorization",
                "description": "Vlož celý řetězec `Bearer <váš_token>`"
            }
        }
    }
    OPENAPI_SECURITY = [{"bearerAuth": []}]
    OPENAPI_SWAGGER_UI_CONFIG = {"persistAuthorization": True}
    API_SPEC_OPTIONS = {
        "security": [{"bearerAuth": []}],
        "components": OPENAPI_COMPONENTS
    }

    # ── EXPIRACE JWT TOKENŮ ČTENÁ Z .ENV ───────────────────────────────
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", 15))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        days=int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRES_DAYS", 30))
    )


class DevelopmentConfig(Config):
    """Nastavení pro vývojové prostředí."""

    DEBUG = True   # zapne auto-reload a detailní chyby
    SQLALCHEMY_ECHO = True   # vypisovat raw SQL pro ladění
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://user:heslo@localhost/dev_db"
    )
    #   URI pro vývojovou DB

    # — místo nekonečné platnosti nyní expirace z .env —
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", 15))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        days=int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRES_DAYS", 30))
    )


class TestingConfig(Config):
    """Nastavení pro testovací běh."""

    TESTING = True    # zapne testovací režim Flaska
    WTF_CSRF_ENABLED = False   # vypne CSRF ochranu v testech
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TEST_DATABASE_URL",
        "sqlite:///:memory:"
    )
    #   in-memory SQLite pro rychlé testy


class ProductionConfig(Config):
    """Nastavení pro produkční prostředí."""

    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.environ["DATABASE_URL"]
    #   produkční DB URI (musí být definováno v .env)

    # — expirace tokenů i v produkci (bere se z Config) —
    # (není třeba znovu deklarovat, ale můžete přepsat analogicky výše)


# ── Mapa názvů režimů na třídy konfigurace ──────────────────────────────────
config_by_name = {
    "development": DevelopmentConfig,
    "testing":     TestingConfig,
    "production":  ProductionConfig,
    "default":     DevelopmentConfig
}
