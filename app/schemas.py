from marshmallow import Schema, fields, validate, validates_schema, ValidationError, post_dump

# — LOGIN schéma —
class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)

# — SUMMARY schémata —
class RezervaceSummarySchema(Schema):
    id_rezervace  = fields.Int()
    datum_cas     = fields.DateTime()
    pocet_osob    = fields.Int()
    stav_rezervace= fields.Str()

class ZakaznikSummarySchema(Schema):
    id_zakaznika = fields.Int()
    jmeno        = fields.Str()
    prijmeni     = fields.Str()

class ObjednavkaSummarySchema(Schema):
    id_objednavky= fields.Int()
    datum_cas    = fields.DateTime()
    stav         = fields.Str()

class HodnoceniSummarySchema(Schema):
    id_hodnoceni= fields.Int()
    hodnoceni   = fields.Int()
    komentar     = fields.Str()

class PlatbaSummarySchema(Schema):
    id_platba = fields.Int()
    castka    = fields.Decimal(as_string=True)
    typ_platby= fields.Str()
    datum     = fields.DateTime()

class PolozkaObjednavkySummarySchema(Schema):
    id_polozky_obj = fields.Int()
    mnozstvi       = fields.Int()
    cena           = fields.Decimal(as_string=True)

class NotifikaceSummarySchema(Schema):
    id_notifikace = fields.Int()
    typ            = fields.Str()
    datum_cas      = fields.DateTime()
    text           = fields.Str()

class PodnikovaAkceSummarySchema(Schema):
    id_akce = fields.Int()
    nazev    = fields.Str()
    datum    = fields.Date()
    cas      = fields.Time()


# — Zákazník —
class ZakaznikSchema(Schema):
    id_zakaznika = fields.Int(dump_only=True)
    jmeno = fields.Str(required=True, validate=validate.Length(min=1))
    prijmeni = fields.Str(required=True, validate=validate.Length(min=1))
    email = fields.Email(required=True)
    telefon = fields.Str(validate=validate.Length(max=20))
    ucet = fields.Nested("VernostniUcetSchema", dump_only=True, allow_none=True)
    rezervace = fields.Nested("RezervaceSummarySchema", many=True, dump_only=True)
    objednavky = fields.Nested("ObjednavkaSummarySchema", many=True, dump_only=True)
    hodnoceni = fields.Nested("HodnoceniSummarySchema", many=True, dump_only=True)
    roles = fields.Method("get_roles", dump_only=True)

    @post_dump
    def replace_empty_relations(self, data, **kwargs):
        if data.get("telefon") is None:
            data["telefon"] = "Žádné telefonní číslo"
        if data.get("ucet") is None:
            data["ucet"] = "Žádný účet"
        if not data.get("objednavky"):
            data["objednavky"] = "Žádné objednávky"
        if not data.get("rezervace"):
            data["rezervace"] = "Žádné rezervace"
        if not data.get("hodnoceni"):
            data["hodnoceni"] = "Žádná hodnocení"
        return data

    def get_roles(self, obj):
        mapping = {"user":"Uživatel","staff":"Pracovník","admin":"Administrátor"}
        return [mapping.get(r.name, r.name) for r in obj.roles]

class ZakaznikCreateSchema(Schema):
    jmeno = fields.Str(required=True, validate=validate.Length(min=1))
    prijmeni = fields.Str(required=True, validate=validate.Length(min=1))
    email = fields.Email(required=True)
    telefon = fields.Str(validate=validate.Length(max=20))
    password = fields.Str(
        required=True,
        load_only=True,
        validate=validate.Length(min=8, error="Heslo musí mít alespoň 8 znaků")
    )

# — Vernostní účet —
class VernostniUcetSchema(Schema):
    id_ucet = fields.Int(dump_only=True)
    body = fields.Int()
    datum_zalozeni = fields.Date()
    zakaznik = fields.Nested(ZakaznikSummarySchema, dump_only=True)

class VernostniUcetCreateSchema(Schema):
    body = fields.Int()
    datum_zalozeni = fields.Date(required=True)
    id_zakaznika = fields.Int(required=True)

# — Rezervace —
class RezervaceSchema(Schema):
    id_rezervace = fields.Int(dump_only=True)
    datum_cas = fields.DateTime()
    pocet_osob = fields.Int()
    stav_rezervace = fields.Str(missing="čekající")
    sleva = fields.Decimal(as_string=True)
    zakaznik = fields.Nested(ZakaznikSummarySchema, dump_only=True)
    stul = fields.Nested("StulSchema", dump_only=True, allow_none=True)
    salonek = fields.Nested("SalonekSchema", dump_only=True, allow_none=True)
    akce = fields.Nested(PodnikovaAkceSummarySchema, dump_only=True, allow_none=True)
    notifikace = fields.Nested(NotifikaceSummarySchema, many=True, dump_only=True)

    @post_dump
    def replace_nulls(self, data, **kwargs):
        if data.get("stul") is None:
            data["stul"] = "Stůl je dostupný"
        if data.get("salonek") is None:
            data["salonek"] = "Žádný salónek"
        if data.get("akce") is None:
            data["akce"] = "Žádná akce"
        if not data.get("notifikace"):
            data["notifikace"] = "Žádné notifikace"
        return data

class RezervaceCreateSchema(Schema):
    datum_cas = fields.DateTime(required=True)
    pocet_osob = fields.Int(required=True)
    stav_rezervace = fields.Str()
    sleva = fields.Decimal(as_string=True)
    id_zakaznika = fields.Int(load_only=True)
    id_stul = fields.Int(allow_none=True)
    id_salonek = fields.Int(allow_none=True)
    id_akce = fields.Int(allow_none=True)

    @validates_schema
    def require_place(self, data, **kwargs):
        if not data.get("id_stul") and not data.get("id_salonek") and not data.get("id_akce"):
            raise ValidationError(
                "Musíte vyplnit buď 'id_stul', 'id_salonek' nebo 'id_akce'.",
                field_names=["id_stul","id_salonek","id_akce"]
            )

# — Stůl —
class StulSchema(Schema):
    id_stul = fields.Int(dump_only=True)
    cislo = fields.Int()
    kapacita = fields.Int()
    popis = fields.Str()
    rezervace = fields.Nested(RezervaceSummarySchema, many=True, dump_only=True)

class StulCreateSchema(Schema):
    cislo = fields.Int(required=True)
    kapacita = fields.Int(required=True)
    popis = fields.Str()

# — Salonek —
class SalonekSchema(Schema):
    id_salonek = fields.Int(dump_only=True)
    nazev = fields.Str()
    kapacita = fields.Int()
    popis = fields.Str()
    rezervace = fields.Nested(RezervaceSummarySchema, many=True, dump_only=True)
    akce = fields.Nested(PodnikovaAkceSummarySchema, many=True, dump_only=True)

class SalonekCreateSchema(Schema):
    nazev = fields.Str(required=True)
    kapacita = fields.Int(required=True)
    popis = fields.Str()

# — Podniková akce —
class PodnikovaAkceSchema(Schema):
    id_akce = fields.Int(dump_only=True)
    nazev = fields.Str()
    popis = fields.Str()
    datum = fields.Date()
    cas = fields.Time()
    salonek = fields.Nested(SalonekSchema, dump_only=True)

class PodnikovaAkceCreateSchema(Schema):
    nazev = fields.Str(required=True)
    popis = fields.Str()
    datum = fields.Date(required=True)
    cas = fields.Time(required=True)
    id_salonek = fields.Int(required=True)

# — Objednávka —
class ObjednavkaSchema(Schema):
    id_objednavky   = fields.Int(dump_only=True)
    datum_cas       = fields.DateTime()
    stav            = fields.Str()
    cas_pripravy    = fields.DateTime(dump_only=True)
    body_ziskane    = fields.Int(dump_only=True)
    celkova_castka  = fields.Decimal(as_string=True)
    zakaznik        = fields.Nested(ZakaznikSummarySchema, dump_only=True)
    polozky         = fields.Nested(PolozkaObjednavkySummarySchema, many=True, dump_only=True)
    platby          = fields.Nested(PlatbaSummarySchema, many=True, dump_only=True)
    hodnoceni       = fields.Nested(HodnoceniSummarySchema, many=True, dump_only=True)
    notifikace      = fields.Nested(NotifikaceSummarySchema, many=True, dump_only=True)

# ** toto použij pro POST /objednavka **  
class ObjednavkaUserCreateSchema(Schema):
    datum_cas       = fields.DateTime(required=True)
    stav            = fields.Str(missing="čekající")
    celkova_castka  = fields.Decimal(as_string=True, required=True)
    # id_zakaznika INJEKTUJEME V KÓDU, NE POSÍLÁ SE Z FRONTENDU

# ** ponechávám pro interní použití, ale už ho NEVIAŽ na POST routu **
class ObjednavkaCreateSchema(Schema):
    datum_cas       = fields.DateTime(required=True)
    stav            = fields.Str()
    celkova_castka  = fields.Decimal(as_string=True)
    id_zakaznika    = fields.Int(required=True)

# — Položka objednávky —
class PolozkaObjednavkySchema(Schema):
    id_polozky_obj = fields.Int(dump_only=True)
    mnozstvi = fields.Int()
    cena = fields.Decimal(as_string=True)
    menu_polozka = fields.Nested("PolozkaMenuSchema", dump_only=True)

class PolozkaObjednavkyCreateSchema(Schema):
    mnozstvi = fields.Int(required=True)
    cena = fields.Decimal(as_string=True, required=True)
    id_menu_polozka = fields.Int(required=True)
    id_objednavky = fields.Int(required=True)

# — Platba —
class PlatbaSchema(Schema):
    id_platba    = fields.Int(dump_only=True)
    castka       = fields.Decimal(as_string=True)
    typ_platby   = fields.Str()
    datum        = fields.DateTime()
    objednavka   = fields.Nested(ObjednavkaSummarySchema, dump_only=True)
    body_ziskane = fields.Int(dump_only=True)   # přidáno
    body_celkem  = fields.Int(dump_only=True)   # přidáno

class PlatbaCreateSchema(Schema):
    castka = fields.Decimal(as_string=True, required=True)
    typ_platby = fields.Str(required=True)
    datum = fields.DateTime(required=True)
    id_objednavky = fields.Int(required=True)

# — Hodnocení —
class HodnoceniSchema(Schema):
    id_hodnoceni = fields.Int(dump_only=True)
    hodnoceni = fields.Int()
    komentar = fields.Str()
    datum = fields.DateTime()
    zakaznik = fields.Nested(ZakaznikSummarySchema, dump_only=True)
    objednavka = fields.Nested(ObjednavkaSummarySchema, dump_only=True)

class HodnoceniCreateSchema(Schema):
    hodnoceni = fields.Int(required=True)
    komentar = fields.Str()
    datum = fields.DateTime(required=True)
    id_objednavky = fields.Int(required=True)
    id_zakaznika = fields.Int(required=True)

# — Položka menu —
class PolozkaMenuSchema(Schema):
    id_menu_polozka = fields.Int(dump_only=True)
    nazev           = fields.Str(required=True)
    popis           = fields.Str(load_default="", allow_none=False)
    cena            = fields.Decimal(as_string=True)
    obrazek_url     = fields.Str()
    kategorie       = fields.Str()
    den             = fields.Str(allow_none=True)
    alergeny        = fields.Method("get_alergeny", dump_only=True)

    def get_alergeny(self, obj):
        return [
            {"id_alergenu": link.id_alergenu, "nazev": link.alergen.nazev}
            for link in obj.alergeny
        ]

class PolozkaMenuCreateSchema(Schema):
    nazev       = fields.Str(required=True)
    popis       = fields.Str(load_default="", allow_none=False)
    cena        = fields.Decimal(as_string=True, required=True)
    obrazek_url = fields.Url(required=True)
    kategorie   = fields.Str(
        required=True,
        validate=validate.OneOf(["týdenní","víkendové","stálá nabídka"])
    )
    den         = fields.Str(
        allow_none=True,
        validate=validate.OneOf(
            ["Pondělí","Úterý","Středa","Čtvrtek","Pátek","Sobota","Neděle", None]
        )
    )

# — Položka menu ↔ alergen —
class PolozkaMenuAlergenSchema(Schema):
    id_menu_polozka = fields.Int(dump_only=True)
    id_alergenu = fields.Int(dump_only=True)

class PolozkaMenuAlergenCreateSchema(Schema):
    id_menu_polozka = fields.Int(required=True)
    id_alergenu = fields.Int(required=True)

# — Jídelní plán —
class JidelniPlanSchema(Schema):
    id_plan = fields.Int(dump_only=True)
    nazev = fields.Str()
    platny_od = fields.Date()
    platny_do = fields.Date()
    polozky = fields.Nested("PolozkaJidelnihoPlanuSummarySchema", many=True, dump_only=True)

class JidelniPlanCreateSchema(Schema):
    nazev = fields.Str(required=True)
    platny_od = fields.Date(required=True)
    platny_do = fields.Date()

class PolozkaJidelnihoPlanuSummarySchema(Schema):
    id_polozka_jid_pl = fields.Int()
    den = fields.Date()
    poradi = fields.Int()

class PolozkaJidelnihoPlanuSchema(Schema):
    id_polozka_jid_pl = fields.Int(dump_only=True)
    den = fields.Date()
    poradi = fields.Int()
    menu_polozka = fields.Nested("PolozkaMenuSchema", dump_only=True)
    plan = fields.Nested(JidelniPlanSchema, dump_only=True)

class PolozkaJidelnihoPlanuCreateSchema(Schema):
    den = fields.Date(required=True)
    poradi = fields.Int(required=True)
    id_plan = fields.Int(required=True)
    id_menu_polozka = fields.Int(required=True)

# — Alergen —
class AlergenSchema(Schema):
    id_alergenu = fields.Int(dump_only=True)
    nazev = fields.Str()
    popis = fields.Str()

class AlergenCreateSchema(Schema):
    nazev = fields.Str(required=True)
    popis = fields.Str()

# — Notifikace —
class NotifikaceSchema(Schema):
    id_notifikace = fields.Int(dump_only=True)
    typ = fields.Str()
    datum_cas = fields.DateTime()
    text = fields.Str()
    rezervace = fields.Nested(RezervaceSummarySchema, dump_only=True, allow_none=True)
    objednavka = fields.Nested(ObjednavkaSummarySchema, dump_only=True, allow_none=True)

class NotifikaceCreateSchema(Schema):
    typ = fields.Str(required=True)
    datum_cas = fields.DateTime(required=True)
    text = fields.Str()
    id_rezervace = fields.Int(allow_none=True)
    id_objednavky = fields.Int(allow_none=True)

# — Role / RBAC schémata —
class RoleSchema(Schema):
    id_role = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    description = fields.Str(allow_none=True)

class UserRoleAssignSchema(Schema):
    role_id = fields.Int(required=True)


# — Pro uplatnění bodů —
class RedeemSchema(Schema):
    points = fields.Int(required=True)