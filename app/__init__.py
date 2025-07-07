import os
import warnings
from datetime import date
from flask import Flask, jsonify, request, current_app
from flask_smorest import Api
from flask_jwt_extended import JWTManager, create_access_token, get_jwt, get_jwt_identity
from werkzeug.exceptions import NotFound, UnprocessableEntity
from flask_cors import CORS
from werkzeug.utils import secure_filename

from .config import config_by_name
from .db import db, migrate
from .models import (
    Zakaznik, VernostniUcet, Rezervace, Stul, Salonek,
    PodnikovaAkce, Objednavka, PolozkaObjednavky, Platba,
    Hodnoceni, PolozkaMenu, PolozkaMenuAlergen,
    JidelniPlan, PolozkaJidelnihoPlanu, Alergen,
    Notifikace, Role, TokenBlacklist
)

# potlačíme varování o duplicitních schématech pro OpenAPI
warnings.filterwarnings(
    "ignore",
    "Multiple schemas resolved to the name",
    UserWarning,
    module="apispec.ext.marshmallow.openapi"
)

def create_app(config_name=None, config_override=None):
    if not config_name:
        config_name = os.getenv("FLASK_CONFIG", "default")

    app = Flask(__name__)
    app.json.ensure_ascii = False

    # načtení configu
    if config_override:
        app.config.from_object(config_override)
    else:
        app.config.from_object(config_by_name[config_name])
    app.config.setdefault("JSON_AS_ASCII", False)

    # složka pro upload obrázků
    upload_folder = os.path.join(app.root_path, 'static', 'images')
    app.config['UPLOAD_FOLDER'] = upload_folder
    os.makedirs(upload_folder, exist_ok=True)

    # CORS
    CORS(
        app,
        resources={r"/api/*": {"origins": "http://localhost:3000"}},
        supports_credentials=True
    )

    # DB + migrace
    db.init_app(app)
    migrate.init_app(app, db)

    # JWT
    jwt = JWTManager(app)

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload["jti"]
        return db.session.query(TokenBlacklist).filter_by(jti=jti).first() is not None

    # dev‐mode token injector
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

    # SSE token z query param
    @app.before_request
    def _inject_token_from_query():
        if request.path.startswith("/api/events") and not request.headers.get("Authorization"):
            token = request.args.get("token")
            if token:
                request.environ["HTTP_AUTHORIZATION"] = f"Bearer {token}"

    # Blueprinty
    api = Api(app)
    from .api import api_bp
    from .api.auth import auth_bp
    api.register_blueprint(api_bp)
    api.register_blueprint(auth_bp)

    # ─── HANDLERY CHYB ──────────────────────────────────────────────────────────

    # 422 Unprocessable Entity (validace vstupu Marshmallow)
    @app.errorhandler(UnprocessableEntity)
    def handle_unprocessable(err):
        data = getattr(err, 'data', {}) or {}
        messages = data.get('messages', {})
        return jsonify({
            "status": "Chybný vstup",
            "code": 422,
            "errors": messages
        }), 422

    # 404 Not Found
    @app.errorhandler(NotFound)
    def handle_404(err):
        msg = err.description or "Nenalezeno"
        return jsonify({
            "status": "Nenalezeno",
            "code": 404,
            "message": msg
        }), 404

    # GENERICKÝ HANDLER PRO KÓD 422
    @app.errorhandler(422)
    def handle_422(err):
        # pro případ, že někde vrátíme abort(422,...)
        data = getattr(err, 'data', {}) or {}
        messages = data.get('messages', {}) if isinstance(data, dict) else {}
        return jsonify({
            "status": "Chybný vstup",
            "code": 422,
            "errors": messages
        }), 422

    # jednoduchý testovací endpoint
    @app.route("/hello")
    def hello():
        return "Hello, World from Flask!"

    return app
