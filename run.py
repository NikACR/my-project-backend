import os
import click
from datetime import datetime, date, time, timedelta
from sqlalchemy import text

from app import create_app, db
from app.models import (
    Zakaznik, VernostniUcet, Rezervace, Stul, Salonek,
    PodnikovaAkce, Workshop, Objednavka, PolozkaObjednavky,
    Platba, Hodnoceni, PolozkaMenu, PolozkaMenuAlergen,
    JidelniPlan, PolozkaJidelnihoPlanu, Alergen, Notifikace,
    Role
)

os.environ.setdefault("DATABASE_HOST", "localhost")

config_name = os.getenv("FLASK_CONFIG", "default")
app = create_app(config_name)

# složka pro ukládání obrázků
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'images')


def _vycistit_databazi():
    db.session.query(PolozkaMenuAlergen).delete()
    db.session.query(Notifikace).delete()
    db.session.query(Hodnoceni).delete()
    db.session.query(Platba).delete()
    db.session.query(PolozkaObjednavky).delete()
    db.session.query(Objednavka).delete()
    db.session.query(Workshop).delete()
    db.session.query(PodnikovaAkce).delete()
    db.session.query(Rezervace).delete()
    db.session.query(PolozkaJidelnihoPlanu).delete()
    db.session.query(JidelniPlan).delete()
    db.session.query(Alergen).delete()
    db.session.query(PolozkaMenu).delete()
    db.session.query(Salonek).delete()
    db.session.query(Stul).delete()
    db.session.query(VernostniUcet).delete()
    # smažeme vazby user_roles, aby při mazání zákazníků nevznikl FK konflikt
    db.session.execute(text('DELETE FROM user_roles'))
    db.session.query(Zakaznik).delete()
    db.session.query(Role).delete()
    db.session.commit()


@app.cli.command("seed-db")
def seed_db():
    _vycistit_databazi()

    # 0) Role
    admin_role = Role(name="admin",  description="Správce systému")
    staff_role = Role(name="staff",  description="Obsluha")
    user_role = Role(name="user",   description="Koncový zákazník")
    db.session.add_all([admin_role, staff_role, user_role])
    db.session.flush()

    # 1) Zákazníci (role=user)
    zak1 = Zakaznik(jmeno="Petr",    prijmeni="Svoboda",
                    email="petr.svoboda@example.cz", telefon="603123456")
    zak1.password = "tajneheslo1"
    zak1.roles.append(user_role)
    zak2 = Zakaznik(jmeno="Eva",     prijmeni="Novotná",
                    email="eva.novotna@example.cz",  telefon="608987654")
    zak2.password = "tajneheslo2"
    zak2.roles.append(user_role)
    zak3 = Zakaznik(jmeno="Lukáš",   prijmeni="Krejčík",
                    email="lukas.krejcik@example.cz", telefon="602555333")
    zak3.password = "tajneheslo3"
    zak3.roles.append(user_role)

    # 2) Staff účty
    staff1 = Zakaznik(jmeno="Anna",    prijmeni="Nováková",
                      email="anna.staff@example.com", telefon="600111222")
    staff1.password = "heslo123"
    staff1.roles.append(staff_role)
    staff2 = Zakaznik(jmeno="Petr",    prijmeni="Pracník",
                      email="petr.staff@example.com", telefon="600333444")
    staff2.password = "heslo123"
    staff2.roles.append(staff_role)
    staff3 = Zakaznik(jmeno="Eva",     prijmeni="Zaměstnaná",
                      email="eva.staff@example.com",  telefon="600555666")
    staff3.password = "heslo123"
    staff3.roles.append(staff_role)

    # 3) Volitelný admin
    admin = Zakaznik(jmeno="Admin",    prijmeni="Root",
                     email="admin@example.com",       telefon=None)
    admin.password = "rootpass"
    admin.roles.append(admin_role)

    db.session.add_all([zak1, zak2, zak3, staff1, staff2, staff3, admin])
    db.session.commit()

    # 4) Věrnostní účty – všichni začínají na 0 bodech
    for zak in Zakaznik.query.all():
        db.session.add(VernostniUcet(
            body=0, datum_zalozeni=date.today(), zakaznik=zak))
    db.session.commit()

    # 5) Stoly
    s1 = Stul(cislo=1, kapacita=4, popis="U okna")
    s2 = Stul(cislo=2, kapacita=2, popis="U stěny")
    s3 = Stul(cislo=3, kapacita=6, popis="Rodinný stůl")
    db.session.add_all([s1, s2, s3])

    # 6) Salónky
    sal1 = Salonek(
        nazev="Salónek A", kapacita=12,
        popis="Malý útulný salónek", obrazek_filename="salon1.jpg"
    )
    sal2 = Salonek(
        nazev="Salónek B", kapacita=20,
        popis="Prostorný salónek",       obrazek_filename="salon2.jpg"
    )
    sal3 = Salonek(
        nazev="Salónek Hvězda", kapacita=30,
        popis="Velký salónek pro akce",  obrazek_filename="salon3.jpg"
    )
    db.session.add_all([sal1, sal2, sal3])

    # 7) Podnikové akce
    ak1 = PodnikovaAkce(
        nazev="Networkingová večeře",
        popis="Setkání pro profesionály",
        cena=4500.00,
        kapacita=50,
        datum=date.today() + timedelta(days=5),
        cas=time(18, 0),
        salonek=sal1,
        obrazek_filename="byznysschuzka.jpg"
    )
    ak2 = PodnikovaAkce(
        nazev="Teambuilding v přírodě",
        popis="Outdoorové aktivity",
        cena=12000.00,
        kapacita=100,
        datum=date.today() + timedelta(days=10),
        cas=time(10, 0),
        salonek=sal2,
        obrazek_filename="teambuildinglesy.jpg"
    )
    ak3 = PodnikovaAkce(
        nazev="Vánoční večírek",
        popis="Slavnostní stolování",
        cena=7000.00,
        kapacita=80,
        datum=date.today() + timedelta(days=15),
        cas=time(19, 0),
        salonek=sal3,
        obrazek_filename="vanocnivecirek.jpg"
    )
    db.session.add_all([ak1, ak2, ak3])

    # 8) Workshopy
    ws1 = Workshop(
        nazev="Kurz domácího pečení chleba",
        popis="Naučíme se péct tradiční kváskový chléb.",
        cena=1200.00, kapacita=10,
        cas_konani=datetime.now() + timedelta(days=7, hours=10),
        obrazek_filename="pecenichleba.jpg"
    )
    ws2 = Workshop(
        nazev="Mixologie a koktejly",
        popis="Umění míchání koktejlů.",
        cena=800.00, kapacita=12,
        cas_konani=datetime.now() + timedelta(days=8, hours=18),
        obrazek_filename="koktejly.jpg"
    )
    ws3 = Workshop(
        nazev="Kurz základů fotografování",
        popis="Naučte se ovládnout fotoaparát.",
        cena=1500.00, kapacita=8,
        cas_konani=datetime.now() + timedelta(days=9, hours=14),
        obrazek_filename="fotografovani.jpg"
    )
    ws4 = Workshop(
        nazev="Základy baristického umění",
        popis="Tvorba espressa a latte art.",
        cena=900.00, kapacita=10,
        cas_konani=datetime.now() + timedelta(days=10, hours=9),
        obrazek_filename="barista.jpg"
    )
    db.session.add_all([ws1, ws2, ws3, ws4])

    # 9) Položky menu
    m1 = PolozkaMenu(nazev="Sýrová pizza", obrazek_filename="pizza.jpg",
                     popis="Italská pizza",       cena=199.00)
    m2 = PolozkaMenu(nazev="Hovězí burger", obrazek_filename="hoveziburger.jpg",
                     popis="Burger s hranolkami", cena=249.00)
    m3 = PolozkaMenu(nazev="Caesar salát", obrazek_filename="caesar.jpg",
                     popis="Čerstvý salát",        cena=159.00)
    dnes_jmeno = datetime.now().strftime("%A")
    default_prep_time = 15
    for m in (m1, m2, m3):
        m.kategorie = "týdenní"
        m.den = dnes_jmeno
        m.preparation_time = default_prep_time
        m.points = int(m.cena // 10)
    db.session.add_all([m1, m2, m3])

    # 10) Alergeny
    a1 = Alergen(nazev="Gluten", popis="Lepek")
    a2 = Alergen(nazev="Laktóza", popis="Mléčný cukr")
    a3 = Alergen(nazev="Ořechy",  popis="Všechny ořechy")
    db.session.add_all([a1, a2, a3])

    # 11) Vazby menu–alergeny
    db.session.add_all([
        PolozkaMenuAlergen(menu_polozka=m1, alergen=a1),
        PolozkaMenuAlergen(menu_polozka=m2, alergen=a2),
        PolozkaMenuAlergen(menu_polozka=m3, alergen=a3),
    ])

    # 12) Rezervace
    r1 = Rezervace(
        datum_cas=datetime.now() + timedelta(days=1),
        pocet_osob=2, stav_rezervace="potvrzená",
        sleva=0, zakaznik=zak1, stul=s1
    )
    r2 = Rezervace(
        datum_cas=datetime.now() + timedelta(days=2),
        pocet_osob=4, stav_rezervace="čekající",
        sleva=10, zakaznik=zak2, stul=s2
    )
    r3 = Rezervace(
        datum_cas=datetime.now() + timedelta(days=3),
        pocet_osob=6, stav_rezervace="zrušená",
        sleva=0, zakaznik=zak3, salonek=sal3
    )
    db.session.add_all([r1, r2, r3])

    # 13) Objednávky
    o1 = Objednavka(datum_cas=datetime.now(), stav="otevřená",
                    celkova_castka=398.00, zakaznik=zak1)
    o2 = Objednavka(datum_cas=datetime.now(), stav="zaplacená",
                    celkova_castka=258.00, zakaznik=zak2)
    o3 = Objednavka(datum_cas=datetime.now(), stav="uzavřená",
                    celkova_castka=159.00, zakaznik=zak3)
    db.session.add_all([o1, o2, o3])

    # 14) Položky objednávek
    po1 = PolozkaObjednavky(mnozstvi=2, cena=199.00,
                            objednavka=o1, menu_polozka=m1)
    po2 = PolozkaObjednavky(mnozstvi=1, cena=249.00,
                            objednavka=o2, menu_polozka=m2)
    po3 = PolozkaObjednavky(mnozstvi=1, cena=159.00,
                            objednavka=o3, menu_polozka=m3)
    db.session.add_all([po1, po2, po3])

    # 15) Platby
    pay1 = Platba(castka=398.00, typ_platby="hotově",
                  datum=datetime.now(), objednavka=o1)
    pay2 = Platba(castka=258.00, typ_platby="kartou",
                  datum=datetime.now(), objednavka=o2)
    pay3 = Platba(castka=159.00, typ_platby="bankovní převod",
                  datum=datetime.now(), objednavka=o3)
    db.session.add_all([pay1, pay2, pay3])

    # 16) Hodnocení
    h1 = Hodnoceni(hodnoceni=5, komentar="Vynikající služba!",
                   datum=datetime.now(), objednavka=o1, zakaznik=zak1)
    h2 = Hodnoceni(hodnoceni=4, komentar="Velmi dobré.",
                   datum=datetime.now(), objednavka=o2, zakaznik=zak2)
    h3 = Hodnoceni(hodnoceni=3, komentar="Ujde.",
                   datum=datetime.now(), objednavka=o3, zakaznik=zak3)
    db.session.add_all([h1, h2, h3])

    # 17) Jídelní plány
    jp1 = JidelniPlan(nazev="Týdenní nabídka",  platny_od=date.today(
    ),          platny_do=date.today()+timedelta(days=7))
    jp2 = JidelniPlan(nazev="Víkendový speciál", platny_od=date.today(
    ),          platny_do=date.today()+timedelta(days=2))
    jp3 = JidelniPlan(nazev="Zimní menu",        platny_od=date.today(
    ),          platny_do=date.today()+timedelta(days=30))
    db.session.add_all([jp1, jp2, jp3])

    # 18) Položky jídelních plánů
    jpp1 = PolozkaJidelnihoPlanu(den=date.today(),
                                 poradi=1, plan=jp1, menu_polozka=m1)
    jpp2 = PolozkaJidelnihoPlanu(den=date.today(),
                                 poradi=2, plan=jp1, menu_polozka=m2)
    jpp3 = PolozkaJidelnihoPlanu(
        den=date.today()+timedelta(days=1), poradi=1, plan=jp2, menu_polozka=m3)
    db.session.add_all([jpp1, jpp2, jpp3])

    # 19) Notifikace (teď s id_zakaznika)
    n1 = Notifikace(
        typ="email",
        datum_cas=datetime.now(),
        text="Vaše rezervace byla potvrzena.",
        rezervace=r1,
        id_zakaznika=zak1.id_zakaznika
    )
    n2 = Notifikace(
        typ="sms",
        datum_cas=datetime.now(),
        text="Objednávka přijata a bude připravena.",
        objednavka=o2,
        id_zakaznika=zak2.id_zakaznika
    )
    n3 = Notifikace(
        typ="push",
        datum_cas=datetime.now(),
        text="Nový jídelní plán je k dispozici.",
        id_zakaznika=zak1.id_zakaznika
    )
    db.session.add_all([n1, n2, n3])

    db.session.commit()
    click.echo(
        "✅ Demo data vloženy, včetně obrázků pro workshopy, akce a salonky a opravených notifikací.")


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
        "Workshop": Workshop,
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
