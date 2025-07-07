# app/seed_menu.py
from app import create_app
from app.db import db
from app.models import PolozkaMenu
from sqlalchemy import text
SEED_DATA = [
    { "nazev": "Sýrová pizza",              "popis": "italská pizza",                                         "cena": 199.00, "obrazek_filename": "pizza.jpg",              "kategorie": "stálá nabídka", "den": "", "preparation_time": 15, "points": 5 },
    { "nazev": "Hovězí burger",             "popis": "burger s hranolkami",                                   "cena": 249.00, "obrazek_filename": "hoveziburger.jpg",       "kategorie": "stálá nabídka", "den": "", "preparation_time": 20, "points": 8 },
    { "nazev": "Caesar salát",              "popis": "čerstvý salát",                                         "cena": 159.00, "obrazek_filename": "caesar.jpg",              "kategorie": "stálá nabídka", "den": "", "preparation_time": 10, "points": 4 },
    { "nazev": "Focaccia",                  "popis": "bryndza, čerstvé klíčky",                               "cena":  99.00, "obrazek_filename": "focaccia.jpg",            "kategorie": "stálá nabídka", "den": "", "preparation_time": 12, "points": 3 },
    { "nazev": "Kulajda",                   "popis": "opékané brambory, zastřené vejce, čerstvý kopr",         "cena": 109.00, "obrazek_filename": "kulajda.jpg",             "kategorie": "stálá nabídka", "den": "", "preparation_time": 18, "points": 6 },
    { "nazev": "Hovězí tatarák",            "popis": "kapary, lanýžové máslo, parmezán, křupavý toast",        "cena": 239.00, "obrazek_filename": "tatarak.jpg",            "kategorie": "stálá nabídka", "den": "", "preparation_time": 5,  "points": 7 },
    { "nazev": "Římský salát",              "popis": "cherry rajčata, gorgonzola, javorový sirup, slanina",   "cena": 199.00, "obrazek_filename": "rimskysalat.jpg",        "kategorie": "stálá nabídka", "den": "", "preparation_time": 10, "points": 4 },
    { "nazev": "Svíčková",                  "popis": "hovězí svíčková, houskový knedlík, brusinky, omáčka",      "cena": 329.00, "obrazek_filename": "svickova.jpg",           "kategorie": "stálá nabídka", "den": "", "preparation_time": 25, "points": 10 },
    { "nazev": "Bramborové noky",           "popis": "pesto, sušená rajčata, parmezán, piniové oříšky",        "cena": 239.00, "obrazek_filename": "bramborovenoky.jpg",    "kategorie": "stálá nabídka", "den": "", "preparation_time": 14, "points": 5 },
    { "nazev": "Vepřová panenka",           "popis": "gratinované brambory, demi-glace, rukola, ředkev",       "cena": 329.00, "obrazek_filename": "panenka.jpg",           "kategorie": "stálá nabídka", "den": "", "preparation_time": 22, "points": 9 },
    { "nazev": "Řízek",                     "popis": "kuřecí řízek v panko strouhance, bramborová kaše",        "cena": 155.00, "obrazek_filename": "rizek.jpg",             "kategorie": "stálá nabídka", "den": "", "preparation_time": 18, "points": 6 },
    { "nazev": "Burger s trhaným vepřovým", "popis": "domácí bulky, trhané vepřové maso, BBQ omáčka, sýr",      "cena": 259.00, "obrazek_filename": "trhanyburger.jpg",      "kategorie": "stálá nabídka", "den": "", "preparation_time": 20, "points": 8 },
    { "nazev": "Buchty jako od babičky",    "popis": "buchtičky s vanilkovým krémem a ovocem",                 "cena": 169.00, "obrazek_filename": "buchty.jpg",            "kategorie": "stálá nabídka", "den": "", "preparation_time": 30, "points": 5 },
    { "nazev": "Paris-Brest",               "popis": "odpalované těsto s pekanovými ořechy a krémem",          "cena": 119.00, "obrazek_filename": "parisbrest.jpg",        "kategorie": "stálá nabídka", "den": "", "preparation_time": 28, "points": 6 },
    { "nazev": "Crème brûlée",              "popis": "vanilkový krém s karamelem",                             "cena":  59.00, "obrazek_filename": "cremebrulee.jpg",       "kategorie": "stálá nabídka", "den": "", "preparation_time": 15, "points": 4 },
    { "nazev": "Craquelin",                 "popis": "větrník se slaným karamelem",                           "cena":  65.00, "obrazek_filename": "craquelin.jpg",         "kategorie": "stálá nabídka", "den": "", "preparation_time": 25, "points": 5 },
    { "nazev": "Bounty cheesecake",         "popis": "čokoládový dort s kokosem a sušenkovým základem",        "cena":  79.00, "obrazek_filename": "bountycheesecake.jpg", "kategorie": "stálá nabídka", "den": "", "preparation_time": 20, "points": 4 },
    { "nazev": "Malinové brownies",         "popis": "kakaové brownies s čerstvými malinami",                 "cena":  75.00, "obrazek_filename": "malinovebrownies.jpg", "kategorie": "stálá nabídka", "den": "", "preparation_time": 20, "points": 4 },
    { "nazev": "Cordon bleu",               "popis": "medová šunka, čedar, smetanová kaše, rajčatový salát",    "cena": 319.00, "obrazek_filename": "cordon.jpg",            "kategorie": "stálá nabídka", "den": "", "preparation_time": 22, "points": 9 },
    { "nazev": "Vepřová žebra",             "popis": "domácí BBQ omáčka, čerstvý křen, sádlová houska",         "cena": 359.00, "obrazek_filename": "zebra.jpg",             "kategorie": "stálá nabídka", "den": "", "preparation_time": 30, "points": 10 },
    { "nazev": "Ball tip steak",            "popis": "pečené brambory, pepřová nebo lanýžová omáčka",           "cena": 429.00, "obrazek_filename": "balltipsteak.jpg",    "kategorie": "stálá nabídka", "den": "", "preparation_time": 25, "points": 9 },
]

def seed_menu():
    app = create_app()
    with app.app_context():
        # smaže polozka_menu + cascade, vynuluje ID
        db.session.execute(text('TRUNCATE TABLE polozka_menu RESTART IDENTITY CASCADE'))
        db.session.commit()

        # znovu vloží všechny položky
        for data in SEED_DATA:
            db.session.add(PolozkaMenu(**data))
        db.session.commit()
        print("Menu úspěšně přenačteno (truncate + insert).")

if __name__ == "__main__":
    seed_menu()