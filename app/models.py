# app/models.py

from .db import db                                    # db = SQLAlchemy instance
from sqlalchemy import CheckConstraint                 # pro kontrolu podmínek na úrovni DB
from werkzeug.security import generate_password_hash, check_password_hash  
                                                      # pro hashování a ověřování hesel
from datetime import datetime, date                         # pro časové razítko blacklistu

# ──────────────────────────────────────────────────────────────────────────────
# PARAMETRY:
# - nullable=False → sloupec je NOT NULL (musíte zadat hodnotu)
# - nullable=True  → sloupec může být NULL (volitelný)
# - back_populates="attr" → propojí vztahy obou tříd, aby byly synchronní
# - lazy="dynamic" → vztah vrací Query objekt, data se načtou teprve při volání .all(), .filter() apod.
# ──────────────────────────────────────────────────────────────────────────────

# ——— spojka Zakaznik ↔ Role —————————————————————————————
user_roles = db.Table(
    "user_roles",
    db.Column("zakaznik_id", db.Integer,
              db.ForeignKey("zakaznik.id_zakaznika"), primary_key=True),
    db.Column("role_id",     db.Integer,
              db.ForeignKey("role.id_role"),           primary_key=True),
)


class Zakaznik(db.Model):
    """
    Zákazník:
    - při vytvoření musíte zadat jmeno, prijmeni, email a password
    - telefon je volitelný
    - vztahy:
        ucet       (1:1 → VernostniUcet)
        rezervace  (1:N → Rezervace)
        objednavky (1:N → Objednavka)
        hodnoceni  (1:N → Hodnoceni)
    """
    __tablename__ = "zakaznik"
    id_zakaznika = db.Column(db.Integer, primary_key=True)  
    jmeno        = db.Column(db.String(50),  nullable=False)  
    prijmeni     = db.Column(db.String(50),  nullable=False)
    telefon      = db.Column(db.String(20),  nullable=True)    # může být NULL
    email        = db.Column(db.String(100), nullable=False, unique=True)
    _password    = db.Column("password", db.String(255), nullable=False, server_default="")  
                                                          # uložený hash hesla

    # vztahy
    ucet       = db.relationship(
        "VernostniUcet",
        back_populates="zakaznik",
        uselist=False,               # 1:1
        cascade="all, delete-orphan"
    )
    rezervace  = db.relationship("Rezervace",    back_populates="zakaznik", lazy="dynamic")
    objednavky = db.relationship("Objednavka",   back_populates="zakaznik", lazy="dynamic")
    hodnoceni  = db.relationship("Hodnoceni",    back_populates="zakaznik", lazy="dynamic")

    # many-to-many: uživatel může mít více rolí
    roles = db.relationship(
        "Role",
        secondary=user_roles,
        backref=db.backref("zakaznici", lazy="dynamic"),
        lazy="dynamic",
    )

    def __repr__(self):
        return f"<Zakaznik {self.jmeno} {self.prijmeni}>"

    @property
    def password(self):
        # zabrání přímému čtení atributu .password
        raise AttributeError("Heslo nelze číst v čistém textu.")

    @password.setter
    def password(self, raw_password: str):
        # vytvoří hash z raw_password a uloží ho do _password
        self._password = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        # porovná raw_password s uloženým hashem
        return check_password_hash(self._password, raw_password)


class VernostniUcet(db.Model):
    """
    Věrnostní účet:
    - vytvoří se automaticky při přidání Zakaznik (v routes.py)
    - body            (int, default 0)
    - datum_zalozeni  (date, NOT NULL, default = dnes)
    - vztah 1:1 zpět na Zakaznik
    """
    __tablename__ = "vernostni_ucet"

    id_ucet        = db.Column(db.Integer, primary_key=True)
    body           = db.Column(db.Integer, nullable=False, default=0)
    datum_zalozeni = db.Column(db.Date,    nullable=False, default=date.today)
    id_zakaznika   = db.Column(
        db.Integer,
        db.ForeignKey("zakaznik.id_zakaznika", ondelete="CASCADE"),
        nullable=False
    )

    # uselist=False => 1:1 vztah
    zakaznik = db.relationship("Zakaznik", back_populates="ucet", uselist=False)

    def __repr__(self):
        return (
            f"<VernostniUcet id={self.id_ucet} "
            f"body={self.body} "
            f"zalozeno={self.datum_zalozeni.isoformat()}>"
        )


class Rezervace(db.Model):
    __tablename__ = "rezervace"
    __table_args__ = (
        CheckConstraint(
            "(id_stul IS NOT NULL) OR (id_salonek IS NOT NULL) OR (id_akce IS NOT NULL)",
            name="chk_rezervace_misto"
        ),
    )
    id_rezervace   = db.Column(db.Integer, primary_key=True)
    datum_cas      = db.Column(db.DateTime, nullable=False)
    pocet_osob     = db.Column(db.Integer,  nullable=False)
    stav_rezervace = db.Column(db.String(20), nullable=False, default="čekající")
    sleva          = db.Column(db.Numeric(5, 2), nullable=True)
    id_zakaznika   = db.Column(db.Integer, db.ForeignKey("zakaznik.id_zakaznika", ondelete="CASCADE"), nullable=False)
    id_stul        = db.Column(db.Integer, db.ForeignKey("stul.id_stul"),      nullable=True)
    id_salonek     = db.Column(db.Integer, db.ForeignKey("salonek.id_salonek"), nullable=True)
    id_akce        = db.Column(db.Integer, db.ForeignKey("podnikova_akce.id_akce"), nullable=True)

    zakaznik   = db.relationship("Zakaznik", back_populates="rezervace")
    stul       = db.relationship("Stul",      back_populates="rezervace")
    salonek    = db.relationship("Salonek",   back_populates="rezervace")
    akce       = db.relationship("PodnikovaAkce", back_populates="rezervace")      # ← přidáno
    notifikace = db.relationship("Notifikace", back_populates="rezervace", lazy="dynamic")

    def __repr__(self):
        return f"<Rezervace {self.id_rezervace} {self.datum_cas}>"


class Stul(db.Model):
    """
    Stůl:
    - cislo, kapacita jsou povinné
    - popis volitelný
    - vztah 1:N na Rezervace
    """
    __tablename__ = "stul"
    id_stul   = db.Column(db.Integer, primary_key=True)
    cislo     = db.Column(db.Integer, nullable=False, unique=True)
    kapacita  = db.Column(db.Integer, nullable=False)
    popis     = db.Column(db.Text,    nullable=True)

    rezervace = db.relationship("Rezervace", back_populates="stul", lazy="dynamic")

    def __repr__(self):
        return f"<Stul {self.cislo} cap={self.kapacita}>"


class Salonek(db.Model):
    """
    Salónek:
    - nazev, kapacita povinné; popis volitelný
    - vztahy: Rezervace (1:N), PodnikovaAkce (1:N)
    """
    __tablename__ = "salonek"
    id_salonek = db.Column(db.Integer, primary_key=True)
    nazev      = db.Column(db.String(100), nullable=False)
    kapacita   = db.Column(db.Integer,       nullable=False)
    popis      = db.Column(db.Text,          nullable=True)

    rezervace = db.relationship("Rezervace",      back_populates="salonek", lazy="dynamic")
    akce      = db.relationship("PodnikovaAkce", back_populates="salonek", lazy="dynamic")

    def __repr__(self):
        return f"<Salonek {self.nazev} cap={self.kapacita}>"


class PodnikovaAkce(db.Model):
    __tablename__ = "podnikova_akce"
    id_akce    = db.Column(db.Integer, primary_key=True)
    nazev      = db.Column(db.String(100), nullable=False)
    popis      = db.Column(db.Text,           nullable=True)
    datum      = db.Column(db.Date,           nullable=False)
    cas        = db.Column(db.Time,           nullable=False)
    id_salonek = db.Column(db.Integer, db.ForeignKey("salonek.id_salonek"), nullable=False)

    salonek   = db.relationship("Salonek",   back_populates="akce")
    rezervace = db.relationship("Rezervace", back_populates="akce", lazy="dynamic")

    def __repr__(self):
        return f"<PodnikovaAkce {self.nazev} {self.datum}>"


class Objednavka(db.Model):
    """
    Objednavka:
    - datum_cas, id_zakaznika povinné; stav, celkova_castka volitelné
    - vztahy: PolozkaObjednavky, Platba, Hodnoceni, Notifikace
    """
    __tablename__ = "objednavka"

    id_objednavky     = db.Column(db.Integer, primary_key=True)
    datum_cas         = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    stav              = db.Column(
                           db.String(20),
                           nullable=False,
                           default="PENDING"
                       )
    celkova_castka    = db.Column(db.Numeric(8, 2), nullable=True)
    id_zakaznika      = db.Column(
                           db.Integer,
                           db.ForeignKey("zakaznik.id_zakaznika", ondelete="CASCADE"),
                           nullable=False
                       )

    # nová pole s českými názvy
    cas_pripravy     = db.Column(db.DateTime, nullable=True)
    body_ziskane     = db.Column(db.Integer, nullable=False, default=0)

    zakaznik   = db.relationship("Zakaznik", back_populates="objednavky")
    polozky    = db.relationship("PolozkaObjednavky", back_populates="objednavka", lazy="dynamic")
    platby     = db.relationship("Platba", back_populates="objednavka", lazy="dynamic")
    hodnoceni  = db.relationship("Hodnoceni", back_populates="objednavka", lazy="dynamic")
    notifikace = db.relationship("Notifikace", back_populates="objednavka", lazy="dynamic")

    def __repr__(self):
        return f"<Objednavka {self.id_objednavky}>"

class PolozkaObjednavky(db.Model):
    """
    PolozkaObjednavky:
    - mnozstvi, cena, id_objednavky, id_menu_polozka povinné
    """
    __tablename__ = "polozka_objednavky"
    id_polozky_obj  = db.Column(db.Integer, primary_key=True)
    mnozstvi        = db.Column(db.Integer, nullable=False)
    cena            = db.Column(db.Numeric(8, 2), nullable=False)
    id_objednavky   = db.Column(db.Integer, db.ForeignKey("objednavka.id_objednavky"), nullable=False)
    id_menu_polozka = db.Column(db.Integer, db.ForeignKey("polozka_menu.id_menu_polozka"), nullable=False)

    objednavka   = db.relationship("Objednavka",        back_populates="polozky")
    menu_polozka = db.relationship("PolozkaMenu",        back_populates="objednavky")

    def __repr__(self):
        return f"<PolozkaObjednavky {self.id_polozky_obj} qty={self.mnozstvi}>"


class Platba(db.Model):
    """
    Platba:
    - castka, typ_platby, datum, id_objednavky povinné
    """
    __tablename__ = "platba"
    id_platba     = db.Column(db.Integer, primary_key=True)
    castka        = db.Column(db.Numeric(8, 2), nullable=False)
    typ_platby    = db.Column(db.String(20),    nullable=False)
    datum         = db.Column(db.DateTime,      nullable=False)
    id_objednavky = db.Column(db.Integer, db.ForeignKey("objednavka.id_objednavky"), nullable=False)

    objednavka = db.relationship("Objednavka", back_populates="platby")

    def __repr__(self):
        return f"<Platba {self.id_platba} amt={self.castka}>"


class Hodnoceni(db.Model):
    """
    Hodnoceni:
    - hodnoceni, datum, id_objednavky, id_zakaznika povinné; komentar volitelný
    """
    __tablename__ = "hodnoceni"
    id_hodnoceni   = db.Column(db.Integer, primary_key=True)
    hodnoceni      = db.Column(db.SmallInteger, nullable=False)
    komentar       = db.Column(db.Text,           nullable=True)
    datum          = db.Column(db.DateTime,       nullable=False)
    id_objednavky  = db.Column(db.Integer, db.ForeignKey("objednavka.id_objednavky"), nullable=False)
    id_zakaznika   = db.Column(db.Integer, db.ForeignKey("zakaznik.id_zakaznika", ondelete="CASCADE"), nullable=False)

    objednavka = db.relationship("Objednavka", back_populates="hodnoceni")
    zakaznik   = db.relationship("Zakaznik",    back_populates="hodnoceni")

    def __repr__(self):
        return f"<Hodnoceni {self.id_hodnoceni} score={self.hodnoceni}>"


class PolozkaMenu(db.Model):
    __tablename__ = "polozka_menu"

    id_menu_polozka = db.Column(db.Integer, primary_key=True)
    nazev           = db.Column(db.String(100), nullable=False)
    popis           = db.Column(db.Text,           nullable=True)
    cena            = db.Column(db.Numeric(8, 2),  nullable=False)
    obrazek_url     = db.Column(db.String,         nullable=True)
    kategorie       = db.Column(db.String(20),     nullable=False)  # 'týdenní' nebo 'víkendové'
    den             = db.Column(db.String(10),     nullable=False)  # 'Pondělí' … 'Neděle'

    objednavky = db.relationship(
        "PolozkaObjednavky",
        back_populates="menu_polozka",
        lazy="dynamic",
    )
    alergeny = db.relationship(
        "PolozkaMenuAlergen",
        back_populates="menu_polozka",
        lazy="selectin",
    )
    plany = db.relationship(
        "PolozkaJidelnihoPlanu",
        back_populates="menu_polozka",
        lazy="dynamic",
    )

    def __repr__(self):
        return f"<PolozkaMenu {self.nazev}>"


class PolozkaMenuAlergen(db.Model):
    __tablename__ = "polozka_menu_alergen"
    id_menu_polozka = db.Column(db.Integer, db.ForeignKey("polozka_menu.id_menu_polozka"), primary_key=True)
    id_alergenu     = db.Column(db.Integer, db.ForeignKey("alergen.id_alergenu"),           primary_key=True)

    menu_polozka = db.relationship("PolozkaMenu", back_populates="alergeny")
    alergen      = db.relationship("Alergen",      back_populates="polozky")

    def __repr__(self):
        return f"<PMA {self.id_menu_polozka}/{self.id_alergenu}>"



class JidelniPlan(db.Model):
    """
    JidelniPlan:
    - nazev, platny_od povinné; platny_do volitelné
    - vztah: polozky (1:N)
    """
    __tablename__ = "jidelni_plan"
    id_plan    = db.Column(db.Integer, primary_key=True)
    nazev      = db.Column(db.String(100), nullable=False)
    platny_od  = db.Column(db.Date,           nullable=False)
    platny_do  = db.Column(db.Date,           nullable=True)

    polozky = db.relationship("PolozkaJidelnihoPlanu", back_populates="plan", lazy="dynamic")

    def __repr__(self):
        return f"<JidelniPlan {self.nazev}>"


class PolozkaJidelnihoPlanu(db.Model):
    """
    PolozkaJidelnihoPlanu:
    - den, poradi, id_plan, id_menu_polozka povinné
    """
    __tablename__ = "polozka_jidelniho_planu"
    id_polozka_jid_pl = db.Column(db.Integer, primary_key=True)
    den               = db.Column(db.Date,    nullable=False)
    poradi            = db.Column(db.Integer, nullable=False)
    id_plan           = db.Column(db.Integer, db.ForeignKey("jidelni_plan.id_plan"),            nullable=False)
    id_menu_polozka   = db.Column(db.Integer, db.ForeignKey("polozka_menu.id_menu_polozka"),     nullable=False)

    plan         = db.relationship("JidelniPlan", back_populates="polozky")
    menu_polozka = db.relationship("PolozkaMenu", back_populates="plany")

    def __repr__(self):
        return f"<PolozkaJidelnihoPlanu {self.id_polozka_jid_pl}>"


class Alergen(db.Model):
    __tablename__ = "alergen"
    id_alergenu = db.Column(db.Integer, primary_key=True)
    nazev       = db.Column(db.String(100), nullable=False)
    popis       = db.Column(db.Text,           nullable=True)

    # ← ZDE jsme změnili lazy z "dynamic" na "selectin":
    polozky = db.relationship(
        "PolozkaMenuAlergen",
        back_populates="alergen",
        lazy="selectin",
    )

    def __repr__(self):
        return f"<Alergen {self.nazev}>"

class Notifikace(db.Model):
    """
    Notifikace:
    - typ, datum_cas povinné; text, id_rezervace, id_objednavky volitelné
    - vztahy: Rezervace, Objednavka
    """
    __tablename__    = "notifikace"
    id_notifikace    = db.Column(db.Integer, primary_key=True)
    typ              = db.Column(db.String(20), nullable=False)
    datum_cas        = db.Column(db.DateTime, nullable=False)
    text             = db.Column(db.Text,     nullable=True)
    id_rezervace     = db.Column(db.Integer,  db.ForeignKey("rezervace.id_rezervace"), nullable=True)
    id_objednavky    = db.Column(db.Integer,  db.ForeignKey("objednavka.id_objednavky"), nullable=True)

    rezervace   = db.relationship("Rezervace",   back_populates="notifikace")
    objednavka  = db.relationship("Objednavka",  back_populates="notifikace")

    def __repr__(self):
        return f"<Notifikace {self.id_notifikace} type={self.typ}>"


class Role(db.Model):
    """
    Role:
    - id_role: primární klíč
    - name: unikátní název role (např. "admin", "editor")
    - description: nepovinný popis role
    """
    __tablename__ = "role"
    id_role       = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(30), unique=True, nullable=False)
    description   = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f"<Role {self.name}>"


class TokenBlacklist(db.Model):
    """
    TokenBlacklist:
    - id: primární klíč
    - jti: jedinečný identifikátor JWT (token ID)
    - created_at: čas přidání na blacklist
    """
    __tablename__ = "token_blacklist"
    id          = db.Column(db.Integer, primary_key=True)
    jti         = db.Column(db.String(36), unique=True, nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
