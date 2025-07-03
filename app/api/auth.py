from flask.views import MethodView
from flask_smorest import Blueprint, abort
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)

from ..db import db
from ..models import Zakaznik, TokenBlacklist
from ..schemas import LoginSchema

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/login")
class LoginResource(MethodView):
    """
    POST /api/auth/login
    - @arguments(LoginSchema): validuje email, password
    - Ověříme uživatele a heslo, abort(401) při chybě
    - Vytvoříme access i refresh token s rolemi
    - Vrací { "access_token": ..., "refresh_token": ... }
    """
    @auth_bp.arguments(LoginSchema)
    def post(self, data):
        user = db.session.query(Zakaznik).filter_by(
            email=data["email"]).first()
        if not user or not user.check_password(data["password"]):
            abort(401, message="Neplatné přihlašovací údaje.")
        roles = [r.name for r in user.roles]
        access_token = create_access_token(
            identity=str(user.id_zakaznika),
            additional_claims={"roles": roles}
        )
        refresh_token = create_refresh_token(identity=str(user.id_zakaznika))
        return {"access_token": access_token, "refresh_token": refresh_token}


@auth_bp.route("/me")
class MeResource(MethodView):
    """
    GET /api/auth/me
    - @jwt_required(): vyžaduje platný access token
    - Vrací základní informace o přihlášeném uživateli včetně rolí
    """
    @jwt_required()
    @auth_bp.response(200)
    def get(self):
        user_id = get_jwt_identity()
        user = db.session.get(Zakaznik, int(user_id))
        if not user:
            abort(404, message="Uživatel nenalezen.")
        return {
            "id":       user.id_zakaznika,
            "email":    user.email,
            "jmeno":    user.jmeno,
            "prijmeni": user.prijmeni,
            "roles":    [r.name for r in user.roles]
        }


@auth_bp.route("/refresh")
class RefreshResource(MethodView):
    """
    POST /api/auth/refresh
    - @jwt_required(refresh=True): vyžaduje validní refresh token
    - Vygeneruje nový access token se stejnými rolemi
    """
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


@auth_bp.route("/logout")
class LogoutResource(MethodView):
    """
    POST /api/auth/logout
    - @jwt_required(): přidá aktuální access token do blacklistu
    """
    @jwt_required()
    def post(self):
        jti = get_jwt()["jti"]
        db.session.add(TokenBlacklist(jti=jti))
        db.session.commit()
        return {"msg": "Token zablokován, jste odhlášeni."}, 200
