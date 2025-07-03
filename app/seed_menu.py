# seed_menu.py

from app import create_app
from app.db import db
from app.models import PolozkaMenu

SEED_DATA = [
    {"nazev": "Sýrová pizza",              "popis": "italská pizza",                                        "cena": 199.00, "obrazek_url": "/static/images/syrova_pizza.jpg",     "kategorie": "týdenní",   "den": "Pondělí"},
    {"nazev": "Hovězí burger",             "popis": "burger s hranolkami",                                  "cena": 249.00, "obrazek_url": "/static/images/hovezi_burger.jpg",     "kategorie": "týdenní",   "den": "Úterý"},
    {"nazev": "Caesar salát",              "popis": "čerstvý salát",                                        "cena": 159.00, "obrazek_url": "/static/images/caesar_salat.jpg",      "kategorie": "týdenní",   "den": "Středa"},
    {"nazev": "naše focaccia",             "popis": "bryndza, čerstvé klíčky",                              "cena":  99.00, "obrazek_url": "/static/images/nase_focaccia.jpg",     "kategorie": "týdenní",   "den": "Čtvrtek"},
    {"nazev": "Klimoszkovic kulajda",      "popis": "opékané brambory, zastřené vejce, čerstvý kopr",        "cena": 109.00, "obrazek_url": "/static/images/kulajda.jpg",           "kategorie": "týdenní",   "den": "Pátek"},
    {"nazev": "hovězí tatarák",            "popis": "kapary, lanýžové máslo, parmezán, křupavý toast",       "cena": 239.00, "obrazek_url": "/static/images/tatarak.jpg",          "kategorie": "víkendové", "den": "Sobota"},
    {"nazev": "římský salát",              "popis": "cherry rajčata, gorgonzola, javorový sirup, slanina",  "cena": 199.00, "obrazek_url": "/static/images/rimsky_salat.jpg",     "kategorie": "víkendové", "den": "Neděle"},
    {"nazev": "vepřová žebra",             "popis": "domácí BBQ omáčka, čerstvý křen, sádlová houska",        "cena": 359.00, "obrazek_url": "/static/images/veprova_zebra.jpg",    "kategorie": "týdenní",   "den": "Pondělí"},
    {"nazev": "ball tip steak (USA)",      "popis": "pečené brambory, pepřová nebo lanýžová omáčka",          "cena": 429.00, "obrazek_url": "/static/images/ball_tip.jpg",         "kategorie": "týdenní",   "den": "Úterý"},
    {"nazev": "cordon bleu",               "popis": "medová šunka, čedar, smetanová kaše, rajčatový salát",   "cena": 319.00, "obrazek_url": "/static/images/cordon_bleu.jpg",      "kategorie": "týdenní",   "den": "Středa"},
    {"nazev": "svíčková na smetaně",       "popis": "hovězí svíčková, houskový knedlík, brusinky, omáčka",     "cena": 329.00, "obrazek_url": "/static/images/svickova.jpg",         "kategorie": "týdenní",   "den": "Čtvrtek"},
    {"nazev": "bramborové noky",           "popis": "pesto, sušená rajčata, parmezán, piniové oříšky",       "cena": 239.00, "obrazek_url": "/static/images/noky.jpg",            "kategorie": "týdenní",   "den": "Pátek"},
    {"nazev": "vepřová panenka 55",        "popis": "gratinované brambory, demi-glace, rukola, ředkev",      "cena": 329.00, "obrazek_url": "/static/images/panenka.jpg",         "kategorie": "víkendové", "den": "Sobota"},
    {"nazev": "řízek pro prcky",           "popis": "kuřecí řízek v panko strouhance, bramborová kaše",       "cena": 155.00, "obrazek_url": "/static/images/rizek_prcky.jpg",     "kategorie": "víkendové", "den": "Neděle"},
    {"nazev": "burger s trhaným vepřovým", "popis": "domácí bulky, trhané vepřové maso, BBQ omáčka, sýr",     "cena": 259.00, "obrazek_url": "/static/images/burger_trhany.jpg",   "kategorie": "týdenní",   "den": "Pondělí"},
    {"nazev": "buchty jako od babičky",    "popis": "buchtičky s vanilkovým krémem a ovocem",                "cena": 169.00, "obrazek_url": "/static/images/buchty.jpg",          "kategorie": "týdenní",   "den": "Úterý"},
    {"nazev": "paris brest",               "popis": "odpalované těsto s pekanovými ořechy a krémem",         "cena": 119.00, "obrazek_url": "/static/images/paris_brest.jpg",     "kategorie": "týdenní",   "den": "Středa"},
    {"nazev": "crème brûlée",              "popis": "vanilkový krém s karamelem",                            "cena":  59.00, "obrazek_url": "/static/images/creme_brulee.jpg",   "kategorie": "týdenní",   "den": "Čtvrtek"},
    {"nazev": "craquelin",                 "popis": "větrník se slaným karamelem",                          "cena":  65.00, "obrazek_url": "/static/images/craquelin.jpg",       "kategorie": "týdenní",   "den": "Pátek"},
    {"nazev": "bounty cheesecake",         "popis": "čokoládový dort s kokosem a sušenkovým základem",       "cena":  79.00, "obrazek_url": "/static/images/bounty_cheesecake.jpg","kategorie": "víkendové","den":"Sobota"},
    {"nazev": "malinové brownies",         "popis": "kakaové brownies s čerstvými malinami",                "cena":  75.00, "obrazek_url": "/static/images/malinove_brownies.jpg", "kategorie":"víkendové","den":"Neděle"}
]

def seed_menu():
    app = create_app()
    with app.app_context():
        for item in SEED_DATA:
            if not PolozkaMenu.query.filter_by(nazev=item["nazev"]).first():
                db.session.add(PolozkaMenu(**item))
        db.session.commit()
        print("Seed menu položek dokončen.")

if __name__ == "__main__":
    seed_menu()
