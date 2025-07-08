import os
from functools import wraps
from datetime import datetime, date, timedelta

from flask.views import MethodView
from flask import request, current_app, jsonify, url_for
from flask_smorest import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from werkzeug.utils import secure_filename

from ..db import db
from ..models import (
    Zakaznik, VernostniUcet, Stul, Salonek, PodnikovaAkce,
    Workshop, Rezervace, Notifikace,
    Objednavka, PolozkaObjednavky, Platba, Hodnoceni,
    PolozkaMenu, PolozkaMenuAlergen, JidelniPlan,
    PolozkaJidelnihoPlanu, Alergen, Role
)
from ..schemas import (
    ZakaznikSchema, ZakaznikCreateSchema,
    VernostniUcetSchema, VernostniUcetCreateSchema,
    StulSchema, StulCreateSchema,
    SalonekSchema, SalonekCreateSchema,
    PodnikovaAkceSchema, PodnikovaAkceCreateSchema,
    WorkshopSchema, WorkshopCreateSchema,
    ObjednavkaSchema, ObjednavkaUserCreateSchema,
    PolozkaObjednavkySchema, PolozkaObjednavkyCreateSchema,
    PlatbaSchema, PlatbaCreateSchema,
    HodnoceniSchema, HodnoceniCreateSchema,
    PolozkaMenuSchema, PolozkaMenuCreateSchema,
    JidelniPlanSchema, JidelniPlanCreateSchema,
    PolozkaJidelnihoPlanuSchema, PolozkaJidelnihoPlanuCreateSchema,
    AlergenSchema, AlergenCreateSchema,
    NotifikaceSchema, NotifikaceCreateSchema,
    RezervaceSchema, RezervaceCreateSchema,
    RedeemSchema
)
from . import api_bp

# ──────────────────────────────────────────────────────────────────────────────
# HELPER: Kontrola dostupnosti stolu
# ──────────────────────────────────────────────────────────────────────────────
def is_table_available(table_id, dt, persons):
    table = db.session.get(Stul, table_id)
    if not table:
        abort(404, message="Stůl nenalezen.")
    occupied = db.session.query(
        func.coalesce(func.sum(Rezervace.pocet_osob), 0)
    ).filter_by(
        id_stul=table_id,
        datum_cas=dt
    ).scalar()
    return (occupied + persons) <= table.kapacita

# ──────────────────────────────────────────────────────────────────────────────
# Dekorátory pro omezení přístupu
# ──────────────────────────────────────────────────────────────────────────────
def must_be_self_or_admin(param_name="id_zakaznika"):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            current_id = int(get_jwt_identity())
            roles      = set(get_jwt().get("roles", []))
            target_id  = int(kwargs.get(param_name))
            if current_id != target_id and not roles.intersection({"staff","admin"}):
                abort(403, message="Nemáte oprávnění.")
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def must_own_reservation_or_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        current_id = int(get_jwt_identity())
        roles      = set(get_jwt().get("roles", []))
        rez        = db.session.get(Rezervace, kwargs.get("id_rezervace"))
        if not rez:
            abort(404, message="Rezervace nenalezena.")
        if rez.id_zakaznika != current_id and not roles.intersection({"staff","admin"}):
            abort(403, message="Nemáte oprávnění.")
        return fn(*args, **kwargs)
    return wrapper

# ──────────────────────────────────────────────────────────────────────────────
# CRUD pro zákazníka
# ──────────────────────────────────────────────────────────────────────────────
@api_bp.route("/zakaznik")
class ZakaznikList(MethodView):
    @jwt_required()
    @api_bp.response(200, ZakaznikSchema(many=True))
    def get(self):
        roles       = set(get_jwt().get("roles", []))
        if not roles.intersection({"staff","admin"}):
            abort(403, message="Nemáte oprávnění zobrazit všechny zákazníky.")
        role_filter = request.args.get("role")
        stmt        = db.select(Zakaznik)
        if role_filter:
            stmt = stmt.join(Zakaznik.roles).where(Role.name == role_filter)
        return db.session.scalars(stmt).all()

    @jwt_required()
    @api_bp.arguments(ZakaznikCreateSchema)
    @api_bp.response(201, ZakaznikSchema)
    def post(self, new_data):
        roles = set(get_jwt().get("roles", []))
        if not roles.intersection({"staff","admin"}):
            abort(403, message="Nemáte oprávnění vytvářet zákazníky.")
        zak       = Zakaznik(**new_data)
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
        roles      = set(get_jwt().get("roles", []))
        if current_id != id_zakaznika and not roles.intersection({"staff","admin"}):
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
# Generický CRUD registrátor
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

# ──────────────────────────────────────────────────────────────────────────────
# CRUD pro základní entity
# ──────────────────────────────────────────────────────────────────────────────
for base, model, sc, cc, pk in [
    ('ucet',      VernostniUcet,       VernostniUcetSchema,      VernostniUcetCreateSchema,      'id_ucet'),
    ('stul',      Stul,                 StulSchema,                StulCreateSchema,                'id_stul'),
    ('menu',      PolozkaMenu,          PolozkaMenuSchema,         PolozkaMenuCreateSchema,         'id_menu_polozka'),
    ('alergen',   Alergen,              AlergenSchema,             AlergenCreateSchema,             'id_alergenu'),
    ('meal-plans',JidelniPlan,          JidelniPlanSchema,         JidelniPlanCreateSchema,         'id_plan'),
]:
    register_crud(base, model, sc, cc, pk)

# ──────────────────────────────────────────────────────────────────────────────
# SALONEK endpoints (s obrázkem)
# ──────────────────────────────────────────────────────────────────────────────
@api_bp.route("/salonek")
class SalonekList(MethodView):
    @jwt_required()
    @api_bp.response(200, SalonekSchema(many=True))
    def get(self):
        return db.session.scalars(db.select(Salonek)).all()

    @jwt_required()
    @api_bp.arguments(SalonekCreateSchema, location="form")
    @api_bp.response(201, SalonekSchema)
    def post(self, new_data):
        file = request.files.get('obrazek')
        obj  = Salonek(**new_data)
        if file:
            filename = secure_filename(file.filename)
            dest     = os.path.join(current_app.root_path, 'static', 'images')
            os.makedirs(dest, exist_ok=True)
            file.save(os.path.join(dest, filename))
            obj.obrazek_filename = filename
        roles = set(get_jwt().get("roles", []))
        if not roles.intersection({"staff","admin"}):
            abort(403, message="Nemáte oprávnění vytvářet salonek.")
        try:
            db.session.add(obj)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            abort(409, message="Duplicitní nebo neplatný záznam.")
        return obj

@api_bp.route("/salonek/<int:id_salonek>")
class SalonekItem(MethodView):
    @jwt_required()
    @api_bp.response(200, SalonekSchema)
    def get(self, id_salonek):
        obj = db.session.get(Salonek, id_salonek)
        if not obj:
            abort(404, message="Salonek nenalezen.")
        return obj

    @jwt_required()
    @api_bp.arguments(SalonekCreateSchema(partial=True), location="form")
    @api_bp.response(200, SalonekSchema)
    def put(self, data, id_salonek):
        obj = db.session.get(Salonek, id_salonek)
        if not obj:
            abort(404, message="Salonek nenalezen.")
        file = request.files.get('obrazek')
        if file:
            filename = secure_filename(file.filename)
            dest     = os.path.join(current_app.root_path, 'static', 'images')
            os.makedirs(dest, exist_ok=True)
            file.save(os.path.join(dest, filename))
            obj.obrazek_filename = filename
        for k, v in data.items():
            setattr(obj, k, v)
        db.session.commit()
        return obj

    @jwt_required()
    @api_bp.response(204)
    def delete(self, id_salonek):
        obj = db.session.get(Salonek, id_salonek)
        if not obj:
            abort(404, message="Salonek nenalezen.")
        db.session.delete(obj)
        db.session.commit()
        return ""

# ──────────────────────────────────────────────────────────────────────────────
# PODNIKOVÁ AKCE endpoints (s obrázkem)
# ──────────────────────────────────────────────────────────────────────────────
@api_bp.route("/akce")
class AkceList(MethodView):
    @jwt_required()
    @api_bp.response(200, PodnikovaAkceSchema(many=True))
    def get(self):
        return db.session.scalars(db.select(PodnikovaAkce)).all()

    @jwt_required()
    @api_bp.arguments(PodnikovaAkceCreateSchema, location="form")
    @api_bp.response(201, PodnikovaAkceSchema)
    def post(self, new_data):
        file = request.files.get('obrazek')
        obj  = PodnikovaAkce(**new_data)
        if file:
            filename = secure_filename(file.filename)
            dest     = os.path.join(current_app.root_path, 'static', 'images')
            os.makedirs(dest, exist_ok=True)
            file.save(os.path.join(dest, filename))
            obj.obrazek_filename = filename
        roles = set(get_jwt().get("roles", []))
        if not roles.intersection({"staff","admin"}):
            abort(403, message="Nemáte oprávnění vytvářet akce.")
        try:
            db.session.add(obj)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            abort(409, message="Duplicitní nebo neplatný záznam.")
        return obj

@api_bp.route("/akce/<int:id_akce>")
class AkceItem(MethodView):
    @jwt_required()
    @api_bp.response(200, PodnikovaAkceSchema)
    def get(self, id_akce):
        obj = db.session.get(PodnikovaAkce, id_akce)
        if not obj:
            abort(404, message="Akce nenalezena.")
        return obj

    @jwt_required()
    @api_bp.arguments(PodnikovaAkceCreateSchema(partial=True), location="form")
    @api_bp.response(200, PodnikovaAkceSchema)
    def put(self, data, id_akce):
        obj = db.session.get(PodnikovaAkce, id_akce)
        if not obj:
            abort(404, message="Akce nenalezena.")
        file = request.files.get('obrazek')
        if file:
            filename = secure_filename(file.filename)
            dest     = os.path.join(current_app.root_path, 'static', 'images')
            os.makedirs(dest, exist_ok=True)
            file.save(os.path.join(dest, filename))
            obj.obrazek_filename = filename
        for k, v in data.items():
            setattr(obj, k, v)
        db.session.commit()
        return obj

    @jwt_required()
    @api_bp.response(204)
    def delete(self, id_akce):
        obj = db.session.get(PodnikovaAkce, id_akce)
        if not obj:
            abort(404, message="Akce nenalezena.")
        db.session.delete(obj)
        db.session.commit()
        return ""

# ──────────────────────────────────────────────────────────────────────────────
# WORKSHOP endpoints (s obrázkem)
# ──────────────────────────────────────────────────────────────────────────────
@api_bp.route("/workshops")
class WorkshopList(MethodView):
    @jwt_required()
    @api_bp.response(200, WorkshopSchema(many=True))
    def get(self):
        return db.session.scalars(db.select(Workshop)).all()

    @jwt_required()
    @api_bp.arguments(WorkshopCreateSchema, location="form")
    @api_bp.response(201, WorkshopSchema)
    def post(self, new_data):
        file = request.files.get('obrazek')
        obj  = Workshop(**new_data)
        if file:
            filename = secure_filename(file.filename)
            dest     = os.path.join(current_app.root_path, 'static', 'images')
            os.makedirs(dest, exist_ok=True)
            file.save(os.path.join(dest, filename))
            obj.obrazek_filename = filename
        roles = set(get_jwt().get("roles", []))
        if not roles.intersection({"staff","admin"}):
            abort(403, message="Nemáte oprávnění vytvářet workshopy.")
        try:
            db.session.add(obj)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            abort(409, message="Duplicitní nebo neplatný záznam.")
        return obj

@api_bp.route("/workshops/<int:id_workshop>")
class WorkshopItem(MethodView):
    @jwt_required()
    @api_bp.response(200, WorkshopSchema)
    def get(self, id_workshop):
        obj = db.session.get(Workshop, id_workshop)
        if not obj:
            abort(404, message="Workshop nenalezena.")
        return obj

    @jwt_required()
    @api_bp.arguments(WorkshopCreateSchema(partial=True), location="form")
    @api_bp.response(200, WorkshopSchema)
    def put(self, data, id_workshop):
        obj = db.session.get(Workshop, id_workshop)
        if not obj:
            abort(404, message="Workshop nenalezena.")
        file = request.files.get('obrazek')
        if file:
            filename = secure_filename(file.filename)
            dest     = os.path.join(current_app.root_path, 'static', 'images')
            os.makedirs(dest, exist_ok=True)
            file.save(os.path.join(dest, filename))
            obj.obrazek_filename = filename
        for k, v in data.items():
            setattr(obj, k, v)
        db.session.commit()
        return obj

    @jwt_required()
    @api_bp.response(204)
    def delete(self, id_workshop):
        obj = db.session.get(Workshop, id_workshop)
        if not obj:
            abort(404, message="Workshop nenalezena.")
        db.session.delete(obj)
        db.session.commit()
        return ""

# ──────────────────────────────────────────────────────────────────────────────
# OBJEDNAVKY endpoints
# ──────────────────────────────────────────────────────────────────────────────
@api_bp.route("/objednavky")
class ObjednavkyResource(MethodView):
    @jwt_required()
    @api_bp.response(200, ObjednavkaSchema(many=True))
    def get(self):
        user_id = int(get_jwt_identity())
        roles   = set(get_jwt().get("roles", []))
        if roles.intersection({"staff","admin"}):
            objednavky = db.session.scalars(db.select(Objednavka)).all()
        else:
            objednavky = db.session.scalars(
                db.select(Objednavka).where(Objednavka.id_zakaznika == user_id)
            ).all()

        now    = datetime.utcnow()
        result = []
        for o in objednavky:
            paid = db.session.query(Platba).filter_by(id_objednavky=o.id_objednavky).first()
            stav = (
                "Čeká na platbu" if not paid else
                ("Ve zpracování" if (o.cas_pripravy and now < o.cas_pripravy) else "Hotovo")
            )
            result.append({
                "id_objednavky":  o.id_objednavky,
                "stav":           stav,
                "celkova_castka": float(o.celkova_castka),
                "body_ziskane":   o.body_ziskane,
                "cas_pripravy":   o.cas_pripravy.isoformat() if o.cas_pripravy else None
            })
        return jsonify(result), 200

    @jwt_required()
    @api_bp.arguments(ObjednavkaUserCreateSchema, location="json")
    @api_bp.response(201, ObjednavkaSchema)
    def post(self, order_data):
        user_id        = int(get_jwt_identity())
        items          = order_data["items"]
        apply_discount = order_data.get("apply_discount", False)

        menu_ids = [it["id_menu_polozka"] for it in items]
        menu_items = {
            m.id_menu_polozka: m
            for m in db.session.query(PolozkaMenu)
                           .filter(PolozkaMenu.id_menu_polozka.in_(menu_ids))
                           .all()
        }
        if len(menu_items) != len(menu_ids):
            abort(404, message="Některá položka nebyla nalezena.")

        total_price    = 0.0
        total_points   = 0
        max_prep_time  = 0
        max_prep_count = 0
        for it in items:
            m   = menu_items[it["id_menu_polozka"]]
            qty = it.get("mnozstvi", 1)
            total_price  += float(m.cena) * qty
            total_points += m.points * qty
            if m.preparation_time > max_prep_time:
                max_prep_time  = m.preparation_time
                max_prep_count = qty

        prep_minutes = max_prep_time * max_prep_count if max_prep_time and max_prep_count else 0

        account = (db.session.query(VernostniUcet)
                         .filter_by(id_zakaznika=user_id)
                         .with_for_update()
                         .one_or_none())
        if not account:
            account = VernostniUcet(body=0, datum_zalozeni=date.today(), zakaznik_id=user_id)
            db.session.add(account)
            db.session.flush()

        discount_amount = 0
        if apply_discount and account.body >= 400:
            discount_amount = 200
            account.body   -= 400

        objednavka = Objednavka(
            id_zakaznika   = user_id,
            cas_pripravy   = datetime.utcnow() + timedelta(minutes=prep_minutes),
            body_ziskane   = (total_points if not apply_discount else 0),
            celkova_castka = total_price - discount_amount
        )
        db.session.add(objednavka)
        db.session.flush()

        for it in items:
            polo = menu_items[it["id_menu_polozka"]]
            pi   = PolozkaObjednavky(
                mnozstvi     = it.get("mnozstvi", 1),
                cena         = polo.cena,
                objednavka   = objednavka,
                menu_polozka = polo
            )
            db.session.add(pi)

        if not apply_discount:
            account.body += total_points
        db.session.add(account)
        db.session.commit()

        notif = Notifikace(
            typ="OBJEDNAVKA_VYTVOŘENA",
            datum_cas=datetime.utcnow(),
            text=f"Objednávka č. {objednavka.id_objednavky} byla vytvořena.",
            id_objednavky=objednavka.id_objednavky,
            id_zakaznika=user_id
        )
        db.session.add(notif)
        db.session.commit()

        return objednavka

# ──────────────────────────────────────────────────────────────────────────────
# MENU endpoints
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
    @api_bp.arguments(PolozkaMenuCreateSchema, location="form")
    @api_bp.response(201, PolozkaMenuSchema)
    def post(self, new_data):
        file = request.files.get('obrazek')
        obj  = PolozkaMenu(**new_data)
        if file:
            filename = secure_filename(file.filename)
            dest     = os.path.join(current_app.root_path, 'static', 'images')
            os.makedirs(dest, exist_ok=True)
            file.save(os.path.join(dest, filename))
            obj.obrazek_filename = filename
        roles = set(get_jwt().get("roles", []))
        if not roles.intersection({"staff","admin"}):
            abort(403, message="Nemáte oprávnění vytvářet položky menu.")
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
    @api_bp.arguments(PolozkaMenuCreateSchema(partial=True), location="form")
    @api_bp.response(200, PolozkaMenuSchema)
    def put(self, data, id_menu_polozka):
        obj = db.session.get(PolozkaMenu, id_menu_polozka)
        if not obj:
            abort(404, message="Položka menu nenalezena.")
        file = request.files.get('obrazek')
        if file:
            filename = secure_filename(file.filename)
            dest     = os.path.join(current_app.root_path, 'static', 'images')
            os.makedirs(dest, exist_ok=True)
            file.save(os.path.join(dest, filename))
            obj.obrazek_filename = filename
        roles = set(get_jwt().get("roles", []))
        if not roles.intersection({"staff","admin"}):
            abort(403, message="Nemáte oprávnění upravovat položky menu.")
        for k, v in data.items():
            setattr(obj, k, v)
        db.session.commit()
        return obj

    @jwt_required()
    @api_bp.response(204)
    def delete(self, id_menu_polozka):
        roles = set(get_jwt().get("roles", []))
        if not roles.intersection({"staff","admin"}):
            abort(403, message="Nemáte oprávnění mazat položky menu.")
        obj = db.session.get(PolozkaMenu, id_menu_polozka)
        if not obj:
            abort(404, message="Položka menu nenalezena.")
        db.session.delete(obj)
        db.session.commit()
        return ""

# ──────────────────────────────────────────────────────────────────────────────
# MEAL-PLANS endpoints
# ──────────────────────────────────────────────────────────────────────────────
@api_bp.route("/meal-plans")
class MealPlansList(MethodView):
    @jwt_required()
    @api_bp.response(200, JidelniPlanSchema(many=True))
    def get(self):
        today = date.today()
        stmt  = (
            db.select(JidelniPlan)
              .where(JidelniPlan.platny_od <= today)
              .where((JidelniPlan.platny_do.is_(None)) | (JidelniPlan.platny_do >= today))
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
# REZERVACE endpoints
# ──────────────────────────────────────────────────────────────────────────────
@api_bp.route("/rezervace")
class RezervaceList(MethodView):
    @jwt_required()
    @api_bp.response(200, RezervaceSchema(many=True))
    def get(self):
        current_id = int(get_jwt_identity())
        roles      = set(get_jwt().get("roles", []))
        base_stmt = (
            db.select(Rezervace)
            if roles.intersection({"staff","admin"})
            else db.select(Rezervace).where(Rezervace.id_zakaznika == current_id)
        )
        # pagination
        page     = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        stmt = base_stmt.limit(per_page).offset((page - 1) * per_page)
        return db.session.scalars(stmt).all()

    @jwt_required()
    @api_bp.arguments(RezervaceCreateSchema)
    @api_bp.response(201, RezervaceSchema)
    def post(self, new_data):
        # 1) Validace: jen budoucí datum
        now = datetime.utcnow()
        if new_data["datum_cas"] <= now:
            abort(400, message="Rezervace musí být v budoucnosti.")

        current_id = int(get_jwt_identity())
        new_data["id_zakaznika"] = current_id

        # Kontrola dostupnosti stolu
        if new_data.get("id_stul"):
            if not is_table_available(
                new_data["id_stul"],
                new_data["datum_cas"],
                new_data["pocet_osob"]
            ):
                abort(409, message="Vybraný stůl není dostupný.")

        # Kontrola dostupnosti workshopu
        if new_data.get("id_workshop"):
            ws_id  = new_data["id_workshop"]
            dt     = new_data["datum_cas"]
            ppl    = new_data["pocet_osob"]
            existing = db.session.query(
                func.coalesce(func.sum(Rezervace.pocet_osob), 0)
            ).filter_by(
                id_workshop=ws_id,
                datum_cas=dt
            ).scalar()
            workshop = db.session.get(Workshop, ws_id)
            if not workshop:
                abort(404, message="Workshop nenalezen.")
            if existing + ppl > workshop.kapacita:
                abort(409, message="Workshop nemá dostatečnou kapacitu.")

        # Kontrola dostupnosti salonku
        if new_data.get("id_salonek"):
            sal_id = new_data["id_salonek"]
            dt     = new_data["datum_cas"]
            ppl    = new_data["pocet_osob"]
            existing = db.session.query(
                func.coalesce(func.sum(Rezervace.pocet_osob), 0)
            ).filter_by(
                id_salonek=sal_id,
                datum_cas=dt
            ).scalar()
            salonek = db.session.get(Salonek, sal_id)
            if not salonek:
                abort(404, message="Salonek nenalezen.")
            if existing + ppl > salonek.kapacita:
                abort(409, message="Salonek nemá dostatečnou kapacitu.")

        # Kontrola dostupnosti firemní akce
        if new_data.get("id_akce"):
            ak_id = new_data["id_akce"]
            dt    = new_data["datum_cas"]
            ppl   = new_data["pocet_osob"]
            existing = db.session.query(
                func.coalesce(func.sum(Rezervace.pocet_osob), 0)
            ).filter_by(
                id_akce=ak_id,
                datum_cas=dt
            ).scalar()
            akce = db.session.get(PodnikovaAkce, ak_id)
            if not akce:
                abort(404, message="Akce nenalezena.")
            if existing + ppl > akce.kapacita:
                abort(409, message="Akce nemá dostatečnou kapacitu.")

        rez = Rezervace(**new_data)
        try:
            db.session.add(rez)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            abort(409, message="Duplicitní nebo neplatný záznam.")

        notif = Notifikace(
            typ="REZERVACE_VYTVOŘENA",
            datum_cas=datetime.utcnow(),
            text=f"Rezervace č. {rez.id_rezervace} byla vytvořena.",
            id_rezervace=rez.id_rezervace,
            id_zakaznika=current_id
        )
        db.session.add(notif)
        db.session.commit()
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
# PLATBA endpoint
# ──────────────────────────────────────────────────────────────────────────────
@api_bp.route("/platba", methods=["POST"])
@jwt_required()
@api_bp.arguments(PlatbaCreateSchema, location="json")
@api_bp.response(201, PlatbaSchema)
def create_platba_with_points(args):
    raw    = args["datum"]
    dt     = raw if isinstance(raw, datetime) else datetime.fromisoformat(raw)
    platba = Platba(
        castka=args["castka"],
        typ_platby=args["typ_platby"],
        datum=dt,
        id_objednavky=args["id_objednavky"]
    )
    db.session.add(platba)
    db.session.flush()
    zprava = f"Platba #{platba.id_platba} za {args['castka']} Kč úspěšná."
    objed  = db.session.get(Objednavka, platba.id_objednavky)
    note   = Notifikace(
        typ="PLATBA",
        datum_cas=datetime.utcnow(),
        text=zprava,
        id_objednavky=platba.id_platba,
        id_zakaznika = objed.id_zakaznika
    )
    db.session.add(note)
    db.session.commit()
    return platba

# ──────────────────────────────────────────────────────────────────────────────
# NOTIFICATIONS endpoints
# ──────────────────────────────────────────────────────────────────────────────
@api_bp.route("/users/me/notifications")
class MyNotifications(MethodView):
    @jwt_required()
    @api_bp.response(200, NotifikaceSchema(many=True))
    def get(self):
        zak_id = int(get_jwt_identity())
        notifs = (
            db.session.query(Notifikace)
              .filter_by(id_zakaznika=zak_id)
              .order_by(Notifikace.datum_cas.desc())
              .all()
        )
        return notifs

# ──────────────────────────────────────────────────────────────────────────────
# ME/POINTS endpoint
# ──────────────────────────────────────────────────────────────────────────────
@api_bp.route("/users/me/points")
class MyPoints(MethodView):
    @jwt_required()
    @api_bp.response(200, VernostniUcetSchema)
    def get(self):
        zak_id = int(get_jwt_identity())
        ucet   = db.session.query(VernostniUcet).filter_by(id_zakaznika=zak_id).one_or_none()
        if not ucet:
            abort(404, message="Účet nenalezen.")
        return ucet

# ──────────────────────────────────────────────────────────────────────────────
# ME/REDEEM endpoint
# ──────────────────────────────────────────────────────────────────────────────
@api_bp.route("/users/me/redeem")
class RedeemPoints(MethodView):
    @jwt_required()
    @api_bp.arguments(RedeemSchema)
    @api_bp.response(200, VernostniUcetSchema)
    def post(self, data):
        zak_id = int(get_jwt_identity())
        ucet   = db.session.query(VernostniUcet).filter_by(id_zakaznika=zak_id).with_for_update().one_or_none()
        if not ucet:
            abort(404, message="Účet nenalezen.")
        points = data.get("points", 0)
        if ucet.body < points:
            abort(400, message="Nedostatek bodů.")
        ucet.body -= points
        note = Notifikace(
            typ="REDEEM",
            datum_cas=datetime.utcnow(),
            text=f"Uplatněno {points} bodů.",
            id_zakaznika=zak_id
        )
        db.session.add(note)
        db.session.add(ucet)
        db.session.commit()
        return ucet
