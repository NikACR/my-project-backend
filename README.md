<<<<<<< HEAD
# my-project-backend
=======
README – Backend pro Restauraci (Flask & Flask Smorest)
Toto README je určeno všem vývojářům, kteří budou pracovat na backendové části REST API pro restauraci. Najdete zde popis struktury, klíčových souborů, konfigurace, způsob spuštění, migrací, testování i podrobnou analýzu kódu po jednotlivých modulech.

________________________________________

1. Účel projektu
Backend poskytuje REST API pro správu zákazníků, rezervací, objednávek, menu, hodnocení a notifikací. Je postaven na:
•	Python 3.13 + Flask 3.1
•	Flask Smorest pro OpenAPI/Swagger generování a validaci dat (Marshmallow)
•	SQLAlchemy 2.x + Alembic pro ORM a migrace
•	Flask JWT Extended pro autentizaci pomocí JWT
•	pytest pro automatizované testy

________________________________________

2. Struktura projektu
backend/
├── app/
│   ├── api/
│   │   ├── __init__.py    # Blueprint definice (api_bp)
│   │   ├── routes.py      # Všechny CRUD endpointy + register_crud helper
│   │   └── auth.py        # Login a /me endpointy (JWT)
│   ├── __init__.py        # create_app() Factory
│   ├── config.py          # Konfigurace (development/testing/production)
│   ├── db.py              # SQLAlchemy + Flask Migrate init
│   ├── models.py          # Definice ORM modelů (db.Model)
│   └── schemas.py         # Marshmallow schémata (validace & serializace)
├── migrations/            # Alembic migrace
├── tests/                 # Pytest testy pro API endpointy
├── Dockerfile             # Docker image pro backend
├── run.py                 # CLI příkazy (seed-db, shell) + spuštění aplikace
└── requirements.txt       # Python závislosti

________________________________________

3. Konfigurace a spuštění
1.	.env – proměnné prostředí (např. DATABASE_URL, SECRET_KEY, JWT_SECRET_KEY,
FLASK_CONFIG, DEV_JWT_TOKEN). Nikdy nevkládat do Gitu.
2.	Výběr configu:
3.	export FLASK_CONFIG=development    # nebo testing/production
4.	Spuštění aplikace:
5.	flask run  # nebo python run.py
6.	Seed databáze (demo data):
7.	flask seed-db
8.	Swagger UI (interaktivní dokumentace):
Otevřete v prohlížeči http://localhost:8000/api/docs/swagger.

________________________________________

4. Podsložky a hlavní moduly
4.1 app/__init__.py (Application Factory)
•	Funkce create_app(config_name=None, config_override=None):
o	Načte Config třídu podle FLASK_CONFIG.
o	Inicializuje Flask, db.init_app(), migrate.init_app(), JWTManager, Api(app).
o	Registruje Blueprints: api_bp (všechny /api/... endpointy) a auth_bp (/api/auth).
o	Ve development injektuje DEV_JWT_TOKEN před každým requestem, pokud chybí Authorization header.
o	Definuje error handlery pro 404 a 422.
4.2 app/config.py
•	Základní třída Config + dědičné DevelopmentConfig, TestingConfig, ProductionConfig.
•	Nastavuje SQLALCHEMY_DATABASE_URI, JWT_SECRET_KEY, OpenAPI metadata (SWAGGER UI).
4.3 app/db.py
•	db = SQLAlchemy(), migrate = Migrate() – bez vazby na konkrétní aplikaci.
4.4 app/models.py
Definice ORM modelů:
•	Zakaznik: jméno, e mail, telefon, zahashované heslo (_password), vztahy na Rezervace, Objednavky, Hodnoceni, jeden ku jednomu na VernostniUcet.
•	VernostniUcet: body, datum založení, FK na Zakaznik (cascade delete).
•	Rezervace: datum/čas, počet osob, FK na Zakaznik, Stul nebo Salonek (CheckConstraint – musí být buď stůl, nebo salonek), vztah na Notifikace.
•	Objednavka, PolozkaObjednavky, Platba, Hodnoceni, Notifikace – vazby mezi tabulkami.
•	PolozkaMenu, Alergen, PolozkaMenuAlergen – reprezentace menu a alergenů.
•	JidelniPlan, PolozkaJidelnihoPlanu – denní plány s položkami.
4.5 app/schemas.py
•	Marshmallow schémata pro validaci a serializaci.
•	Summary schémata (např. RezervaceSummarySchema) pro vnořené seznamy.
•	Create schémata (load_only) a Schema (dump_only) pro response.
•	Custom @post_dump a @validates_schema pro kontrolu a úpravu dat.

________________________________________

5. API Endpointy
5.1 app/api/__init__.py
•	Vytvoří api_bp = Blueprint("api", __name__, url_prefix="/api").
•	Importuje routes.py, auth.py registruje později v factory.
5.2 app/api/routes.py
1.	ZakaznikList a ZakaznikItem:
o	CRUD pro /api/zakaznik[/:id].
o	Všechny operace chráněné @jwt_required() (GET, POST, PUT, DELETE).
o	Při POST se automaticky vytvoří i VernostniUcet.
o	Error handling: IntegrityError → 409, not found → 404.
2.	register_crud() helper:
o	Generuje CRUD endpointy pro ostatní modely (ucet, stul, salonek, akce, objednavka, atd.) s jedním řádkem.
o	Veřejné – bez ochrany JWT.
5.3 app/api/auth.py
•	LoginResource (POST /api/auth/login):
o	Načte Email + Password, ověří pomocí Zakaznik.check_password(), vytvoří access token (identity = str(id)).
•	MeResource (GET /api/auth/me):
o	Vrací základní info o přihlášeném zákazníkovi (id, email, jmeno, prijmeni).
o	Chráněno @jwt_required().

________________________________________

6. Spuštění & Migrace
1.	Alembic migrace:
2.	alembic revision --autogenerate -m "Popis změny"
3.	alembic upgrade head
4.	Demo data:
5.	flask seed-db
6.	Testy:
7.	pytest -v

________________________________________

7. Docker & Dev Containers
•	Dockerfile (varianty s/bez jq): instaluje Python závislosti, nastavuje FLASK_APP, FLASK_DEBUG.
•	Doporučené otevřít ve VS Code Dev Container pro konzistentní prostředí.

________________________________________

8. Analýza kódu (průvodce soubory)
Níže najdete stručný popis všech hlavních souborů a jejich role:
Soubor	Popis
app/__init__.py	Application Factory – sestavení Flask instance, registrace rozšíření a Blueprintů
app/config.py	Nastavení prostředí (development/testing/production), načítání .env
app/db.py	Inicializace SQLAlchemy (db) a Flask-Migrate (migrate)
app/models.py	Definice všech tabulek jako SQLAlchemy modelů + vztahy a validace
app/schemas.py	Marshmallow schémata: validace requestů, serializace response
app/api/__init__.py	Vytvoření a export Blueprintu api_bp
app/api/routes.py	CRUD endpointy: vlastní zákazníci + generický register_crud pro ostatní entity
app/api/auth.py	Autentizace: login (/login) a informace o uživateli (/me)
run.py	CLI příkazy (seed-db), shell context, spuštění aplikace
migrations/	Automigrované skripty pro změny v DB
tests/	Pytest testy zahrnující CRUD operace pro /api/zakaznik
Dockerfile	Definice Docker image pro backend, nastavení prostředí
requirements.txt	Přesný seznam Python balíčků s verzemi


