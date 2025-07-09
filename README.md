# Backend REST API pro správu restaurace

## 1. Představení projektu
**Žádné ukázky kódu, jen vysvětlení.**

- **Zadání:**  
  Backendové REST API pro kompletní správu restaurace – od zákazníků přes rezervace a objednávky až po platby a notifikace.

- **Technologie:**
  - **Python 3.13 + Flask** – lehký, modulární webový framework  
  - **Flask-Smorest** – automatická generace Swagger/OpenAPI a integrace Marshmallow pro validaci dat  
  - **SQLAlchemy + Alembic** – objektově-relační mapování pro práci s databází a správa migrací  
  - **Flask-JWT-Extended** – bezpečná autentizace a autorizace pomocí JWT  
  - **pytest** – psaní jednotkových a integračních testů  

- **Struktura projektu:**
- app/api/ → definice HTTP endpointů (routes.py, auth.py)
app/models.py → deklarace databázových entit a vztahů
app/schemas.py → Marshmallow schémata pro validaci vstupu a serializaci výstupu
app/db.py → inicializace databáze a migrací
app/config.py → nastavení připojení k DB, konfigurační parametry
migrations/ → Alembic skripty pro změny schématu
tests/ → automatizované testy
run.py → skripty pro seed-db, spouštění aplikace, REPL


## 2. UML diagramy
*(Externě připravené v PPT/PDF.)*

- **Class diagram** – vizualizace entit (`Zakaznik`, `Rezervace`, `Objednavka`, `Platba` atd.) a jejich asociací (1:N, N:M).  
- **Use-case diagram** – ukazuje hlavní scénáře, např. přihlášení uživatele, vytvoření rezervace, zadání objednávky, provedení platby.

## 3. Autentizace a autorizace (detailně)
V této části ukážeme celý tok od přípravy účtu, přes login, zpracování chyb a obnova tokenu, až po kontrolu rolí a smazání zákazníka podle byznys-pravidel.

### 3.1 Seed skript – vytvoření platného staff účtu
**Umístění:** `run.py` nebo skript pro `flask seed-db`
```python
from app.models import db, Zakaznik, Role

# 1) Zajistíme existenci role "staff"
staff_role = Role.query.filter_by(name="staff").first()
if not staff_role:
  staff_role = Role(name="staff")
  db.session.add(staff_role)
  db.session.commit()

# 2) Vytvoříme uživatele Anna Nováková se staff rolí
staff1 = Zakaznik(
  jmeno="Anna", prijmeni="Nováková",
  email="anna.staff@example.com", telefon="600111222"
)
staff1.password = "heslo123"   # setter automaticky zahashuje pomocí Bcrypt
staff1.roles.append(staff_role)
db.session.add(staff1)
db.session.commit()

1. Ověříme, zda role „staff“ existuje; pokud ne, vytvoříme ji.

2. Vytvoříme instanci Zakaznik se základními údaji.

3. Setter password interně volá Werkzeug/Bcrypt a bezpečně uloží hash hesla.

4. Přiřadíme roli staff, uložíme záznam do databáze.

5. Tento účet pak použijeme pro demonstraci oprávnění staff.

3.2 Ukázka přihlášení (curl)
curl -i -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email":"anna.staff@example.com",
    "password":"heslo123"
  }'

-i zobrazí HTTP hlavičky, abychom viděli status kód.

Tělo požadavku je JSON s e-mailem a heslem.

Při úspěchu server vrátí 200 OK a JSON se dvěma tokeny (access_token, refresh_token).

Pokud údaje nesedí, vrátí 401 Unauthorized a chybovou zprávu.

3.3 Kód přihlášení
Umístění: app/api/auth.py, třída LoginResource
@auth_bp.route("/login")
class LoginResource(MethodView):
    @auth_bp.arguments(LoginSchema)
    def post(self, data):
        # 1) Najdeme uživatele podle e-mailu
        user = Zakaznik.query.filter_by(email=data["email"]).first()

        # 2) Ověříme heslo
        if not user or not user.check_password(data["password"]):
            abort(401, message="Neplatné přihlašovací údaje.")

        # 3) Načteme role uživatele
        roles = [r.name for r in user.roles]

        # 4) Vytvoříme krátkodobý access token s rolemi
        access  = create_access_token(
            identity=str(user.id_zakaznika),
            additional_claims={"roles": roles}
        )

        # 5) Vytvoříme dlouhodobý refresh token
        refresh = create_refresh_token(identity=str(user.id_zakaznika))

        # 6) Vrátíme klientovi oba tokeny
        return {"access_token": access, "refresh_token": refresh}, 200
Popis:
1. LoginSchema zkontroluje, že JSON obsahuje email a password.

2. filter_by(...).first() vyhledá uživatele v databázi.

3. check_password porovná zadané heslo s uloženým hashem.

4. create_access_token a create_refresh_token generují JWT tokeny; do access tokenu vkládáme claim roles.

5. Oba tokeny vracíme klientovi jako JSON.

3.4 Zpracování chyb autentizace
| Chyba                        | Kdy nastane                             | Odpověď                                             | Náprava                                         |
| ---------------------------- | --------------------------------------- | --------------------------------------------------- | ----------------------------------------------- |
| Missing Authorization Header | Požadavek bez hlavičky `Authorization`  | `401 { "msg": "Missing Authorization Header" }`     | Přidat hlavičku `Authorization: Bearer <token>` |
| Invalid signature            | Token změněn nebo podepsán jiným klíčem | `401 { "msg": "Token has invalid signature" }`      | Získat nový platný token                        |
| Token has expired            | Vypršel `exp` čas v tokenu              | `401 { "msg": "Token has expired" }`                | Volat `POST /api/auth/refresh`                  |
| Neplatné přihlašovací údaje  | Nesprávný e-mail nebo heslo v `/login`  | `401 { "message": "Neplatné přihlašovací údaje." }` | Opravit přihlašovací údaje                      |

3.5 Obnova tokenu (refresh)
@auth_bp.route("/refresh")
class RefreshResource(MethodView):
    @jwt_required(refresh=True)
    def post(self):
        user_id = get_jwt_identity()
        user = db.session.get(Zakaznik, int(user_id))
        if not user:
            abort(404, message="Uživatel nenalezen.")
        roles = [r.name for r in user.roles]
        access_token = create_access_token(
            identity=str(user_id),
            additional_claims={"roles": roles}
        )
        return {"access_token": access_token}, 200
 Popis:
@jwt_required(refresh=True) akceptuje pouze refresh token.

get_jwt_identity() vrátí uživatelské ID z tokenu.

Pokud uživatel zmizel z DB → 404 Not Found.

Jinak vygenerujeme nový access token se stejnými rolemi.

3.6 Role-based autorizace
Dekorátor pro role (app/api/decorators.py):
def roles_required(*allowed_roles):
    def decorator(fn):
        @wraps(fn)
        @jwt_required()  # kontrola platného access tokenu → 401
        def wrapper(*args, **kwargs):
            roles = get_jwt().get("roles", [])
            if not any(r in roles for r in allowed_roles):
                abort(403, message="K této akci nemáte oprávnění.")
            return fn(*args, **kwargs)
        return wrapper
    return decorator

Popis:
@jwt_required() zaručí, že token je přítomný a platný (jinak 401).

get_jwt()["roles"] vrátí seznam rolí uživatele.

Pokud uživatel nemá žádnou požadovanou roli, vrátíme 403 Forbidden.

Příklad endpointu pro admin roli (app/api/routes.py):
@blp.route("/admin/tasks")
class AdminTasksResource(MethodView):
    @roles_required("admin")
    @blp.response(200, TaskSchema(many=True))
    def get(self):
        return Task.query.all()

Scénáře:
Bez tokenu → 401 Unauthorized

Token bez "admin" → 403 Forbidden

Token s "admin" → 200 OK + data

3.7 Zjednodušený přehled rolí a jejich oprávnění
guest:

- Prohlížení veřejného obsahu: GET /menu, GET /promos

- Přihlášení/registrace: POST /auth/login, POST /auth/register

user:

- Vše z guest +

- Vlastní profil: GET/PUT /me

- Správa vlastních rezervací: CRUD /rezervace

- Správa vlastních objednávek: POST /objednavky, GET /objednavky/{id}

- Platby: POST /platby

- Hodnocení: POST /hodnoceni

staff:

- Vše z user +

- CRUD položek menu: POST/PUT/DELETE /menu

- Správa objednávek: GET /objednavky, PUT /objednavky/{id}

- Správa rezervací: GET/PUT /rezervace/{id}

admin:

- Vše ze staff +

- CRUD zákazníků: GET/PUT/DELETE /zakaznik/{id}

- CRUD rolí: /role

- Interní akce: migrace, seed, logy, konfigurace

3.8 Mazání zákazníka s byznys-kontrolou
@blp.route("/zakaznik/<int:id_zakaznika>")
class ZakaznikItem(MethodView):
    @roles_required("admin")
    def delete(self, id_zakaznika):
        user = db.session.get(Zakaznik, id_zakaznika)
        if not user:
            abort(404, message="Zákazník nenalezen.")
        aktivni = (
            db.session.query(Objednavka)
            .filter_by(zakaznik_id=id_zakaznika, stav="PENDING")
            .count()
        )
        if aktivni > 0:
            abort(400, message=(
                f"Nelze smazat zákazníka; "
                f"má {aktivni} aktivní objednávku{'y' if aktivni>1 else ''}."
            ))
        db.session.delete(user)
        db.session.commit()
        return {"message":"Zákazník smazán."}, 200

Popis:
1. Pokud zákazník neexistuje → 404 Not Found

2. Pokud má aktivní objednávky ("PENDING") → 400 Bad Request, abychom neztratili transakční data

3. Jinak smažeme záznam a vrátíme 200 OK

4. Dokumentace API
http://localhost:8000/api/docs/swagger

- Swagger UI generované automaticky z app/schemas.py a registrace blueprintů.

- Umožňuje “Try it out” pro každý endpoint.

5. Implementace ORM:
- Model Zakaznik (app/models.py): primární klíč, hash hesla, vztahy rezervace, roles.

- CRUD rezervace v app/api/routes.py: validace vstupu, db.session.add(), db.session.commit(), vrácení JSON.

6. Databázové migrace:
alembic revision --autogenerate -m "Přidání sloupce stav_platby do Platba"
alembic upgrade head
flask seed-db

- Alembic porovná modely s aktuálním schématem, vygeneruje skript a aplikuje změnu.

7. Serializace a validace dat
Vstupní schéma v app/schemas.py s vlastním @validates_schema.

Výstupní schéma s dump_only=True pro id a definicí polí pro odpověď.
