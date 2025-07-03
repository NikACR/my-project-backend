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
from datetime import date
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

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
    ObjednavkaSchema, ObjednavkaCreateSchema,
    PolozkaObjednavkySchema, PolozkaObjednavkyCreateSchema,
    PlatbaSchema, PlatbaCreateSchema,
    HodnoceniSchema, HodnoceniCreateSchema,
    PolozkaMenuSchema, PolozkaMenuCreateSchema,
    PolozkaMenuAlergenSchema, PolozkaMenuAlergenCreateSchema,
    JidelniPlanSchema, JidelniPlanCreateSchema,
    PolozkaJidelnihoPlanuSchema, PolozkaJidelnihoPlanuCreateSchema,
    AlergenSchema, AlergenCreateSchema,
    NotifikaceSchema, NotifikaceCreateSchema,
    RezervaceSchema, RezervaceCreateSchema
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
    route_base,
    model,
    schema_cls,
    create_schema_cls,
    pk_name,
    roles_list=("staff", "admin"),
    roles_create=("staff", "admin"),
    roles_item_get=("staff", "admin"),
    roles_update=("staff", "admin"),
    roles_delete=("staff", "admin")
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

# CRUD pro základní modely
register_crud('ucet', VernostniUcet, VernostniUcetSchema, VernostniUcetCreateSchema, 'id_ucet')
register_crud('stul', Stul, StulSchema, StulCreateSchema, 'id_stul', roles_list=('user','staff','admin'))
register_crud('salonek', Salonek, SalonekSchema, SalonekCreateSchema, 'id_salonek',
              roles_list=('user','staff','admin'),
              roles_create=('user','staff','admin'),
              roles_item_get=('user','staff','admin'),
              roles_update=('user','staff','admin'),
              roles_delete=('user','staff','admin'))
register_crud('akce', PodnikovaAkce, PodnikovaAkceSchema, PodnikovaAkceCreateSchema, 'id_akce',
              roles_list=('user','staff','admin'),
              roles_create=('user','staff','admin'),
              roles_item_get=('user','staff','admin'),
              roles_update=('user','staff','admin'),
              roles_delete=('user','staff','admin'))
register_crud('objednavka', Objednavka, ObjednavkaSchema, ObjednavkaCreateSchema, 'id_objednavky')
register_crud('polozka-objednavky', PolozkaObjednavky, PolozkaObjednavkySchema, PolozkaObjednavkyCreateSchema, 'id_polozky_obj',
              roles_list=('user','staff','admin'),
              roles_create=('user','staff','admin'),
              roles_item_get=('user','staff','admin'),
              roles_update=('user','staff','admin'),
              roles_delete=('user','staff','admin'))
register_crud('platba', Platba, PlatbaSchema, PlatbaCreateSchema, 'id_platba',
              roles_list=('user','staff','admin'),
              roles_create=('user','staff','admin'),
              roles_item_get=('user','staff','admin'),
              roles_update=('user','staff','admin'),
              roles_delete=('user','staff','admin'))
register_crud('hodnoceni', Hodnoceni, HodnoceniSchema, HodnoceniCreateSchema, 'id_hodnoceni',
              roles_list=('user','staff','admin'),
              roles_create=('user','staff','admin'),
              roles_item_get=('user','staff','admin'),
              roles_update=('user','staff','admin'),
              roles_delete=('user','staff','admin'))
register_crud('notifikace', Notifikace, NotifikaceSchema, NotifikaceCreateSchema, 'id_notifikace',
              roles_list=('user','staff','admin'),
              roles_create=('user','staff','admin'),
              roles_item_get=('user','staff','admin'),
              roles_update=('user','staff','admin'),
              roles_delete=('user','staff','admin'))
register_crud('jidelni-plan', JidelniPlan, JidelniPlanSchema, JidelniPlanCreateSchema, 'id_plan')
register_crud('polozka-planu', PolozkaJidelnihoPlanu, PolozkaJidelnihoPlanuSchema, PolozkaJidelnihoPlanuCreateSchema, 'id_polozka_jid_pl',
              roles_list=('user','staff','admin'),
              roles_create=('user','staff','admin'),
              roles_item_get=('user','staff','admin'),
              roles_update=('user','staff','admin'),
              roles_delete=('user','staff','admin'))
register_crud('alergen', Alergen, AlergenSchema, AlergenCreateSchema, 'id_alergenu',
              roles_list=('user','staff','admin'),
              roles_create=('user','staff','admin'),
              roles_item_get=('user','staff','admin'),
              roles_update=('user','staff','admin'),
              roles_delete=('user','staff','admin'))

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
        """Vrátí všechny jídelní plány platné k dnešnímu dni."""
        today = date.today()
        stmt = (
            db.select(JidelniPlan)
              .where(JidelniPlan.platny_od <= today)
              .where(
                  (JidelniPlan.platny_do == None) |
                  (JidelniPlan.platny_do >= today)
              )
        )
        return db.session.scalars(stmt).all()

@api_bp.route("/meal-plans/<int:id_plan>")
class MealPlanItem(MethodView):
    @jwt_required()
    @api_bp.response(200, JidelniPlanSchema)
    def get(self, id_plan):
        """Vrátí detail jednoho jídelního plánu podle jeho ID."""
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
