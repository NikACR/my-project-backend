import os
import click
from datetime import datetime, date, time, timedelta
from sqlalchemy import text

from app import create_app, db
from app.models import (
    Zakaznik, VernostniUcet, Rezervace, Stul, Salonek,
    PodnikovaAkce, Objednavka, PolozkaObjednavky,
    Platba, Hodnoceni, PolozkaMenu, PolozkaMenuAlergen,
    JidelniPlan, PolozkaJidelnihoPlanu, Alergen, Notifikace,
    Role
)

os.environ.setdefault("DATABASE_HOST", "localhost")

config_name = os.getenv("FLASK_CONFIG", "default")
app = create_app(config_name)


def _vycistit_databazi():
    db.session.query(PolozkaMenuAlergen).delete()
    db.session.query(Notifikace).delete()
    db.session.query(Hodnoceni).delete()
    db.session.query(Platba).delete()
    db.session.query(PolozkaObjednavky).delete()
    db.session.query(Objednavka).delete()
    db.session.query(PodnikovaAkce).delete()
    db.session.query(Rezervace).delete()
    db.session.query(PolozkaJidelnihoPlanu).delete()
    db.session.query(JidelniPlan).delete()
    db.session.query(Alergen).delete()
    db.session.query(PolozkaMenu).delete()
    db.session.query(Salonek).delete()
    db.session.query(Stul).delete()
    db.session.query(VernostniUcet).delete()
    # smažeme vazby user_roles, aby při mazání zakazniků nevznikl FK konflikt
    db.session.execute(text('DELETE FROM user_roles'))
    db.session.query(Zakaznik).delete()
    db.session.query(Role).delete()
    db.session.commit()


@app.cli.command("seed-db")
def seed_db():
    _vycistit_databazi()

    # 0) Role
    admin_role = Role(name="admin", description="Správce systému")
    staff_role = Role(name="staff", description="Obsluha")
    user_role  = Role(name="user",  description="Koncový zákazník")
    db.session.add_all([admin_role, staff_role, user_role])
    db.session.flush()

    # 1) Zákazníci (role=user)
    zak1 = Zakaznik(jmeno="Petr",    prijmeni="Svoboda",   email="petr.svoboda@example.cz",   telefon="603123456")
    zak1.password = "tajneheslo1"
    zak1.roles.append(user_role)

    zak2 = Zakaznik(jmeno="Eva",     prijmeni="Novotná",   email="eva.novotna@example.cz",    telefon="608987654")
    zak2.password = "tajneheslo2"
    zak2.roles.append(user_role)

    zak3 = Zakaznik(jmeno="Lukáš",   prijmeni="Krejčík",   email="lukas.krejcik@example.cz",  telefon="602555333")
    zak3.password = "tajneheslo3"
    zak3.roles.append(user_role)

    # 2) Staff účty
    staff1 = Zakaznik(jmeno="Anna",   prijmeni="Nováková",  email="anna.staff@example.com",   telefon="600111222")
    staff1.password = "heslo123"
    staff1.roles.append(staff_role)

    staff2 = Zakaznik(jmeno="Petr",   prijmeni="Pracník",   email="petr.staff@example.com",   telefon="600333444")
    staff2.password = "heslo123"
    staff2.roles.append(staff_role)

    staff3 = Zakaznik(jmeno="Eva",    prijmeni="Zaměstnaná",email="eva.staff@example.com",    telefon="600555666")
    staff3.password = "heslo123"
    staff3.roles.append(staff_role)

    # 3) Volitelný admin
    admin = Zakaznik(jmeno="Admin",   prijmeni="Root",      email="admin@example.com",        telefon=None)
    admin.password = "rootpass"
    admin.roles.append(admin_role)

    db.session.add_all([zak1, zak2, zak3, staff1, staff2, staff3, admin])
    db.session.commit()

    # 4) Věrnostní účty – všichni začínají na 0 bodech
    for zak in Zakaznik.query.all():
        db.session.add(
            VernostniUcet(
                body=0,
                datum_zalozeni=date.today(),
                zakaznik=zak
            )
        )
    db.session.commit()

    # 5) Stoly
    s1 = Stul(cislo=1, kapacita=4, popis="U okna")
    s2 = Stul(cislo=2, kapacita=2, popis="U stěny")
    s3 = Stul(cislo=3, kapacita=6, popis="Rodinný stůl")
    db.session.add_all([s1, s2, s3])

    # 6) Salónky
    sal1 = Salonek(nazev="Salónek Slunce", kapacita=20, popis="prostorný salónek se stolním fotbálkem")
    sal2 = Salonek(nazev="Salónek Měsíc",   kapacita=15, popis="útulný salónek s krbem")
    sal3 = Salonek(nazev="Salónek Hvězda",  kapacita=30, popis="velký salónek pro akce")
    db.session.add_all([sal1, sal2, sal3])

    # 7) Podnikové akce
    ak1 = PodnikovaAkce(
        nazev="Firemní večírek",
        popis="večerní setkání pro zaměstnance",
        datum=date.today() + timedelta(days=5),
        cas=time(18, 0),
        salonek=sal1
    )
    ak2 = PodnikovaAkce(
        nazev="Degustace vín",
        popis="ochutnávka vybraných vín",
        datum=date.today() + timedelta(days=10),
        cas=time(17, 30),
        salonek=sal2
    )
    ak3 = PodnikovaAkce(
        nazev="Květinový workshop",
        popis="tvořivá dílna",
        datum=date.today() + timedelta(days=15),
        cas=time(16, 0),
        salonek=sal3
    )
    db.session.add_all([ak1, ak2, ak3])

    # 8) Položky menu
    m1 = PolozkaMenu(nazev="Sýrová pizza", popis="italská pizza", cena=199.00)
    m2 = PolozkaMenu(nazev="Hovězí burger", popis="burger s hranolkami", cena=249.00)
    m3 = PolozkaMenu(nazev="Caesar salát", popis="čerstvý salát", cena=159.00)

    dnes_jmeno = datetime.now().strftime("%A")
    default_prep_time = 15
    for m in (m1, m2, m3):
        m.kategorie         = "Týdenní nabídka"
        m.den               = dnes_jmeno
        m.preparation_time  = default_prep_time
        m.points            = int(m.cena // 10)

    db.session.add_all([m1, m2, m3])

    # 9) Alergeny
    a1 = Alergen(nazev="Gluten", popis="lepek")
    a2 = Alergen(nazev="Laktóza", popis="mléčný cukr")
    a3 = Alergen(nazev="Ořechy",  popis="všechny ořechy")
    db.session.add_all([a1, a2, a3])

    # 10) Vazby menu–alergeny
    db.session.add_all([
        PolozkaMenuAlergen(menu_polozka=m1, alergen=a1),
        PolozkaMenuAlergen(menu_polozka=m2, alergen=a2),
        PolozkaMenuAlergen(menu_polozka=m3, alergen=a3),
    ])

    # 11) Rezervace
    r1 = Rezervace(
        datum_cas=datetime.now() + timedelta(days=1),
        pocet_osob=2,
        stav_rezervace="potvrzená",
        sleva=0,
        zakaznik=zak1,
        stul=s1
    )
    r2 = Rezervace(
        datum_cas=datetime.now() + timedelta(days=2),
        pocet_osob=4,
        stav_rezervace="čekající",
        sleva=10,
        zakaznik=zak2,
        stul=s2
    )
    r3 = Rezervace(
        datum_cas=datetime.now() + timedelta(days=3),
        pocet_osob=6,
        stav_rezervace="zrušená",
        sleva=0,
        zakaznik=zak3,
        salonek=sal3
    )
    db.session.add_all([r1, r2, r3])

    # 12) Objednávky
    o1 = Objednavka(datum_cas=datetime.now(), stav="otevřená", celkova_castka=398.00, zakaznik=zak1)
    o2 = Objednavka(datum_cas=datetime.now(), stav="zaplacená", celkova_castka=258.00, zakaznik=zak2)
    o3 = Objednavka(datum_cas=datetime.now(), stav="uzavřená", celkova_castka=159.00, zakaznik=zak3)
    db.session.add_all([o1, o2, o3])

    # 13) Položky objednávek
    po1 = PolozkaObjednavky(mnozstvi=2, cena=199.00, objednavka=o1, menu_polozka=m1)
    po2 = PolozkaObjednavky(mnozstvi=1, cena=249.00, objednavka=o2, menu_polozka=m2)
    po3 = PolozkaObjednavky(mnozstvi=1, cena=159.00, objednavka=o3, menu_polozka=m3)
    db.session.add_all([po1, po2, po3])

    # 14) Platby
    pay1 = Platba(castka=398.00, typ_platby="hotově", datum=datetime.now(), objednavka=o1)
    pay2 = Platba(castka=258.00, typ_platby="kartou", datum=datetime.now(), objednavka=o2)
    pay3 = Platba(castka=159.00, typ_platby="bankovní převod", datum=datetime.now(), objednavka=o3)
    db.session.add_all([pay1, pay2, pay3])

    # 15) Hodnocení
    h1 = Hodnoceni(hodnoceni=5, komentar="Vynikající služba!", datum=datetime.now(), objednavka=o1, zakaznik=zak1)
    h2 = Hodnoceni(hodnoceni=4, komentar="Velmi dobré.",      datum=datetime.now(), objednavka=o2, zakaznik=zak2)
    h3 = Hodnoceni(hodnoceni=3, komentar="Ujde.",             datum=datetime.now(), objednavka=o3, zakaznik=zak3)
    db.session.add_all([h1, h2, h3])

    # 16) Jídelní plány
    jp1 = JidelniPlan(nazev="Týdenní nabídka",     platny_od=date.today(),           platny_do=date.today()+timedelta(days=7))
    jp2 = JidelniPlan(nazev="Víkendový speciál",    platny_od=date.today(),           platny_do=date.today()+timedelta(days=2))
    jp3 = JidelniPlan(nazev="Zimní menu",           platny_od=date.today(),           platny_do=date.today()+timedelta(days=30))
    db.session.add_all([jp1, jp2, jp3])

    # 17) Položky jídelních plánů
    jpp1 = PolozkaJidelnihoPlanu(den=date.today(),                         poradi=1, plan=jp1, menu_polozka=m1)
    jpp2 = PolozkaJidelnihoPlanu(den=date.today(),                         poradi=2, plan=jp1, menu_polozka=m2)
    jpp3 = PolozkaJidelnihoPlanu(den=date.today()+timedelta(days=1),      poradi=1, plan=jp2, menu_polozka=m3)
    db.session.add_all([jpp1, jpp2, jpp3])

    # 18) Notifikace
    n1 = Notifikace(typ="email", datum_cas=datetime.now(), text="Vaše rezervace byla potvrzena.", rezervace=r1)
    n2 = Notifikace(typ="sms",   datum_cas=datetime.now(), text="Objednávka přijata a bude připravena.", objednavka=o2)
    n3 = Notifikace(typ="push",  datum_cas=datetime.now(), text="Jídelní plán byl aktualizován.")
    db.session.add_all([n1, n2, n3])

    db.session.commit()
    click.echo("✅ Demo data a role vloženy a všichni uživatelé mají věrnostní účet s 0 body.")


@app.shell_context_processor
def make_shell_context():
    return {
        "db": db,
        "Zakaznik": Zakaznik,
        "VernostniUcet": VernostniUcet,
        "Rezervace": Rezervace,
        "Stul": Stul,
        "Salonek": Salonek,
        "PodnikovaAkce": PodnikovaAkce,
        "Objednavka": Objednavka,
        "PolozkaObjednavky": PolozkaObjednavky,
        "Platba": Platba,
        "Hodnoceni": Hodnoceni,
        "PolozkaMenu": PolozkaMenu,
        "PolozkaMenuAlergen": PolozkaMenuAlergen,
        "JidelniPlan": JidelniPlan,
        "PolozkaJidelnihoPlanu": PolozkaJidelnihoPlanu,
        "Alergen": Alergen,
        "Notifikace": Notifikace,
        "Role": Role
    }


if __name__ == "__main__":
    print(app.url_map)
    app.run(host="0.0.0.0", port=8000, debug=True)
