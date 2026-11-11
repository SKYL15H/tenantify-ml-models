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


# ── Kamus Singkatan & Slang Bahasa Indonesia ─────────────────────────
SLANG_MAP = {
    "bgt": "banget", "bgtss": "banget", "bgtt": "banget", "bngtt": "banget",
    "ga": "tidak", "gak": "tidak", "gk": "tidak", "g": "tidak", "kaga": "tidak",
    "kagak": "tidak", "tdk": "tidak", "ngga": "tidak", "nggak": "tidak", "nda": "tidak",
    "tp": "tapi", "tpi": "tapi", "ttp": "tetap",
    "dgn": "dengan", "dg": "dengan",
    "sy": "saya", "aq": "saya", "aku": "saya", "gw": "saya", "gue": "saya", "gua": "saya",
    "lu": "kamu", "lo": "kamu", "loe": "kamu", "ente": "kamu", "lw": "kamu",
    "bgs": "bagus", "bgus": "bagus", "mantul": "mantap", "mantep": "mantap",
    "mantapp": "mantap", "top": "mantap", "jos": "mantap", "josss": "mantap",
    "krg": "kurang", "kurg": "kurang", "kurng": "kurang",
    "bnyk": "banyak", "byk": "banyak",
    "dikit": "sedikit", "sdkt": "sedikit", "dkit": "sedikit",
    "tlg": "tolong", "pls": "tolong", "plz": "tolong", "mohon": "tolong",
    "mkn": "makan", "mknn": "makanan", "makann": "makanan",
    "minum": "minuman", "mnm": "minuman", "mnmn": "minuman",
    "pesen": "pesan", "pesenan": "pesanan", "orderan": "pesanan",
    "hrg": "harga", "mrh": "murah", "mhl": "mahal",
    "packing": "kemasan", "packaging": "kemasan", "bungkus": "kemasan", "bungkusnya": "kemasan",
    "ancur": "hancur", "tumpah": "tumpah", "bocor": "bocor", "robek": "robek",
    "asin": "asin", "keasinan": "asin", "hambar": "hambar", "anyep": "hambar",
    "basi": "basi", "bau": "bau", "apek": "bau", "mentah": "mentah",
    "gosong": "gosong", "hangus": "gosong",
    "ramah": "ramah", "judes": "judes", "jutek": "jutek", "galak": "galak", "cuek": "cuek",
    "cepet": "cepat", "cpt": "cepat", "fast": "cepat", "kenceng": "cepat",
    "lama": "lambat", "lemot": "lambat", "lelet": "lambat", "llet": "lambat",
    "recomended": "rekomendasi", "rekomen": "rekomendasi", "worth": "layak", "worthit": "layak",
    "nyesel": "menyesal", "kecewa": "kecewa", "kapok": "kapok", "zonk": "zonk",
    "bikin": "membuat", "beneran": "sungguh",
    "next": "selanjutnya", "kedepan": "kedepannya", "kalo": "kalau", "kl": "kalau", "klo": "kalau"
}

# ── Kamus Kata Kasar & Abusive (Indonesian Toxic Lexicon) ────────────
ABUSIVE_WORDS = {
    # Hewan sebagai makian
    "anjing", "anj1ng", "anjink", "anying", "anjeng", "asw", "asu",
    "babi", "b4b1", "bb1",
    # Makian kasar & umpatan
    "bangsat", "b@ngs@t", "b4ngs4t", "bajingan", "b4j1ng4n", "kampret", "brengsek", "keparat",
    "jancuk", "jancok", "dancok", "dancuk", "cok", "cuk",
    "bangke", "bangkai", "tai", "taek", "tae", "setan", "iblis", "dajjal",
    # Organ reproduksi & seksual kasar
    "kontol", "k0nt0l", "kntil", "kntl", "memek", "mmk", "jembut", "jmbt",
    "pantek", "peler", "itil", "tetek", "ngentot", "ngentod",
    "lonte", "lont3", "pelacur", "jablay", "perek", "sundal", "pecun", "bencong",
    # Cacian mental/intelektual kasar
    "goblok", "g0bl0k", "gblk", "goblog", "tolol", "t0l0l", "tll", "bego", "bgok",
    "idiot", "pekok", "autis", "dungu", "otak udang",
    # Frasa umpatan
    "sialan", "biadab", "laknat", "mampus", "modar", "mati aja"
}

# Pola regex untuk makian yang disamarkan dengan tanda bintang / simbol
# Contoh: baji***an, anj**g, k*nt*l, g*bl*k, b*b*, b*ngs*t
MASKED_ABUSIVE_PATTERNS = [
    r'\bb+a+j+i+[\*\@\#\$\%\&]+[a-z]*\b',   # baji***an
    r'\ba+n+j+[\*\@\#\$\%\&]+[a-z]*\b',     # anj**g, anj**k
    r'\bb+[\*\@\#\$\%\&]+b+i+\b',           # b*bi, b**i
    r'\bk+[\*\@\#\$\%\&]+n+t+[\*\@\#\$\%\&]*o*l*\b', # k*nt*l
    r'\bg+[\*\@\#\$\%\&]+b+l+[\*\@\#\$\%\&]*[a-z]*\b', # g*bl*k
    r'\bb+[\*\@\#\$\%\&]+n+g+s+[\*\@\#\$\%\&]*t*\b',   # b*ngs*t
    r'\bm+[\*\@\#\$\%\&]+m+[\*\@\#\$\%\&]*k+\b',       # m*m*k
    r'\bt+[\*\@\#\$\%\&]+l+[\*\@\#\$\%\&]*l*\b',       # t*l*l
    r'\bj+a+n+c+[\*\@\#\$\%\&]+[a-z]*\b',   # janc**k
]

# Kata kasar yang butuh pengecekan konteks ekstra
CONTEXT_DEPENDENT_WORDS = {"sampah", "najis"}

# ── Kamus Aspek Review untuk Analisis Toko ──────────────────────────
ASPECT_KEYWORDS = {
    "Rasa & Kualitas": [
        "rasa", "rasanya", "enak", "mantap", "lezat", "sedap", "nagih", "nikmat",
        "asin", "keasinan", "hambar", "manis", "kemanisan", "pahit", "pedas", "pedes",
        "basi", "bau", "mentah", "gosong", "dingin", "renyah", "crispy", "alot", "segar"
    ],
    "Porsi & Takaran": [
        "porsi", "porsinya", "dikit", "sedikit", "banyak", "kenyang", "pas",
        "jumbo", "mini", "ukurannya", "potongan", "isi", "isinya", "tebel", "tipis"
    ],
    "Kemasan & Kebersihan": [
        "kemasan", "packing", "packaging", "bungkus", "bungkusnya", "plastik",
        "tumpah", "bocor", "robek", "rapi", "higienis", "bersih", "kotor", "debu", "paper bag"
    ],
    "Pelayanan & Tenant": [
        "pelayanan", "penjual", "seller", "admin", "ramah", "sopan", "jutek",
        "galak", "judes", "respon", "chat", "dibalas", "dibales", "cuek", "tanggap"
    ],
    "Kecepatan & Pengiriman": [
        "cepat", "cepet", "kilat", "lama", "lambat", "lelet", "nunggu", "antri",
        "antar", "pengiriman", "sampai", "jam"
    ],
    "Harga & Nilai": [
        "harga", "harganya", "murah", "terjangkau", "mahal", "kemahalan",
        "worth", "worthit", "sebanding", "sesuai", "promo", "diskon"
    ]
}

# ── Indikator Saran / Rekomendasi Konstruktif ────────────────────────
SUGGESTION_KEYWORDS = [
    "saran", "sarannya", "masukan", "mungkin", "bisa", "tolong", "mohon",
    "ke depannya", "kedepannya", "next", "perlu", "ditingkatkan", "ditambah",
    "variasi", "varian", "opsi", "coba", "bagus kalau", "lebih baik", "harap"
]

# ── Sentiment Lexicon Positif & Negatif ─────────────────────────────
POSITIVE_WORDS = {
    "enak", "mantap", "lezat", "nikmat", "sedap", "suka", "favorit", "nagih",
    "juara", "top", "bagus", "rapi", "bersih", "ramah", "cepat", "puas",
    "murah", "terjangkau", "rekomendasi", "rekomen", "terbaik", "senang",
    "berlangganan", "langganan", "memuaskan", "segar", "hangat", "krispi",
    "pas", "worth", "worthit", "oke", "ok", "jempol", "keren", "estetik",
    "higienis", "fresh", "crispy", "lezatt", "enaknyoo"
}

NEGATIVE_WORDS = {
    "kurang", "kecewa", "menyesal", "nyesel", "kapok", "zonk",
    "asin", "keasinan", "hambar", "basi", "bau", "mentah", "gosong",
    "tumpah", "bocor", "kotor", "dingin", "alot", "keras", "lama", "lelet",
    "lambat", "mahal", "kemahalan", "dikit", "sedikit", "rusak", "tertukar",
    "judes", "jutek", "galak", "cuek", "penipu", "nipu", "bohong",
    "tidak ramah", "ga ramah", "tidak enak", "ga enak", "nggak enak",
    "tidak dibalas", "ga dibales", "diabaikan", "tidak niat", "ga niat"
}


class NLUCommentModerator:
    """
    Engine NLU untuk memproses, memoderasi, dan mengklasifikasi komentar
    pelanggan toko/penjual secara otomatis.
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
        Contoh: 'anj1ng' -> 'anjing', 'g0bl0k' -> 'goblok', 'k0nt0l' -> 'kontol'.
        """
        # Hapus spasi atau titik antar huruf yang sengaja dibuat untuk bypass filter (misal: a.n.j.i.n.g -> anjing)
        de_spaced = re.sub(r'(?<=\b[a-zA-Z0-9])[\.\-\_\s](?=[a-zA-Z0-9]\b)', '', text)

        leet_map = {
            '0': 'o',
            '1': 'i',
            '3': 'e',
            '4': 'a',
            '5': 's',
            '7': 't',
            '8': 'b',
            '@': 'a',
            '$': 's',
            '!': 'i'
        }
        res = []
        for char in de_spaced:
            res.append(leet_map.get(char, char))
        return "".join(res)

    def preprocess_text(self, text: str) -> Tuple[str, str]:
        """
        NLU Pipeline Preprocessing:
        1. Cleaning & Unescaping
        2. Leetspeak normalization
        3. Collapsing character elongation (misal: 'enaaaak' -> 'enak')
        4. Slang/abbreviation expansion ke bahasa Indonesia baku/formal
        Mengembalikan (cleaned_text, normalized_text_for_analysis).
        """
        if not text:
            return "", ""

        # Step 1: HTML unescape & lowercasing
        raw = html.unescape(text).strip()
        lowered = unicodedata.normalize('NFKD', raw).lower()

        # Step 2: Leetspeak decoding untuk deteksi kata kasar
        normalized_leet = self.normalize_leetspeak(lowered)

        # Step 3: Collapse repeated characters (3x atau lebih berturut-turut jadi 1 atau 2)
        collapsed = re.sub(r'(.)\1{2,}', r'\1', normalized_leet)

        # Step 4: Tokenize & Slang Expansion
        tokens = re.findall(r'\b[\w\'-]+\b', collapsed)
        expanded_tokens = [SLANG_MAP.get(tok, tok) for tok in tokens]
        expanded_text = " ".join(expanded_tokens)

        return raw, expanded_text

    def detect_profanity_and_toxicity(self, raw_text: str, preprocessed_text: str) -> Tuple[bool, List[str], str]:
        """
        Mengecek apakah komentar mengandung kata-kata kasar, makian, ujaran kebencian,
        atau konten toksik ('Comment aneh-aneh').
        """
        flagged = []
        lowered_raw = raw_text.lower()
        leet_normalized = self.normalize_leetspeak(lowered_raw)

        # 1. Cek kata kasar standar pada teks raw, leet, dan preprocessed
        for target in [lowered_raw, leet_normalized, preprocessed_text]:
            matches = self.abusive_regex.findall(target)
            for m in matches:
                clean_m = m.lower()
                if clean_m not in flagged:
                    flagged.append(clean_m)

        # 2. Cek makian bertanda bintang / simbol (misal: baji***an, a**ing, k*nt*l)
        for pattern in self.masked_regexes:
            matches = pattern.findall(lowered_raw)
            for m in matches:
                clean_m = m.lower()
                if clean_m not in flagged:
                    flagged.append(f"sensoran ({clean_m})")

        # 3. Cek context-dependent insults (contoh: 'toko sampah', 'makanan sampah', 'najis')
        if re.search(r'\b(sampah|najis)\b', preprocessed_text):
            flagged.append("hinaan degradatif (sampah/najis)")

        # Jika ada makian eksplisit
        if flagged:
            reason = f"Terdeteksi kata-kata kasar / makian: {', '.join(flagged)}. Sesuai aturan moderasi, komentar otomatis di-remove."
            return True, flagged, reason

        return False, [], ""

    def extract_aspects(self, text: str) -> List[str]:
        """Mengekstraksi aspek-aspek apa saja yang dibahas dalam komentar."""
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
        Fungsi Utama Klasifikasi & Moderasi NLU:
        Mengembalikan keputusan routing:
        - Jika Kategori 'Comment aneh-aneh' -> Action: AUTO_REMOVED (Dihapus dari publik, tidak ke dashboard)
        - Jika Kategori 'Kritik & Saran Positif' -> Action: DELIVERED_TO_DASHBOARD (Terkirim ke dashboard)
        - Jika Kategori 'Kritik & Saran Negatif' -> Action: DELIVERED_TO_DASHBOARD (Terkirim ke dashboard)
        """
        raw_text, preprocessed_text = self.preprocess_text(text)

        # Jika komentar kosong
        if not raw_text.strip():
            return {
                "comment_id": comment_id,
                "tenant_id": tenant_id,
                "original_text": text,
                "cleaned_text": "",
                "category": CommentCategory.NEGATIF.value,
                "action": ModerationAction.AUTO_REMOVED.value,
                "is_delivered_to_dashboard": False,
                "confidence_score": 1.0,
                "sentiment": SentimentType.NEGATIVE.value,
                "aspects": [],
                "flagged_words": [],
                "moderation_reason": "Komentar kosong / tidak valid.",
                "dashboard_badge": "DIBLOKIR / REMOVED"
            }

        # ── STAGE 1: Toxicity & Safety Gate ─────────────────────────
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

        # ── STAGE 2: Sentiment & Constructive Suggestion Classification ──
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

        # Cek frasa negasi negatif (misal: 'tidak enak', 'kurang manis', 'tidak dibalas')
        if re.search(r'\b(tidak|kurang|bukan|belum|ga|gak|nggak)\s+(enak|mantap|manis|sedap|rapi|cepat|bersih|puas|ramah|dibalas|dibales)\b', preprocessed_text):
            neg_score += 2.5

        # Cek frasa keluhan khusus (misal: 'nyesel beli', 'kecewa banget', 'nipu lu')
        if re.search(r'\b(nyesel|kecewa|kapok|nipu|judes|jutek|zonk|hambar|basi|tumpah)\b', preprocessed_text):
            neg_score += 2.0

        # Cek frasa penguat positif (misal: 'enak banget', 'sangat ramah')
        if re.search(r'\b(enak|mantap|lezat|puas|ramah|cepat|segar|estetik)\s+(banget|sekali|pisan)\b', preprocessed_text):
            pos_score += 2.5

        # Pertimbangan Rating (jika ada nilai rating 1-5 bintang dari user)
        if rating is not None:
            if rating >= 4.0:
                pos_score += 1.5
            elif rating <= 2.5:
                neg_score += 1.5

        # Aspek yang terdeteksi
        aspects = self.extract_aspects(preprocessed_text)

        # Penentuan Kategori: Positif vs Negatif
        # Jika komentar adalah saran membangun ("Saran saya packaging diganti paper bag ya")
        # dan tidak ada keluhan negatif tajam -> masuk ke Kritik & Saran Positif
        if suggestion_score > 0 and neg_score == 0:
            pos_score += 1.0

        if pos_score >= neg_score:
            # Kritik & Saran Positif
            total = max(pos_score + neg_score + 0.1, 1.0)
            confidence = min(round(0.72 + (pos_score / total) * 0.26, 2), 0.99)
            category = CommentCategory.POSITIF.value
            sentiment = SentimentType.POSITIVE.value
            action = ModerationAction.DELIVERED_TO_DASHBOARD.value
            is_delivered = True
            reason = "Komentar berupa feedback apresiasi atau saran positif yang membangun. Diteruskan ke dashboard toko."
            badge = "Apresiasi & Rekomendasi"
        else:
            # Kritik & Saran Negatif
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
        """
        Moderasi dan klasifikasi kumpulan komentar sekaligus.
        Memisahkan komentar yang otomatis dihapus vs komentar yang diteruskan ke dashboard toko.
        """
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
            text = item.get("text") or item.get("comment") or ""
            rating = item.get("rating")

            result = self.classify_comment(
                text=text,
                comment_id=cid,
                tenant_id=tid,
                rating=rating
            )
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


# Global singleton instance untuk reuse
comment_moderator = NLUCommentModerator()
