"""
Tenantify AI — NLU Comment Moderation & Classification Engine
Modul text processing berbasis Natural Language Understanding (NLU) untuk:
1. Mendeteksi dan memoderasi komentar kasar/aneh-aneh (Auto-removed).
2. Mengklasifikasi komentar toko/penjual ke dalam 3 parameter:
   - Kritik & Saran Positif (Terkirim ke dashboard)
   - Kritik & Saran Negatif (Terkirim ke dashboard)
   - Comment aneh-aneh (komentar yang berbahasa kasar) (Otomatis di-remove)
3. Ekstraksi aspek feedback (Rasa, Porsi, Pelayanan, Kemasan, Harga, Waktu).
"""

import re
import html
import unicodedata
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum


class CommentCategory(str, Enum):
    POSITIF = "Kritik & Saran Positif"
    ANEH_KASAR = "Comment aneh-aneh (komentar yang berbahasa kasar)"
    NEGATIF = "Kritik & Saran Negatif"


class ModerationAction(str, Enum):
    DELIVERED_TO_DASHBOARD = "DELIVERED_TO_DASHBOARD"
    AUTO_REMOVED = "AUTO_REMOVED"


class SentimentType(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    TOXIC = "TOXIC"


# ── Kamus Singkatan & Slang Bahasa Indonesia & English ───────────────
# 1. Kamus Slang & Singkatan Gaul (Bahasa Indonesia & English)
SLANG_MAP = {
    # ── Negasi & Penolakan (Indonesian & English) ─────────────────────
    "ga": "tidak", "gak": "tidak", "gk": "tidak", "g": "tidak", "kaga": "tidak",
    "kagak": "tidak", "tdk": "tidak", "ngga": "tidak", "nggak": "tidak", "nda": "tidak",
    "ndak": "tidak", "ora": "tidak", "ogah": "tidak", "enggak": "tidak", "engga": "tidak",
    "tak": "tidak", "bkn": "bukan", "gajadi": "tidak jadi", "gabisa": "tidak bisa",
    "gbs": "tidak bisa", "gamau": "tidak mau", "gkmau": "tidak mau", "gapapa": "tidak apa-apa",
    "gatau": "tidak tahu", "gktau": "tidak tahu",
    "dont": "tidak", "don't": "tidak", "doesnt": "tidak", "doesn't": "tidak",
    "didnt": "tidak", "didn't": "tidak", "wont": "tidak", "won't": "tidak",
    "cant": "tidak bisa", "can't": "tidak bisa", "isnt": "tidak", "isn't": "tidak",
    "arent": "tidak", "aren't": "tidak",

    # ── Keterangan Derajat / Penguat / Intensifier (Indonesian & English)
    "bgt": "banget", "bgtss": "banget", "bgtt": "banget", "bngtt": "banget", "bnget": "banget",
    "bgtz": "banget", "buanget": "banget", "bingits": "banget", "beut": "banget",
    "beneran": "sungguh", "bener2": "sungguh", "tenan": "sungguh",
    "skali": "sekali", "skl": "sekali", "amat": "sangat", "sangatt": "sangat",
    "parah": "parah", "parahh": "parah", "pisan": "sekali", "pol": "banget", "poll": "banget",
    "rly": "really", "sooo": "so", "supeer": "super",

    # ── Pronomina & Sapaan Pelanggan/Penjual (Indonesian & English) ───
    "sy": "saya", "aq": "saya", "aku": "saya", "ak": "saya", "gw": "saya", "gue": "saya",
    "gua": "saya", "gwa": "saya", "gwe": "saya", "w": "saya", "kmi": "kami",
    "lu": "kamu", "lo": "kamu", "loe": "kamu", "lw": "kamu", "ente": "kamu",
    "km": "kamu", "kmu": "kamu", "sampeyan": "kamu", "u": "kamu", "ur": "kamu",
    "min": "admin", "mimin": "admin", "adm": "admin", "seller": "penjual", "seler": "penjual",
    "kak": "kakak", "kaka": "kakak", "sis": "kakak", "sist": "kakak", "sista": "kakak",
    "gan": "agan", "bro": "abang", "bang": "abang", "om": "paman",

    # ── Kata Hubung, Partikel & Preposisi (Indonesian & English) ──────
    "tp": "tapi", "tpi": "tapi", "ttpi": "tapi", "ttp": "tetap", "tetep": "tetap",
    "dgn": "dengan", "dg": "dengan",
    "utk": "untuk", "untk": "untuk", "bwt": "buat",
    "dr": "dari", "dri": "dari",
    "krn": "karena", "krena": "karena", "karna": "karena", "krna": "karena", "coz": "karena",
    "cuz": "karena", "bcoz": "karena",
    "jd": "jadi", "jdi": "jadi",
    "kalo": "kalau", "kl": "kalau", "klo": "kalau", "klu": "kalau",
    "trs": "terus", "trus": "terus", "truss": "terus",
    "sm": "sama", "sma": "sama",
    "dlm": "dalam",
    "sblm": "sebelum", "sebelom": "sebelum", "b4": "sebelum",
    "stlh": "setelah", "ssdh": "sesudah",
    "bs": "bisa", "bsa": "bisa",
    "jg": "juga", "jga": "juga",
    "aja": "saja", "aj": "saja", "ajh": "saja", "doang": "saja", "thok": "saja",
    "dong": "dong", "donk": "dong", "dunk": "dong",
    "nih": "ini", "ni": "ini", "nie": "ini",
    "tuh": "itu", "tu": "itu",
    "udh": "sudah", "uda": "sudah", "udah": "sudah", "sdh": "sudah", "sudh": "sudah",
    "blm": "belum", "blom": "belum", "bleum": "belum",
    "lg": "lagi", "lgi": "lagi",
    "emg": "memang", "emang": "memang",
    "knp": "kenapa", "knapa": "kenapa", "kenapah": "kenapa",
    "gmn": "bagaimana", "gmana": "bagaimana", "gimana": "bagaimana",
    "gtu": "begitu", "gitu": "begitu",
    "gni": "begini", "gini": "begini",
    "trnyata": "ternyata", "ternyta": "ternyata", "taunya": "ternyata",
    "tbh": "honestly", "idk": "tidak tahu", "imo": "in my opinion", "imho": "in my opinion",
    "fyi": "fyi", "asap": "asap", "thru": "through",

    # ── Makanan, Rasa & Kualitas ──────────────────────────────────────
    "bgs": "bagus", "bgus": "bagus", "mantul": "mantap", "mantep": "mantap",
    "mantapp": "mantap", "mantabb": "mantap", "top": "mantap", "jos": "mantap",
    "josss": "mantap", "maknyus": "mantap", "ciamik": "mantap", "apik": "bagus",
    "delish": "delicious", "yumm": "yummy", "fav": "favorite", "fave": "favorite",
    "krg": "kurang", "kurg": "kurang", "kurng": "kurang",
    "bnyk": "banyak", "byk": "banyak", "bejibun": "banyak",
    "dikit": "sedikit", "sdkt": "sedikit", "dkit": "sedikit", "seiprit": "sedikit",
    "mkn": "makan", "mknn": "makanan", "makann": "makanan",
    "minum": "minuman", "mnm": "minuman", "mnmn": "minuman",
    "hrg": "harga", "mrh": "murah", "murmer": "murah", "murce": "murah",
    "mhl": "mahal", "mehong": "mahal",
    "asin": "asin", "keasinan": "asin", "hambar": "hambar", "anyep": "hambar", "cemplang": "hambar",
    "basi": "basi", "basii": "basi", "mambu": "basi",
    "bau": "bau", "apek": "bau", "amis": "bau", "tengik": "bau",
    "mentah": "mentah", "mengkal": "mentah",
    "gosong": "gosong", "hangus": "gosong", "tutong": "gosong",
    "pds": "pedas", "pedes": "pedas", "kepedesan": "pedas",
    "pait": "pahit", "kepaitan": "pahit",
    "kemanisan": "manis",
    "alot": "keras", "liat": "keras", "kras": "keras",
    "dingin": "dingin", "adem": "dingin",
    "anget": "hangat",
    "renyah": "renyah", "crispy": "renyah", "krispi": "renyah", "kriuk": "renyah",
    "seger": "segar", "fresh": "segar",

    # ── Kemasan, Fisik & Kebersihan ───────────────────────────────────
    "packing": "kemasan", "packaging": "kemasan", "bungkus": "kemasan", "bungkusnya": "kemasan",
    "packingan": "kemasan", "wadah": "kemasan", "pic": "picture",
    "ancur": "hancur", "remuk": "hancur", "penyok": "hancur", "peyot": "hancur",
    "tumpah": "tumpah", "bleber": "tumpah", "bocor": "bocor", "rembes": "bocor",
    "robek": "robek", "sobek": "robek",
    "kotor": "kotor", "jorok": "kotor", "kumel": "kotor",
    "rapi": "rapi", "rapih": "rapi", "rapet": "rapi",
    "higienis": "bersih", "resik": "bersih",

    # ── Pelayanan, Waktu & Sikap ──────────────────────────────────────
    "ramah": "ramah", "baek": "ramah", "helpful": "ramah",
    "judes": "judes", "jutek": "judes", "jutex": "judes", "galak": "galak", "cuek": "cuek", "ketus": "judes",
    "cepet": "cepat", "cpt": "cepat", "fast": "cepat", "kenceng": "cepat", "gesit": "cepat", "satset": "cepat",
    "lama": "lambat", "lemot": "lambat", "lelet": "lambat", "llet": "lambat", "ngaret": "lambat",
    "gercep": "responsif", "tanggap": "responsif",
    "dibalas": "dibalas", "dibales": "dibalas", "direply": "dibalas", "direspon": "dibalas",
    "diabaiin": "diabaikan", "dicuekin": "diabaikan", "dikacangin": "diabaikan",

    # ── Pesanan & Logistik ────────────────────────────────────────────
    "pesen": "pesan", "pesenan": "pesanan", "orderan": "pesanan", "ordran": "pesanan", "order": "pesanan",
    "ongkir": "ongkir", "ongkos": "ongkir",
    "kirim": "pengiriman", "kiriman": "pengiriman", "antar": "pengiriman", "delivery": "pengiriman",
    "nyampe": "sampai", "sampe": "sampai",
    "kurir": "kurir", "ojol": "kurir", "driver": "kurir",

    # ── Ulasan, Kepuasan & Saran ──────────────────────────────────────
    "recomended": "rekomendasi", "rekomen": "rekomendasi", "recom": "rekomendasi", "recommended": "rekomendasi",
    "worth": "layak", "worthit": "layak", "worthed": "layak",
    "nyesel": "menyesal", "kecewa": "kecewa", "kapok": "kapok", "zonk": "zonk", "rugi": "rugi",
    "nipu": "menipu", "boong": "bohong",
    "bikin": "membuat", "bkin": "membuat",
    "tlg": "tolong", "pls": "tolong", "plz": "tolong", "pliss": "tolong", "tlng": "tolong", "mohon": "tolong",
    "mks": "terima kasih", "makasi": "terima kasih", "makasih": "terima kasih",
    "tq": "terima kasih", "thx": "terima kasih", "thanks": "terima kasih", "ty": "terima kasih",
    "next": "selanjutnya", "kedepan": "kedepannya", "kdepan": "kedepannya", "kedepannya": "kedepannya",
    "adain": "sediakan", "sediain": "sediakan",
    "tambahin": "ditambah", "benerin": "perbaiki", "perbaiki": "perbaiki",
    "estetik": "estetik", "aesthetic": "estetik"
}

# 2. Kamus Kata Kasar & Makian (Indonesian & English Toxic Lexicon)
ABUSIVE_WORDS = {
    # Hewan sebagai makian
    "anjing", "anj1ng", "anjink", "anying", "anjeng", "ajg", "asw", "asu", "asuu",
    "babi", "b4b1", "bb1", "monyet", "kunyuk", "bajing", "celeng",
    "anjir", "bjir", "njir", "njirs", "njirr",

    # Makian kasar, umpatan & caci maki daerah
    "bangsat", "b@ngs@t", "b4ngs4t", "bajingan", "b4j1ng4n", "kampret", "brengsek", "keparat",
    "jancuk", "jancok", "dancok", "dancuk", "cok", "cuk", "ancuk", "ancok",
    "pantek", "pantak", "puki", "pukimak", "pukima", "kimak", "bodat", "bedebah",
    "bangke", "bangkai", "tai", "taek", "tae", "taik", "setan", "iblis", "dajjal", "bejat",
    "sialan", "biadab", "laknat", "mampus", "modar", "modyar", "mati aja", "matio",

    # Organ reproduksi & seksual kasar (ID & EN)
    "kontol", "k0nt0l", "kntil", "kntl", "kontl", "kntol",
    "memek", "mmk", "m3m3k", "jembut", "jmbt",
    "peler", "paler", "pelir", "itil", "titit", "tetek", "toket", "pepek", "tempik",
    "ngentot", "ngentod", "gentot", "ngewe", "ewe", "crot", "sange", "sangean",
    "lonte", "lont3", "pelacur", "jablay", "jabl4y", "perek", "sundal", "pecun", "bispak",
    "bencong", "banci", "dick", "pussy", "cock", "cocksucker", "prick", "twat", "wanker",

    # Cacian mental/intelektual kasar (ID & EN)
    "goblok", "g0bl0k", "gblk", "goblog", "goblokk", "tolol", "t0l0l", "tll", "bego", "bgok", "begok",
    "idiot", "pekok", "pekokk", "autis", "dungu", "otak udang", "bloon", "oon", "geblek", "koplak",
    "moron", "stupid", "retard", "retarded", "dumbass", "dipshit", "jackass",

    # Bahasa Inggris kasar, vulgar & umpatan
    "hell", "fuck", "fucking", "fucker", "fck", "motherfucker", "bitch", "bitches", "b!tch",
    "asshole", "bastard", "shit", "bullshit", "cunt", "slut", "whore", "douchebag", "scumbag",
    "stfu", "wtf"
}

# 3. Pola Regex untuk Makian Bertanda Bintang / Sensor Simbol (Indonesian & English)
MASKED_ABUSIVE_PATTERNS = [
    # bajingan & variasinya
    r'(?<!\w)b+a*j+[a-z]*[\*\@\#\$\%\&\!\~\-\_]+[a-z]*(?!\w)',
    r'(?<!\w)b+[\*\@\#\$\%\&\!\~\-\_]+j+i*n*g*a*n*(?!\w)',
    # anjing & variasinya
    r'(?<!\w)a+n*j*[\*\@\#\$\%\&\!\~\-\_]+[a-z]*(?!\w)',
    r'(?<!\w)a+[\*\@\#\$\%\&\!\~\-\_]+n*j+[a-z]*(?!\w)',
    # babi & variasinya
    r'(?<!\w)b+[\*\@\#\$\%\&\!\~\-\_]+[i|1]+(?!\w)',
    r'(?<!\w)b+[\*\@\#\$\%\&\!\~\-\_]+b+[i|1|\*]+(?!\w)',
    r'(?<!\w)b+a+[\*\@\#\$\%\&\!\~\-\_]+[i|1|\*]*(?!\w)',
    r'(?<!\w)b+[\*\@\#\$\%\&\!\~\-\_]{3,}(?!\w)',
    # kontol & variasinya
    r'(?<!\w)k+[\*\@\#\$\%\&\!\~\-\_]+n+t+[a-z\*\@\#\$\%\&\!\~\-\_]*(?!\w)',
    r'(?<!\w)k+[\*\@\#\$\%\&\!\~\-\_]{2,}l+(?!\w)',
    r'(?<!\w)k+o+n+[\*\@\#\$\%\&\!\~\-\_]+[a-z]*(?!\w)',
    r'(?<!\w)k+o*n*t+[\*\@\#\$\%\&\!\~\-\_]+l*(?!\w)',
    # goblok & variasinya
    r'(?<!\w)g+[\*\@\#\$\%\&\!\~\-\_]+b+l+[a-z\*\@\#\$\%\&\!\~\-\_]*(?!\w)',
    r'(?<!\w)g+[\*\@\#\$\%\&\!\~\-\_]{2,}k+(?!\w)',
    r'(?<!\w)g+o+b+[\*\@\#\$\%\&\!\~\-\_]+[a-z]*(?!\w)',
    r'(?<!\w)g+o*b*l+[\*\@\#\$\%\&\!\~\-\_]+k*(?!\w)',
    # bangsat & variasinya
    r'(?<!\w)b+[\*\@\#\$\%\&\!\~\-\_]+n+g+s+[a-z\*\@\#\$\%\&\!\~\-\_]*(?!\w)',
    r'(?<!\w)b+a+n+g+[\*\@\#\$\%\&\!\~\-\_]+[a-z]*(?!\w)',
    r'(?<!\w)b+a*n*g*s+[\*\@\#\$\%\&\!\~\-\_]+t*(?!\w)',
    # memek & variasinya
    r'(?<!\w)m+[\*\@\#\$\%\&\!\~\-\_]+m+[a-z\*\@\#\$\%\&\!\~\-\_]*(?!\w)',
    r'(?<!\w)m+e+[\*\@\#\$\%\&\!\~\-\_]+k+(?!\w)',
    # tolol & variasinya
    r'(?<!\w)t+[\*\@\#\$\%\&\!\~\-\_]+l+[a-z\*\@\#\$\%\&\!\~\-\_]*(?!\w)',
    r'(?<!\w)t+o+[\*\@\#\$\%\&\!\~\-\_]+l+(?!\w)',
    # jancuk/jancok & variasinya
    r'(?<!\w)j+a*n*c+[\*\@\#\$\%\&\!\~\-\_]+[a-z]*(?!\w)',
    r'(?<!\w)j+a+n+[\*\@\#\$\%\&\!\~\-\_]+[a-z]*(?!\w)',
    r'(?<!\w)j+[\*\@\#\$\%\&\!\~\-\_]+n+c+[a-z\*\@\#\$\%\&\!\~\-\_]*(?!\w)',
    # pantek & variasinya
    r'(?<!\w)p+a*n*t+[\*\@\#\$\%\&\!\~\-\_]+[a-z]*(?!\w)',
    r'(?<!\w)p+[\*\@\#\$\%\&\!\~\-\_]+n+t+[a-z\*\@\#\$\%\&\!\~\-\_]*(?!\w)',
    # kampret & variasinya
    r'(?<!\w)k+a*m*p+[\*\@\#\$\%\&\!\~\-\_]+[a-z]*(?!\w)',
    r'(?<!\w)k+[\*\@\#\$\%\&\!\~\-\_]+m+p+r+[a-z\*\@\#\$\%\&\!\~\-\_]*(?!\w)',
    # peler, jembut, lonte
    r'(?<!\w)p+[\*\@\#\$\%\&\!\~\-\_]+l+e*r+(?!\w)',
    r'(?<!\w)j+[\*\@\#\$\%\&\!\~\-\_]+m+b+u*t+(?!\w)',
    r'(?<!\w)l+[\*\@\#\$\%\&\!\~\-\_]+n+t+e*(?!\w)',
    # Bahasa Inggris bertanda sensor (fuck, bitch, shit, asshole, dick, etc)
    r'(?<!\w)f+[\*\@\#\$\%\&\!\~\-\_]+c*k+[a-z]*(?!\w)',
    r'(?<!\w)f+u+[\*\@\#\$\%\&\!\~\-\_]+k+(?!\w)',
    r'(?<!\w)f+[\*\@\#\$\%\&\!\~\-\_]{2,}(?!\w)',
    r'(?<!\w)b+[\*\@\#\$\%\&\!\~\-\_]+t*c*h+[a-z]*(?!\w)',
    r'(?<!\w)b+i+[\*\@\#\$\%\&\!\~\-\_]+h+(?!\w)',
    r'(?<!\w)s+h+[\*\@\#\$\%\&\!\~\-\_]+t+(?!\w)',
    r'(?<!\w)s+[\*\@\#\$\%\&\!\~\-\_]+i+t+(?!\w)',
    r'(?<!\w)a+[\*\@\#\$\%\&\!\~\-\_]+s+h+o*l*e*(?!\w)',
    r'(?<!\w)a+s+s+[\*\@\#\$\%\&\!\~\-\_]+[a-z]*(?!\w)',
    r'(?<!\w)d+[\*\@\#\$\%\&\!\~\-\_]+c*k+(?!\w)',
    r'(?<!\w)p+[\*\@\#\$\%\&\!\~\-\_]+s+s+y+(?!\w)',
    r'(?<!\w)c+[\*\@\#\$\%\&\!\~\-\_]+n*t+(?!\w)',
]

# 4. Kamus Aspek Review untuk Analisis Dashboard Toko (Bilingual: ID & EN)
ASPECT_KEYWORDS = {
    "Rasa & Kualitas": [
        # Bahasa Indonesia
        "rasa", "rasanya", "cita rasa", "tekstur", "bumbu", "bumbunya", "enak", "enak banget",
        "mantap", "lezat", "sedap", "nagih", "nikmat", "maknyus", "asin", "keasinan", "hambar",
        "cemplang", "anyep", "manis", "kemanisan", "pahit", "pait", "kepaitan", "pedas", "pedes",
        "kepedesan", "gurih", "gurihnya", "micin", "basi", "mambu", "bau", "amis", "tengik",
        "apek", "bacin", "mentah", "mengkal", "gosong", "hangus", "tutong", "dingin", "anget",
        "hangat", "panas", "renyah", "crispy", "krispi", "garing", "kriuk", "alot", "keras",
        "lembut", "empuk", "juicy", "segar", "fresh", "matang", "mateng", "aromanya", "wangi",
        "harum", "oily", "berminyak", "enek", "eneg", "creamy", "pekat", "encer", "kopi", "teh",
        # English
        "taste", "tasted", "flavor", "flavour", "flavorful", "delicious", "tasty", "yummy", "delish",
        "savory", "savoury", "salty", "oversalted", "bland", "tasteless", "sweet", "bitter", "spicy",
        "sour", "spoiled", "rotten", "stale", "smelly", "stinky", "raw", "undercooked", "burnt",
        "burned", "overcooked", "cold", "warm", "hot", "crunchy", "tough", "tender",
        "cooked", "seasoning", "greasy", "coffee", "tea", "drink", "drinks", "beverage",
        "aroma", "aromas", "scent", "food", "dish", "meal", "chicken", "beef"
    ],
    "Porsi & Takaran": [
        # Bahasa Indonesia
        "porsi", "porsinya", "takaran", "dikit", "sedikit", "pelit", "banyak", "melimpah",
        "kenyang", "pas", "jumbo", "mini", "ukuran", "ukurannya", "size", "potongan", "irisan",
        "isi", "isinya", "topping", "toping", "nasi", "lauk", "daging", "sayur", "tebel",
        "tebal", "tipis", "lebar", "seiprit", "nanggung", "cukup",
        # English
        "portion", "portions", "amount", "quantity", "serving", "huge", "big", "large", "small",
        "tiny", "little", "filling", "stuffed", "slice", "slices", "piece", "pieces", "meat",
        "rice", "thick", "thin"
    ],
    "Kemasan & Kebersihan": [
        # Bahasa Indonesia
        "kemasan", "packing", "packaging", "packingan", "bungkus", "bungkusnya", "wadah", "kotak",
        "box", "cup", "gelas", "plastik", "paper bag", "paperbag", "kantong", "tutup", "seal",
        "sealer", "bubble wrap", "tumpah", "bocor", "rembes", "robek", "sobek", "hancur", "ancur",
        "remuk", "penyok", "peyot", "rapi", "rapih", "rapet", "aman", "safety", "higienis",
        "hygienic", "bersih", "kotor", "debu", "lalat", "rambut", "kecoak", "jorok", "resik",
        "steril", "sendok", "garpu", "sedotan", "tisu", "tissue",
        # English
        "package", "pack", "container", "spilled", "spilt", "leak", "leaking", "leaked", "torn",
        "crushed", "damaged", "neat", "tidy", "secure", "clean", "cleanliness", "hygiene",
        "dirty", "filthy", "dust", "hair", "cockroach", "spoon", "fork", "straw", "napkin"
    ],
    "Pelayanan & Tenant": [
        # Bahasa Indonesia
        "pelayanan", "service", "layanan", "penjual", "seller", "admin", "mimin", "kasir",
        "barista", "waiter", "pelayan", "staff", "staf", "karyawan", "owner", "owner-nya",
        "ramah", "sopan", "santun", "humble", "baik", "helpful", "judes", "jutek", "galak",
        "ketus", "cuek", "jutex", "respon", "response", "chat", "dibalas", "dibales",
        "slow respon", "fast respon", "gercep", "diabaikan", "tanggap", "komunikatif",
        "salah pesanan", "salah kirim", "kurang kirim", "salah menu", "tertukar",
        # English
        "customer service", "vendor", "shop", "store", "waitress", "employee", "polite",
        "kind", "attentive", "rude", "unfriendly", "reply", "replied", "slow response",
        "fast response", "ignored", "wrong item", "wrong order", "missing item"
    ],
    "Kecepatan & Pengiriman": [
        # Bahasa Indonesia
        "cepat", "cepet", "kilat", "gercep", "satset", "express", "lama", "lambat", "lelet",
        "ngaret", "nunggu", "antri", "antrean", "antrian", "nunggunya", "jam", "menit",
        "antar", "antarnya", "antarannya", "kurir", "driver", "ojol", "pengiriman", "kirim",
        "kiriman", "sampai", "nyampe", "durasi", "waktu tunggu", "delay",
        # English
        "speed", "swift", "slow", "late", "delayed", "wait", "waiting", "waited", "queue",
        "queueing", "hour", "hours", "minute", "minutes", "delivery", "courier", "rider",
        "shipping", "arrived", "arrival", "duration"
    ],
    "Harga & Nilai": [
        # Bahasa Indonesia
        "harga", "harganya", "price", "biaya", "murah", "murmer", "terjangkau", "ekonomis",
        "hemat", "mahal", "kemahalan", "mehong", "kantong", "worth", "worthit", "worthed",
        "layak", "sebanding", "sesuai", "padan", "promo", "diskon", "potongan harga",
        "voucher", "ongkir", "cashback", "pricey", "kemahalan",
        # English
        "pricing", "cost", "cheap", "affordable", "inexpensive", "budget", "expensive",
        "overpriced", "worth it", "worthwhile", "valuable", "value", "deal", "discount",
        "shipping fee"
    ]
}

# 5. Indikator Saran / Rekomendasi Konstruktif (Bilingual: ID & EN)
SUGGESTION_KEYWORDS = [
    # Bahasa Indonesia
    "saran", "sarannya", "masukan", "usul", "usulan", "rekomendasi", "request", "nasihat",
    "kritik", "feedback", "mungkin", "bisa", "bisakah", "boleh", "tolong", "mohon", "harap",
    "kiranya", "minta", "ada baiknya", "alangkah baiknya", "bagus kalau", "lebih baik",
    "enaknya", "sebaiknya", "seharusnya", "mending", "mendingan", "ke depannya", "kedepannya",
    "kedepan", "next", "next time", "berikutnya", "nanti", "nanti lagi", "lain kali", "perlu",
    "harus", "ditingkatkan", "tingkatkan", "tingkatin", "ditambah", "tambahkan", "tambahin",
    "diperbaiki", "perbaiki", "benerin", "dikurangi", "kurangi", "kurangin", "disesuaikan",
    "ganti", "diganti", "disediakan", "sediakan", "adain", "diadain", "perhatikan",
    "diperhatikan", "cek lagi", "lebih teliti", "diteliti", "dijaga", "variasi", "varian",
    "opsi", "menu baru", "pilihan", "alternatif", "inovasi", "coba",
    # English
    "suggest", "suggestion", "suggestions", "recommend", "recommendation", "input", "advice",
    "maybe", "perhaps", "could", "could you", "can you", "please", "kindly", "would be great if",
    "would be nice if", "better if", "hope", "hopefully", "should", "need to", "improve",
    "improved", "improvement", "enhance", "increase", "add", "added", "fix", "repair",
    "reduce", "provide", "consider", "option", "options", "variety", "variation", "variations",
    "alternative", "new menu", "in the future"
]

# 6. Sentiment Lexicon Positif (Bilingual: ID & EN)
POSITIVE_WORDS = {
    # Bahasa Indonesia
    "enak", "uenak", "lezat", "nikmat", "sedap", "maknyus", "gurih", "empuk", "lembut",
    "juicy", "renyah", "garing", "kriuk", "crispy", "krispi", "segar", "fresh", "hangat",
    "anget", "wangi", "harum", "nagih", "candu", "nagihin", "mantap", "mantul", "mantep",
    "jos", "josss", "puas", "suka", "senang", "favorit", "favorite", "cinta", "love",
    "rekomendasi", "rekomen", "recommended", "recomended", "top", "juara", "juaranya",
    "terbaik", "jempol", "keren", "bagus", "ciamik", "apik", "istimewa", "sempurna",
    "perfect", "hebat", "berkualitas", "premium", "ramah", "sopan", "santun", "humble",
    "baik", "tanggap", "responsif", "gercep", "helpful", "perhatian", "amanah", "jujur",
    "rapi", "rapih", "rapet", "bersih", "higienis", "hygienic", "resik", "steril",
    "estetik", "aesthetic", "cantik", "menarik", "aman", "safety", "cepat", "cepet",
    "kilat", "gesit", "satset", "express", "murah", "murmer", "terjangkau", "ekonomis",
    "hemat", "worth", "worthit", "worthed", "layak", "sebanding", "pas", "berkah", "untung",
    "langganan", "berlangganan", "repeat", "reorder", "oke", "ok", "sip", "lezatt",
    "enaknyoo", "memuaskan",
    # English
    "good", "great", "delicious", "tasty", "yummy", "delish", "savory", "flavorful",
    "amazing", "awesome", "fantastic", "excellent", "superb", "wonderful", "fabulous",
    "perfection", "tender", "warm", "hot", "satisfying", "satisfied", "loved", "favourite",
    "best", "attentive", "speedy", "prompt", "tidy", "spotless", "beautiful", "secure",
    "budget-friendly", "worthwhile", "generous", "happy", "pleased", "impressed", "solid", "super"
}

# 7. Sentiment Lexicon Negatif (Bilingual: ID & EN)
NEGATIVE_WORDS = {
    # Bahasa Indonesia
    "kurang", "kecewa", "menyesal", "nyesel", "kapok", "zonk", "rugi", "rugii",
    "hambar", "cemplang", "anyep", "asin", "keasinan", "kemanisan", "kepedesan",
    "pahit", "pait", "kepaitan", "basi", "basii", "mambu", "bau", "amis", "tengik",
    "apek", "bacin", "mentah", "mengkal", "gosong", "hangus", "tutong", "alot",
    "keras", "lembek", "benyek", "dingin", "adem", "oily", "berminyak", "enek",
    "eneg", "dikit", "sedikit", "pelit", "seiprit", "tumpah", "bocor", "rembes",
    "robek", "sobek", "hancur", "remuk", "rusak", "penyok", "peyot", "kotor",
    "jorok", "kumel", "debu", "lalat", "rambut", "kecoak", "lama", "lambat",
    "lelet", "ngaret", "mahal", "kemahalan", "mehong", "pricey", "judes", "jutek",
    "galak", "ketus", "cuek", "diabaikan", "tertukar", "penipu", "nipu", "bohong",
    "palsu", "buruk", "jelek", "ancur", "gagal", "kecele", "batal",
    "tidak ramah", "ga ramah", "tidak enak", "ga enak", "nggak enak",
    "tidak dibalas", "ga dibales", "diabaikan", "tidak niat", "ga niat",
    # English
    "bad", "worst", "worse", "terrible", "horrible", "awful", "poor", "poorly",
    "disappointed", "disappointing", "disappointment", "regret", "regretful", "regretted",
    "bland", "tasteless", "oversalted", "sour", "spoiled", "rotten", "stale", "smelly",
    "stinky", "raw", "undercooked", "burnt", "burned", "overcooked", "hard", "tough",
    "greasy", "sick", "nauseous", "small", "tiny", "little", "insufficient", "spilled",
    "spilt", "leaking", "leaked", "torn", "ripped", "crushed", "damaged", "broken",
    "dirty", "filthy", "messy", "disgusting", "gross", "unhygienic", "dusty", "slow",
    "delayed", "expensive", "overpriced", "rip-off", "ripoff", "rude", "impolite",
    "unfriendly", "unresponsive", "scam", "scammer", "fake", "dishonest", "ruined",
    "waste", "unacceptable"
}

# Kata kasar yang butuh pengecekan konteks ekstra
CONTEXT_DEPENDENT_WORDS = {"sampah", "najis", "trash", "garbage", "scum"}


class NLUCommentModerator:
    """
    Engine NLU untuk memproses, memoderasi, dan mengklasifikasi komentar
    pelanggan toko/penjual secara otomatis (Bilingual: Indonesia & English).
    """

    def __init__(self):
        self._build_abusive_patterns()

    def _build_abusive_patterns(self):
        """Membangun regular expression untuk menangkap kata kasar dan variasi leetspeak/masking."""
        escaped_words = [re.escape(w) for w in ABUSIVE_WORDS]
        self.abusive_regex = re.compile(r'\b(' + '|'.join(escaped_words) + r')\b', re.IGNORECASE)
        self.masked_regexes = [re.compile(p, re.IGNORECASE) for p in MASKED_ABUSIVE_PATTERNS]

    def normalize_leetspeak(self, text: str) -> str:
        """
        Mengembalikan teks leetspeak / angka pengganti huruf ke karakter alfabet standar.
        Contoh: 'anj1ng' -> 'anjing', 'g0bl0k' -> 'goblok', 'k0nt0l' -> 'kontol', 'b!tch' -> 'bitch'.
        Tanda seru di akhir kalimat (misal: 'enak!') tetap dipertahankan sebagai tanda baca.
        """
        de_spaced = re.sub(r'(?<=\b[a-zA-Z0-9])[\.\-\_\s](?=[a-zA-Z0-9]\b)', '', text)
        de_spaced = re.sub(r'!(?=[a-zA-Z])', 'i', de_spaced)

        leet_map = {
            '0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's',
            '7': 't', '8': 'b', '@': 'a', '$': 's'
        }
        res = []
        for char in de_spaced:
            res.append(leet_map.get(char, char))
        return "".join(res)

    def preprocess_text(self, text: str) -> Tuple[str, str]:
        """
        Pipeline NLU Preprocessing (Bilingual: ID & EN):
        1. HTML Unescape & Lowercasing
        2. Leetspeak Decoding
        3. Collapsing Karakter Berulang (misal: 'enaaaak' -> 'enak')
        4. Slang/Abbreviation Expansion ke bahasa formal (ID & EN)
        Mengembalikan: (raw_cleaned_text, normalized_text_for_analysis)
        """
        if not text:
            return "", ""

        raw = html.unescape(text).strip()
        lowered = unicodedata.normalize('NFKD', raw).lower()
        normalized_leet = self.normalize_leetspeak(lowered)
        collapsed = re.sub(r'(.)\1{2,}', r'\1', normalized_leet)
        tokens = re.findall(r"\b[\w'-]+\b", collapsed)
        expanded_tokens = [SLANG_MAP.get(tok, tok) for tok in tokens]
        expanded_text = " ".join(expanded_tokens)
        return raw, expanded_text

    def detect_profanity_and_toxicity(self, raw_text: str, preprocessed_text: str) -> Tuple[bool, List[str], str]:
        """
        Mengecek apakah komentar mengandung kata-kata kasar, makian, ujaran kebencian,
        sensoran leetspeak, atau konten toksik ('Comment aneh-aneh') baik bahasa Indonesia maupun English.
        """
        flagged = []
        lowered_raw = raw_text.lower()
        leet_normalized = self.normalize_leetspeak(lowered_raw)

        for target in [lowered_raw, leet_normalized, preprocessed_text]:
            matches = self.abusive_regex.findall(target)
            for m in matches:
                clean_m = m.lower()
                if clean_m not in flagged:
                    flagged.append(clean_m)

        for pattern in self.masked_regexes:
            matches = pattern.findall(lowered_raw)
            for m in matches:
                clean_m = m.lower()
                if clean_m not in flagged:
                    flagged.append(f"sensoran ({clean_m})")

        if re.search(r'\b(sampah|najis|trash|garbage|scum)\b', preprocessed_text) or re.search(r'\b(piece of shit|go to hell|kill yourself|shut up)\b', lowered_raw):
            flagged.append("hinaan degradatif (sampah/najis/trash)")

        if flagged:
            reason = f"Terdeteksi kata-kata kasar / makian: {', '.join(flagged)}. Sesuai aturan moderasi, komentar otomatis di-remove."
            return True, flagged, reason

        return False, [], ""

    def extract_aspects(self, text: str) -> List[str]:
        """Mengekstraksi aspek-aspek apa saja yang dibahas dalam komentar (Bilingual: ID & EN)."""
        found_aspects = []
        text_lower = text.lower()
        for aspect, keywords in ASPECT_KEYWORDS.items():
            for kw in keywords:
                if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                    found_aspects.append(aspect)
                    break
        return found_aspects

    def classify_comment(
        self,
        text: str,
        comment_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        rating: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Pipeline Utama Klasifikasi Komentar Toko (Bilingual: Indonesia & English):
        - Stage 1: Safety Gate (Auto-remove toxic/profane/abusive)
        - Stage 2: Sentiment Lexicon & Negation Rule-based Scoring
        - Stage 3: Constructive Suggestion & Aspect Topic Extraction
        """
        raw_text, preprocessed_text = self.preprocess_text(text)

        is_toxic, flagged_words, toxic_reason = self.detect_profanity_and_toxicity(raw_text, preprocessed_text)
        if is_toxic:
            return {
                "comment_id": comment_id,
                "tenant_id": tenant_id,
                "original_text": raw_text,
                "cleaned_text": preprocessed_text,
                "category": CommentCategory.ANEH_KASAR.value,
                "action": ModerationAction.AUTO_REMOVED.value,
                "is_delivered_to_dashboard": False,
                "confidence_score": 0.98,
                "sentiment": SentimentType.TOXIC.value,
                "aspects": self.extract_aspects(preprocessed_text),
                "flagged_words": flagged_words,
                "moderation_reason": toxic_reason,
                "dashboard_badge": "DIBLOKIR / REMOVED"
            }

        pos_score = 0.0
        neg_score = 0.0
        suggestion_score = 0.0

        tokens = preprocessed_text.split()
        for tok in tokens:
            if tok in POSITIVE_WORDS:
                pos_score += 1.0
            if tok in NEGATIVE_WORDS:
                neg_score += 1.0
            if tok in SUGGESTION_KEYWORDS:
                suggestion_score += 0.8

        # Cek frasa negasi negatif (Bahasa Indonesia & English)
        if re.search(r'\b(tidak|kurang|bukan|belum|ga|gak|nggak|not|never|barely|hardly|didnt|didn\'t|dont|don\'t|doesnt|doesn\'t)\s+(enak|mantap|manis|sedap|rapi|cepat|bersih|puas|ramah|dibalas|dibales|good|delicious|tasty|fresh|clean|fast|friendly|worth|satisfied|polite|proper|hot|warm|cooked)\b', preprocessed_text):
            neg_score += 2.5

        # Cek frasa keluhan tajam (Bahasa Indonesia & English)
        if re.search(r'\b(nyesel|kecewa|kapok|nipu|judes|jutek|zonk|hambar|basi|tumpah|regret|disappointed|disappointing|scam|scammer|ripoff|awful|terrible|horrible|spoiled|rotten|spilled|leaking|disgusting|gross|vomit)\b', preprocessed_text):
            neg_score += 2.0

        # Cek frasa penguat positif (Bahasa Indonesia & English)
        if re.search(r'\b(enak|mantap|lezat|puas|ramah|cepat|segar|estetik|good|delicious|tasty|fresh|friendly|fast|clean|aesthetic|recommended|satisfying|great|amazing|awesome|nice)\s+(banget|sekali|pisan|so\s+much|a\s+lot)\b|\b(so|very|really|super|extremely|highly|truly|absolutely)\s+(good|delicious|tasty|fresh|friendly|fast|clean|aesthetic|recommended|satisfying|great|amazing|awesome|nice)\b', preprocessed_text):
            pos_score += 2.5

        if rating is not None:
            if rating >= 4.0:
                pos_score += 1.5
            elif rating <= 2.5:
                neg_score += 1.5

        aspects = self.extract_aspects(preprocessed_text)

        if suggestion_score > 0 and neg_score == 0:
            pos_score += 1.0

        if pos_score >= neg_score:
            total = max(pos_score + neg_score + 0.1, 1.0)
            confidence = min(round(0.72 + (pos_score / total) * 0.26, 2), 0.99)
            category = CommentCategory.POSITIF.value
            sentiment = SentimentType.POSITIVE.value
            action = ModerationAction.DELIVERED_TO_DASHBOARD.value
            is_delivered = True
            reason = "Komentar berupa feedback apresiasi atau saran positif yang membangun. Diteruskan ke dashboard toko."
            badge = "Apresiasi & Rekomendasi"
        else:
            total = max(pos_score + neg_score + 0.1, 1.0)
            confidence = min(round(0.72 + (neg_score / total) * 0.26, 2), 0.99)
            category = CommentCategory.NEGATIF.value
            sentiment = SentimentType.NEGATIVE.value
            action = ModerationAction.DELIVERED_TO_DASHBOARD.value
            is_delivered = True
            reason = "Komentar berisi kritik/keluhan santun tanpa bahasa kasar. Diteruskan ke dashboard toko untuk evaluasi perbaikan."
            badge = "Perlu Perhatian / Evaluasi"

        return {
            "comment_id": comment_id,
            "tenant_id": tenant_id,
            "original_text": raw_text,
            "cleaned_text": preprocessed_text,
            "category": category,
            "action": action,
            "is_delivered_to_dashboard": is_delivered,
            "confidence_score": confidence,
            "sentiment": sentiment,
            "aspects": aspects,
            "flagged_words": [],
            "moderation_reason": reason,
            "dashboard_badge": badge
        }

    def moderate_batch(self, comments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Moderasi dan klasifikasi kumpulan komentar sekaligus (Bilingual: ID & EN)."""
        processed_comments = []
        delivered_to_dashboard = []
        auto_removed = []

        summary_counts = {
            CommentCategory.POSITIF.value: 0,
            CommentCategory.NEGATIF.value: 0,
            CommentCategory.ANEH_KASAR.value: 0,
        }

        for item in comments:
            cid = item.get("id") or item.get("comment_id")
            tid = item.get("tenant_id") or item.get("tenantId")
            text = item.get("text") or item.get("comment") or item.get("comment_text") or ""
            rating = item.get("rating")

            result = self.classify_comment(text=text, comment_id=cid, tenant_id=tid, rating=rating)
            processed_comments.append(result)
            summary_counts[result["category"]] += 1

            if result["is_delivered_to_dashboard"]:
                delivered_to_dashboard.append(result)
            else:
                auto_removed.append(result)

        return {
            "total_processed": len(comments),
            "total_delivered_to_dashboard": len(delivered_to_dashboard),
            "total_auto_removed": len(auto_removed),
            "summary_by_category": summary_counts,
            "delivered_comments": delivered_to_dashboard,
            "removed_comments": auto_removed,
            "all_results": processed_comments
        }


# Singleton instance
comment_moderator = NLUCommentModerator()
