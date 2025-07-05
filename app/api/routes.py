"""
Principy a důležité body
------------------------
1. JWT autorizace (@jwt_required)
   - Každý chráněný endpoint vyžaduje platný JWT token v hlavičce
     Authorization: Bearer <token>.
   - Token se získá přes /api/auth/login a obsahuje zakódované identity
     (ID zákazníka) a pole roles.
   - Pokud token chybí nebo je neplatný, flask-jwt-extended vrátí 401 Unauthorized.

2. Validace a serializace (@api_bp.arguments, @api_bp.response)
   - @arguments(SomeSchema): validuje vstupní JSON podle schématu.
   - @response(status, SomeSchema): serializuje výstup dle schématu.

3. Chybové stavy (abort)
   - abort(code, message="...") vrátí JSON { "message": "...", "code": code }.

4. Role‐based Access Control
   - Role z claimu get_jwt()["roles"]: "user", "staff", "admin".

5. Transakce a IntegrityError
   - Při IntegrityError: rollback a 409 Conflict.

6. db.session.flush() vs db.session.commit()

7. register_crud
   - Generuje CRUD endpointy automaticky.
"""
from functools import wraps
from flask.views import MethodView
from flask_smorest import abort
from flask import request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from datetime import datetime, date, timedelta
from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity,
    get_jwt
)

from ..db import db
from ..models import (
    Zakaznik, VernostniUcet, Stul, Salonek, PodnikovaAkce,
    Objednavka, PolozkaObjednavky, Platba, Hodnoceni,
    PolozkaMenu, PolozkaMenuAlergen, JidelniPlan,
    PolozkaJidelnihoPlanu, Alergen, Notifikace, Rezervace, Role
)
from ..schemas import (
    ZakaznikSchema, ZakaznikCreateSchema,
    VernostniUcetSchema, VernostniUcetCreateSchema,
    StulSchema, StulCreateSchema,
    SalonekSchema, SalonekCreateSchema,
    PodnikovaAkceSchema, PodnikovaAkceCreateSchema,
    ObjednavkaSchema, ObjednavkaUserCreateSchema,
    PolozkaObjednavkySchema, PolozkaObjednavkyCreateSchema,
    PlatbaSchema, PlatbaCreateSchema,
    HodnoceniSchema, HodnoceniCreateSchema,
    PolozkaMenuSchema, PolozkaMenuCreateSchema,
    PolozkaMenuAlergenSchema, PolozkaMenuAlergenCreateSchema,
    JidelniPlanSchema, JidelniPlanCreateSchema,
    PolozkaJidelnihoPlanuSchema, PolozkaJidelnihoPlanuCreateSchema,
    AlergenSchema, AlergenCreateSchema,
    NotifikaceSchema, NotifikaceCreateSchema,
    RezervaceSchema, RezervaceCreateSchema,
    RedeemSchema
)
from . import api_bp

# ──────────────────────────────────────────────────────────────────────────────
# Dekorátory pro omezení přístupu
# ──────────────────────────────────────────────────────────────────────────────
def must_be_self_or_admin(param_name="id_zakaznika"):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            current_id = int(get_jwt_identity())
            roles = set(get_jwt().get("roles", []))
            target_id = int(kwargs.get(param_name))
            if current_id != target_id and not roles.intersection({"staff", "admin"}):
                abort(403, message="Nemáte oprávnění.")
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def must_own_reservation_or_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        current_id = int(get_jwt_identity())
        roles = set(get_jwt().get("roles", []))
        rez = db.session.get(Rezervace, kwargs.get("id_rezervace"))
        if not rez:
            abort(404, message="Rezervace nenalezena.")
        if rez.id_zakaznika != current_id and not roles.intersection({"staff", "admin"}):
            abort(403, message="Nemáte oprávnění.")
        return fn(*args, **kwargs)
    return wrapper

# ──────────────────────────────────────────────────────────────────────────────
# 1) CRUD PRO ZÁKAZNÍKA
# ──────────────────────────────────────────────────────────────────────────────
@api_bp.route("/zakaznik")
class ZakaznikList(MethodView):
    @jwt_required()
    @api_bp.response(200, ZakaznikSchema(many=True))
    def get(self):
        roles = set(get_jwt().get("roles", []))
        if not roles.intersection({"staff", "admin"}):
            abort(403, message="Nemáte oprávnění zobrazit všechny zákazníky.")
        role_filter = request.args.get("role")
        stmt = db.select(Zakaznik)
        if role_filter:
            stmt = stmt.join(Zakaznik.roles).where(Role.name == role_filter)
        return db.session.scalars(stmt).all()

    @jwt_required()
    @api_bp.arguments(ZakaznikCreateSchema)
    @api_bp.response(201, ZakaznikSchema)
    def post(self, new_data):
        roles = set(get_jwt().get("roles", []))
        if not roles.intersection({"staff", "admin"}):
            abort(403, message="Nemáte oprávnění vytvářet zákazníky.")
        zak = Zakaznik(**new_data)
        user_role = db.session.query(Role).filter_by(name="user").one()
        zak.roles.append(user_role)
        try:
            db.session.add(zak)
            db.session.flush()
            ucet = VernostniUcet(body=0, datum_zalozeni=date.today(), zakaznik=zak)
            db.session.add(ucet)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            abort(409, message="Duplicitní nebo neplatný záznam.")
        return zak

@api_bp.route("/zakaznik/<int:id_zakaznika>")
class ZakaznikItem(MethodView):
    @jwt_required()
    @api_bp.response(200, ZakaznikSchema)
    def get(self, id_zakaznika):
        current_id = int(get_jwt_identity())
        roles = set(get_jwt().get("roles", []))
        if current_id != id_zakaznika and not roles.intersection({"staff", "admin"}):
            abort(403, message="Nemáte oprávnění zobrazit tohoto zákazníka.")
        zak = db.session.get(Zakaznik, id_zakaznika)
        if not zak:
            abort(404, message="Zákazník nenalezen.")
        return zak

    @jwt_required()
    @must_be_self_or_admin("id_zakaznika")
    @api_bp.arguments(ZakaznikSchema(partial=True))
    @api_bp.response(200, ZakaznikSchema)
    def put(self, data, id_zakaznika):
        zak = db.session.get(Zakaznik, id_zakaznika)
        if not zak:
            abort(404, message="Zákazník nenalezen.")
        for k, v in data.items():
            setattr(zak, k, v)
        db.session.commit()
        return zak

    @jwt_required()
    @must_be_self_or_admin("id_zakaznika")
    @api_bp.response(204)
    def delete(self, id_zakaznika):
        zak = db.session.get(Zakaznik, id_zakaznika)
        if not zak:
            abort(404, message="Zákazník nenalezen.")
        db.session.delete(zak)
        db.session.commit()
        return ""

# ──────────────────────────────────────────────────────────────────────────────
# 2) GENERICKÝ register_crud PRO OSTATNÍ ENTITY
# ──────────────────────────────────────────────────────────────────────────────
def register_crud(
    route_base, model, schema_cls, create_schema_cls, pk_name,
    roles_list=("staff","admin"), roles_create=("staff","admin"),
    roles_item_get=("staff","admin"), roles_update=("staff","admin"),
    roles_delete=("staff","admin")
):
    def check_roles(allowed):
        roles = set(get_jwt().get("roles", []))
        if not roles.intersection(allowed):
            abort(403, message="Nemáte oprávnění.")

    @api_bp.route(f"/{route_base}")
    class ListView(MethodView):
        @jwt_required()
        @api_bp.response(200, schema_cls(many=True))
        def get(self):
            check_roles(roles_list)
            return db.session.scalars(db.select(model)).all()

        @jwt_required()
        @api_bp.arguments(create_schema_cls)
        @api_bp.response(201, schema_cls)
        def post(self, new_data):
            check_roles(roles_create)
            obj = model(**new_data)
            try:
                db.session.add(obj)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                abort(409, message="Duplicitní nebo neplatný záznam.")
            return obj

    @api_bp.route(f"/{route_base}/<int:{pk_name}>")
    class ItemView(MethodView):
        @jwt_required()
        @api_bp.response(200, schema_cls)
        def get(self, **kwargs):
            check_roles(roles_item_get)
            obj = db.session.get(model, kwargs[pk_name])
            if not obj:
                abort(404, message=f"{model.__tablename__.capitalize()} nenalezen.")
            return obj

        @jwt_required()
        @api_bp.arguments(schema_cls(partial=True))
        @api_bp.response(200, schema_cls)
        def put(self, data, **kwargs):
            check_roles(roles_update)
            obj = db.session.get(model, kwargs[pk_name])
            if not obj:
                abort(404, message=f"{model.__tablename__.capitalize()} nenalezen.")
            for k, v in data.items():
                setattr(obj, k, v)
            db.session.commit()
            return obj

        @jwt_required()
        @api_bp.response(204)
        def delete(self, **kwargs):
            check_roles(roles_delete)
            obj = db.session.get(model, kwargs[pk_name])
            if not obj:
                abort(404, message=f"{model.__tablename__.capitalize()} nenalezen.")
            db.session.delete(obj)
            db.session.commit()
            return ""

# CRUD pro základní entity
for base, model, sc, cc, pk in [
    ('ucet', VernostniUcet, VernostniUcetSchema, VernostniUcetCreateSchema, 'id_ucet'),
    ('stul', Stul, StulSchema, StulCreateSchema, 'id_stul'),
    ('salonek', Salonek, SalonekSchema, SalonekCreateSchema, 'id_salonek'),
    ('akce', PodnikovaAkce, PodnikovaAkceSchema, PodnikovaAkceCreateSchema, 'id_akce'),
    ('alergen', Alergen, AlergenSchema, AlergenCreateSchema, 'id_alergenu'),
]:
    register_crud(base, model, sc, cc, pk)

# ──────────────────────────────────────────────────────────────────────────────
# 3) VLASTNÍ POST /api/objednavky – spočítá čas, body, slevu
# ──────────────────────────────────────────────────────────────────────────────
@api_bp.route("/objednavky", methods=["POST"])
@jwt_required()
@api_bp.arguments(ObjednavkaUserCreateSchema, location="json")
@api_bp.response(201, ObjednavkaSchema)
def create_order(order_data):
    user_id        = int(get_jwt_identity())
    items          = order_data["items"]
    apply_discount = order_data.get("apply_discount", False)

    # Načti položky menu
    menu_ids   = [it["id_menu_polozka"] for it in items]
    menu_items = {
        m.id_menu_polozka: m for m in
        db.session.query(PolozkaMenu)
          .filter(PolozkaMenu.id_menu_polozka.in_(menu_ids))
          .all()
    }
    if len(menu_items) != len(menu_ids):
        abort(404, message="Některá položka nebyla nalezena.")

    # Vypočti čas přípravy a body
    prep_times   = []
    total_points = 0
    total_price  = 0
    for it in items:
        m = menu_items[it["id_menu_polozka"]]
        prep_times.append(m.preparation_time)
        total_points += m.points * it["mnozstvi"]
        total_price  += m.cena * it["mnozstvi"]
    prep_time = max(prep_times) if prep_times else 0

    # Získej nebo vytvoř vernostní účet
    account = db.session.query(VernostniUcet).filter_by(id_zakaznika=user_id).first()
    if not account:
        account = VernostniUcet(body=0, datum_zalozeni=date.today(), zakaznik_id=user_id)
        db.session.add(account)
        db.session.flush()

    # Aplikuj slevu
    discount_amount = 0
    if apply_discount and account.body >= 400:
        discount_amount = 200
        account.body   -= 400

    # Vytvoř objednávku
    order = Objednavka(
        id_zakaznika   = user_id,
        cas_pripravy   = datetime.utcnow() + timedelta(minutes=prep_time),
        body_ziskane   = total_points,
        celkova_castka = total_price - discount_amount
    )
    db.session.add(order)
    db.session.flush()

    # Vytvoř položky objednávky
    for it in items:
        pi = PolozkaObjednavky(
            mnozstvi     = it["mnozstvi"],
            cena         = menu_items[it["id_menu_polozka"]].cena,
            objednavka   = order,
            menu_polozka = menu_items[it["id_menu_polozka"]]
        )
        db.session.add(pi)

    # Přičti body za novou objednávku
    account.body += total_points
    db.session.add(account)

    # Přidáme tyto tři hodnoty přímo na instanci
    order.preparation_time = prep_time
    order.body_ziskane     = total_points
    order.discount_amount  = discount_amount

    db.session.commit()
    return order

# ──────────────────────────────────────────────────────────────────────────────
# VLASTNÍ ENDPOINTY PRO MENU
# ──────────────────────────────────────────────────────────────────────────────
@api_bp.route("/menu")
class PolozkaMenuList(MethodView):
    @api_bp.response(200, PolozkaMenuSchema(many=True))
    def get(self):
        stmt = (
            db.select(PolozkaMenu)
              .options(
                  selectinload(PolozkaMenu.alergeny)
                    .selectinload(PolozkaMenuAlergen.alergen)
              )
        )
        return db.session.scalars(stmt).all()

    @jwt_required()
    @api_bp.arguments(PolozkaMenuCreateSchema)
    @api_bp.response(201, PolozkaMenuSchema)
    def post(self, new_data):
        roles = set(get_jwt().get("roles", []))
        if not roles.intersection({"staff", "admin"}):
            abort(403, message="Nemáte oprávnění vytvářet položky menu.")
        obj = PolozkaMenu(**new_data)
        try:
            db.session.add(obj)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            abort(409, message="Duplicitní nebo neplatný záznam.")
        return obj

@api_bp.route("/menu/<int:id_menu_polozka>")
class PolozkaMenuItem(MethodView):
    @api_bp.response(200, PolozkaMenuSchema)
    def get(self, id_menu_polozka):
        stmt = (
            db.select(PolozkaMenu)
              .options(
                  selectinload(PolozkaMenu.alergeny)
                    .selectinload(PolozkaMenuAlergen.alergen)
              )
              .where(PolozkaMenu.id_menu_polozka == id_menu_polozka)
        )
        obj = db.session.scalars(stmt).first()
        if not obj:
            abort(404, message="Položka menu nenalezena.")
        return obj

    @jwt_required()
    @api_bp.arguments(PolozkaMenuSchema(partial=True))
    @api_bp.response(200, PolozkaMenuSchema)
    def put(self, data, id_menu_polozka):
        roles = set(get_jwt().get("roles", []))
        if not roles.intersection({"staff", "admin"}):
            abort(403, message="Nemáte oprávnění upravovat položky menu.")
        obj = db.session.get(PolozkaMenu, id_menu_polozka)
        if not obj:
            abort(404, message="Položka menu nenalezena.")
        for k, v in data.items():
            setattr(obj, k, v)
        db.session.commit()
        return obj

    @jwt_required()
    @api_bp.response(204)
    def delete(self, id_menu_polozka):
        roles = set(get_jwt().get("roles", []))
        if not roles.intersection({"staff", "admin"}):
            abort(403, message="Nemáte oprávnění mazat položky menu.")
        obj = db.session.get(PolozkaMenu, id_menu_polozka)
        if not obj:
            abort(404, message="Položka menu nenalezena.")
        db.session.delete(obj)
        db.session.commit()
        return ""

# ──────────────────────────────────────────────────────────────────────────────
# VLASTNÍ ENDPOINTY PRO MEAL-PLANS
# ──────────────────────────────────────────────────────────────────────────────
@api_bp.route("/meal-plans")
class MealPlansList(MethodView):
    @jwt_required()
    @api_bp.response(200, JidelniPlanSchema(many=True))
    def get(self):
        today = date.today()
        stmt = (
            db.select(JidelniPlan)
              .where(JidelniPlan.platny_od <= today)
              .where(
                  (JidelniPlan.platny_do.is_(None)) |
                  (JidelniPlan.platny_do >= today)
              )
        )
        return db.session.scalars(stmt).all()

@api_bp.route("/meal-plans/<int:id_plan>")
class MealPlanItem(MethodView):
    @jwt_required()
    @api_bp.response(200, JidelniPlanSchema)
    def get(self, id_plan):
        plan = db.session.get(JidelniPlan, id_plan)
        if not plan:
            abort(404, message="Jídelní plán nenalezen.")
        return plan

# ──────────────────────────────────────────────────────────────────────────────
# VLASTNÍ ENDPOINTY PRO REZERVACE
# ──────────────────────────────────────────────────────────────────────────────
@api_bp.route("/rezervace")
class RezervaceList(MethodView):
    @jwt_required()
    @api_bp.response(200, RezervaceSchema(many=True))
    def get(self):
        current_id = int(get_jwt_identity())
        roles = set(get_jwt().get("roles", []))
        if roles.intersection({"staff", "admin"}):
            stmt = db.select(Rezervace)
        else:
            stmt = db.select(Rezervace).where(Rezervace.id_zakaznika == current_id)
        return db.session.scalars(stmt).all()

    @jwt_required()
    @api_bp.arguments(RezervaceCreateSchema)
    @api_bp.response(201, RezervaceSchema)
    def post(self, new_data):
        new_data["id_zakaznika"] = int(get_jwt_identity())
        rez = Rezervace(**new_data)
        try:
            db.session.add(rez)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            abort(409, message="Duplicitní nebo neplatný záznam.")
        return rez

@api_bp.route("/rezervace/<int:id_rezervace>")
class RezervaceItem(MethodView):
    @jwt_required()
    @must_own_reservation_or_admin
    @api_bp.response(200, RezervaceSchema)
    def get(self, id_rezervace):
        return db.session.get(Rezervace, id_rezervace)

    @jwt_required()
    @must_own_reservation_or_admin
    @api_bp.arguments(RezervaceSchema(partial=True))
    @api_bp.response(200, RezervaceSchema)
    def put(self, data, id_rezervace):
        rez = db.session.get(Rezervace, id_rezervace)
        for k, v in data.items():
            setattr(rez, k, v)
        db.session.commit()
        return rez

    @jwt_required()
    @must_own_reservation_or_admin
    @api_bp.response(204)
    def delete(self, id_rezervace):
        rez = db.session.get(Rezervace, id_rezervace)
        db.session.delete(rez)
        db.session.commit()
        return ""

# ──────────────────────────────────────────────────────────────────────────────
# BODY – načtení stavu bodů na účtu
# ──────────────────────────────────────────────────────────────────────────────
@api_bp.route("/users/me/points")
class MyPoints(MethodView):
    @jwt_required()
    @api_bp.response(200, VernostniUcetSchema)
    def get(self):
        zakaznik_id = int(get_jwt_identity())
        ucet = db.session.query(VernostniUcet).filter_by(id_zakaznika=zakaznik_id).one_or_none()
        if not ucet:
            abort(404, message="Účet nenalezen.")
        return ucet

# ──────────────────────────────────────────────────────────────────────────────
# BODY – uplatnění bodů
# ──────────────────────────────────────────────────────────────────────────────
@api_bp.route("/users/me/redeem")
class RedeemPoints(MethodView):
    @jwt_required()
    @api_bp.arguments(RedeemSchema)
    @api_bp.response(200, VernostniUcetSchema)
    def post(self, data):
        zakaznik_id = int(get_jwt_identity())
        ucet = db.session.query(VernostniUcet).filter_by(id_zakaznika=zakaznik_id).with_for_update().one_or_none()
        if not ucet:
            abort(404, message="Účet nenalezen.")
        points = data.get("points", 0)
        if ucet.body < points:
            abort(400, message="Nedostatek bodů.")
        ucet.body -= points

        # Vytvoříme notifikaci bez zakaznik_id, jen s textem
        note = Notifikace(
            typ="REDEEM",
            datum_cas=datetime.utcnow(),
            text=f"Uplatněno {points} bodů."
        )
        db.session.add(note)
        db.session.add(ucet)
        db.session.commit()
        return ucet

# ──────────────────────────────────────────────────────────────────────────────
# Override POST /platba: ukládá platbu, přičítá body a vytváří notifikaci
# ──────────────────────────────────────────────────────────────────────────────
@api_bp.route("/platba", methods=["POST"])
@jwt_required()
@api_bp.arguments(PlatbaCreateSchema, location="json")
@api_bp.response(201, PlatbaSchema)
def create_platba_with_points(args):
    user_id = int(get_jwt_identity())

    # 1) Vytvořím platbu
    platba = Platba(
        castka=args["castka"],
        typ_platby=args["typ_platby"],
        datum=args["datum"],
        id_objednavky=args["id_objednavky"]
    )
    db.session.add(platba)
    db.session.flush()  # vyplní platba.id_platba

    # 2) Spočítám a přičtu loyalty body (1 bod / 10 Kč)
    earned = int(float(str(args["castka"])) // 10)
    ucet = db.session.query(VernostniUcet).filter_by(id_zakaznika=user_id).one()
    ucet.body += earned
    db.session.add(ucet)

    # 3) Vytvořím notifikaci bez zakaznik_id, jen s textem a vazbou na objednavku
    zprava = f"Platba #{platba.id_platba} za {args['castka']} Kč úspěšná, získáno {earned} bodů."
    note = Notifikace(
        typ="PLATBA",
        datum_cas=datetime.utcnow(),
        text=zprava,
        id_objednavky=platba.id_platba
    )
    db.session.add(note)

    # 4) Commit
    db.session.commit()
    return platba
