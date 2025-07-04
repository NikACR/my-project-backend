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

    # ─── Idempotentní seed trvalých položek menu + alergenů ─────────────────
    from .models import PolozkaMenu, Alergen, PolozkaMenuAlergen

    with app.app_context():
        # 1) Seed položek menu – včetně obrázků, kategorie a dne (den="" aby nebylo NULL)
        seed_items = [
            {"nazev":"Sýrová pizza","popis":"italská pizza","cena":199.00,
             "obrazek_url":None,"kategorie":"stálá nabídka","den":""},
            {"nazev":"Hovězí burger","popis":"burger s hranolkami","cena":249.00,
             "obrazek_url":None,"kategorie":"stálá nabídka","den":""},
            {"nazev":"Caesar salát","popis":"čerstvý salát","cena":159.00,
             "obrazek_url":None,"kategorie":"stálá nabídka","den":""},
            {"nazev":"naše focaccia","popis":"bryndza, čerstvé klíčky","cena":99.00,
             "obrazek_url":None,"kategorie":"stálá nabídka","den":""},
            {"nazev":"Klimoszkovic kulajda","popis":"opékané brambory, zastřené vejce, čerstvý kopr","cena":109.00,
             "obrazek_url":None,"kategorie":"stálá nabídka","den":""},
            {"nazev":"hovězí tatarák","popis":"kapary, lanýžové máslo, parmezán, křupavý toast","cena":239.00,
             "obrazek_url":None,"kategorie":"stálá nabídka","den":""},
            {"nazev":"římský salát","popis":"cherry rajčata, gorgonzola, javorový sirup, anglická slanina, domácí focaccia","cena":199.00,
             "obrazek_url":None,"kategorie":"stálá nabídka","den":""},
            {"nazev":"vepřová žebra","popis":"domácí BBQ omáčka, čerstvý křen, sádlová houska","cena":359.00,
             "obrazek_url":None,"kategorie":"stálá nabídka","den":""},
            {"nazev":"ball tip steak (USA)","popis":"pečené brambory, pepřová nebo lanýžová omáčka","cena":429.00,
             "obrazek_url":None,"kategorie":"stálá nabídka","den":""},
            {"nazev":"cordon bleu","popis":"medová šunka, čedar, smetanová kaše, rajčatový salát","cena":319.00,
             "obrazek_url":None,"kategorie":"stálá nabídka","den":""},
            {"nazev":"svíčková na smetaně","popis":"hovězí svíčková, domácí houskový knedlík, brusinky, smetanová omáčka","cena":329.00,
             "obrazek_url":None,"kategorie":"stálá nabídka","den":""},
            {"nazev":"bramborové noky","popis":"domácí pesto, sušená rajčata, parmezán, piniové oříšky","cena":239.00,
             "obrazek_url":None,"kategorie":"stálá nabídka","den":""},
            {"nazev":"vepřová panenka 55","popis":"gratinované brambory, demi-glace, rukola, fermentovaná ředkev","cena":329.00,
             "obrazek_url":None,"kategorie":"stálá nabídka","den":""},
            {"nazev":"řízek pro prcky","popis":"kuřecí řízek v panko strouhance, bramborová kaše","cena":155.00,
             "obrazek_url":None,"kategorie":"stálá nabídka","den":""},
            {"nazev":"burger s trhaným vepřovým","popis":"domácí bulky, trhané vepřové maso, BBQ omáčka, sýr Monterey Jack, fermentovaná okurka","cena":259.00,
             "obrazek_url":None,"kategorie":"stálá nabídka","den":""},
            {"nazev":"buchty jako od babičky","popis":"buchtičky s vanilkovým krémem a lesním ovocem","cena":169.00,
             "obrazek_url":None,"kategorie":"stálá nabídka","den":""},
            {"nazev":"paris brest","popis":"odpalované těsto s pekanovými ořechy a krémem","cena":119.00,
             "obrazek_url":None,"kategorie":"stálá nabídka","den":""},
            {"nazev":"crème brûlée","popis":"jemný vanilkový krém s karamelizovanou vrstvičkou","cena":59.00,
             "obrazek_url":None,"kategorie":"stálá nabídka","den":""},
            {"nazev":"craquelin","popis":"větrník se slaným karamelem","cena":65.00,
             "obrazek_url":None,"kategorie":"stálá nabídka","den":""},
            {"nazev":"bounty cheesecake","popis":"čokoládový dort s kokosem a sušenkovým základem","cena":79.00,
             "obrazek_url":None,"kategorie":"stálá nabídka","den":""},
            {"nazev":"malinové brownies","popis":"kakaové brownies s čerstvými malinami","cena":75.00,
             "obrazek_url":None,"kategorie":"stálá nabídka","den":""},
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
            "Vejce": "vejce a výrobky z něj",
            "Ryby":  "rybí produkty",
            "Ořechy":"piniové a pekanové ořechy"
        }
        for nazev, popis in alergeny.items():
            if not db.session.query(Alergen).filter_by(nazev=nazev).first():
                db.session.add(Alergen(nazev=nazev, popis=popis))
        db.session.commit()

        # 3) Seed vazeb položka↔alergen
        menu_alergeny = {
            "Sýrová pizza":              ["Lepek","Mléko"],
            "Hovězí burger":             ["Lepek"],
            "Caesar salát":              ["Vejce","Ryby","Mléko"],
            "naše focaccia":             ["Lepek","Mléko"],
            "Klimoszkovic kulajda":      ["Vejce"],
            "hovězí tatarák":            ["Lepek","Mléko"],
            "římský salát":              ["Lepek","Mléko"],
            "vepřová žebra":             ["Lepek"],
            "ball tip steak (USA)":      ["Mléko"],
            "cordon bleu":               ["Lepek","Mléko"],
            "svíčková na smetaně":       ["Lepek","Mléko"],
            "bramborové noky":           ["Ořechy"],
            "vepřová panenka 55":        ["Mléko"],
            "řízek pro prcky":           ["Lepek","Mléko"],
            "burger s trhaným vepřovým": ["Lepek","Mléko"],
            "buchty jako od babičky":    ["Lepek","Mléko"],
            "paris brest":               ["Ořechy","Vejce","Mléko"],
            "crème brûlée":              ["Vejce","Mléko"],
            "craquelin":                 ["Lepek","Vejce","Mléko"],
            "bounty cheesecake":         ["Lepek","Vejce","Mléko"],
            "malinové brownies":         ["Lepek","Vejce","Mléko"]
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
