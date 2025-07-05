import os
import warnings
from flask import Flask, jsonify, request
from flask_smorest import Api
from flask_jwt_extended import JWTManager, create_access_token
from werkzeug.exceptions import NotFound, UnprocessableEntity
from flask_cors import CORS

# potlačíme varování o duplicitních schématech pro OpenAPI
warnings.filterwarnings(
    "ignore",
    "Multiple schemas resolved to the name",
    UserWarning,
    module="apispec.ext.marshmallow.openapi"
)

from .config import config_by_name
from .db import db, migrate

# načteme modely, aby je Alembic/apispec viděl
from .models import (
    Zakaznik, VernostniUcet, Rezervace, Stul, Salonek,
    PodnikovaAkce, Objednavka, PolozkaObjednavky, Platba,
    Hodnoceni, PolozkaMenu, PolozkaMenuAlergen,
    JidelniPlan, PolozkaJidelnihoPlanu, Alergen, Notifikace,
    Role, TokenBlacklist
)

def create_app(config_name=None, config_override=None):
    if not config_name:
        config_name = os.getenv("FLASK_CONFIG", "default")

    app = Flask(__name__)
    app.json.ensure_ascii = False

    # načtení configu (development/testing/production)
    if config_override:
        app.config.from_object(config_override)
    else:
        app.config.from_object(config_by_name[config_name])
    app.config.setdefault("JSON_AS_ASCII", False)

    # povolíme CORS pro frontend na localhost:3000
    CORS(
        app,
        resources={r"/api/*": {"origins": "http://localhost:3000"}},
        supports_credentials=True
    )

    # init DB + migrace
    db.init_app(app)
    migrate.init_app(app, db)

    # init JWT + blacklist callback
    jwt = JWTManager(app)

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload["jti"]
        return db.session.query(TokenBlacklist).filter_by(jti=jti).first() is not None

    # ─── dev‐mode JWT injector ───────────────────────────────────────────────
    if config_name == "development":
        dev_email = os.getenv("DEV_USER_EMAIL")
        dev_password = os.getenv("DEV_USER_PASSWORD")

        @app.before_request
        def _inject_dev_token():
            if not request.headers.get("Authorization") and dev_email and dev_password:
                user = db.session.query(Zakaznik).filter_by(email=dev_email).first()
                if user and user.check_password(dev_password):
                    token = create_access_token(identity=str(user.id_zakaznika))
                    request.environ["HTTP_AUTHORIZATION"] = f"Bearer {token}"

    # ─── SSE: umožnit JWT také z query param 'token' ─────────────────────────
    @app.before_request
    def _inject_token_from_query():
        # pro event-streamy (SSE) bez hlavičky Authorization
        # např. GET /api/events/objednavka/5?token=<jwt>
        if request.path.startswith("/api/events") and not request.headers.get("Authorization"):
            token = request.args.get("token")
            if token:
                request.environ["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    # ────────────────────────────────────────────────────────────────────────────

    # init API / Swagger UI
    api = Api(app)
    from .api import api_bp
    from .api.auth import auth_bp
    api.register_blueprint(api_bp)
    api.register_blueprint(auth_bp)

    # ─── Idempotentní seed trvalých položek menu + alergenů
    # seedování momentálně zakomentováno, aby bylo možné spouštět migrace bez chyb
    """
    from .models import PolozkaMenu, Alergen, PolozkaMenuAlergen

    with app.app_context():
        # 1) Seed položek menu – včetně obrázků, kategorie a dne (den="" aby nebylo NULL)
        seed_items = [
            {"nazev":"Sýrová pizza","popis":"italská pizza","cena":199.00,
             "obrazek_url":None,"kategorie":"stálá nabídka","den":""},
            # ... ostatní položky ...
        ]
        for itm in seed_items:
            itm.setdefault("kategorie", "stálá nabídka")
            itm.setdefault("den", "")
            if not db.session.query(PolozkaMenu).filter_by(nazev=itm["nazev"]).first():
                db.session.add(PolozkaMenu(**itm))
        db.session.commit()

        # 2) Seed alergenů
        alergeny = {
            "Lepek": "obiloviny obsahující lepek",
            "Mléko": "mléčné výrobky a laktóza",
            # ... další alergeny ...
        }
        for nazev, popis in alergeny.items():
            if not db.session.query(Alergen).filter_by(nazev=nazev).first():
                db.session.add(Alergen(nazev=nazev, popis=popis))
        db.session.commit()

        # 3) Seed vazeb položka↔alergen
        menu_alergeny = {
            "Sýrová pizza": ["Lepek","Mléko"],
            # ... další vazby ...
        }
        for náz, algs in menu_alergeny.items():
            pol = db.session.query(PolozkaMenu).filter_by(nazev=náz).first()
            if pol:
                for alg_n in algs:
                    alg = db.session.query(Alergen).filter_by(nazev=alg_n).first()
                    if alg and not db.session.query(PolozkaMenuAlergen).filter_by(
                        id_menu_polozka=pol.id_menu_polozka,
                        id_alergenu=alg.id_alergenu
                    ).first():
                        db.session.add(PolozkaMenuAlergen(menu_polozka=pol, alergen=alg))
        db.session.commit()
    """
    # ────────────────────────────────────────────────────────────────────────────

    @app.errorhandler(UnprocessableEntity)
    def handle_validation_error(err):
        data     = getattr(err, 'data', {}) or {}
        messages = data.get('messages', {})
        return jsonify({
            "status": "Chybný vstup",
            "code":   422,
            "errors": messages
        }), 422

    @app.errorhandler(NotFound)
    def handle_404(err):
        msg = err.description or "Nenalezeno"
        return jsonify({
            "status":  "Nenalezeno",
            "code":    404,
            "message": msg
        }), 404

    @app.route("/hello")
    def hello():
        return "Hello, World from Flask!"

    return app
