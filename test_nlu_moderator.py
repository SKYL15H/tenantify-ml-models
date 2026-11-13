from comment_moderator import comment_moderator

test_comments = [
    # ── Kategori: Kritik & Saran Positif (Bahasa Indonesia)
    ("Makanannya enak bgt, porsinya pas dan packing rapi!", "Kritik & Saran Positif"),
    ("Kopinya mantap, mungkin ke depannya bisa sediain varian oat milk ya kak", "Kritik & Saran Positif"),
    ("Saran saya packagingnya diganti paper bag ya biar lebih eco friendly", "Kritik & Saran Positif"),
    ("Pelayanan ramah banget, packagingnya rapi dan estetik.", "Kritik & Saran Positif"),
    ("Gila enak bgt parah nagih!", "Kritik & Saran Positif"),
    ("Makanannya ciamik pol, porsi melimpah murmer!", "Kritik & Saran Positif"),

    # ── Kategori: Kritik & Saran Positif (English)
    ("The food was super delicious, huge portion and prompt delivery!", "Kritik & Saran Positif"),
    ("Really loved the coffee, amazing aroma and friendly barista!", "Kritik & Saran Positif"),
    ("Neat packaging and aesthetic presentation, highly recommended!", "Kritik & Saran Positif"),
    ("Tasty burger, maybe in the future you could add more vegan options please", "Kritik & Saran Positif"),
    ("Awesome taste and fast delivery! Will definitely reorder soon.", "Kritik & Saran Positif"),

    # ── Kategori: Kritik & Saran Negatif (Bahasa Indonesia)
    ("Ayamnya masih mentah bagian dalam kak, tolong lebih teliti lagi masaknya", "Kritik & Saran Negatif"),
    ("Pesanan sampai 1 jam lebih, makanannya sudah dingin dan kuahnya tumpah", "Kritik & Saran Negatif"),
    ("Adminnya judes banget dichat ga dibales", "Kritik & Saran Negatif"),
    ("porsinya dikit banget min, nyesel beli mahal-mahal", "Kritik & Saran Negatif"),
    ("Rasa kuahnya hambar cemplang, ayamnya alot keras, mahal bener kapok", "Kritik & Saran Negatif"),

    # ── Kategori: Kritik & Saran Negatif (English)
    ("The chicken was still raw inside, please cook it more carefully next time", "Kritik & Saran Negatif"),
    ("Waited over 1 hour, the food arrived completely cold and the soup was spilled", "Kritik & Saran Negatif"),
    ("Very rude cashier and slow response, never replied to my chat", "Kritik & Saran Negatif"),
    ("Tiny portion for an expensive price, totally regret buying here", "Kritik & Saran Negatif"),
    ("The pasta was bland and oversalted, disappointing quality", "Kritik & Saran Negatif"),

    # ── Kategori: Comment aneh-aneh (Bahasa Indonesia)
    ("Woy babi lu jualan makanan basi anjing!", "Comment aneh-aneh (komentar yang berbahasa kasar)"),
    ("Penjual t0l0l, nyesel beli di toko sampah ini gblk", "Comment aneh-aneh (komentar yang berbahasa kasar)"),
    ("makanan baji***an lu nipu gue", "Comment aneh-aneh (komentar yang berbahasa kasar)"),
    ("b.a.b.i lu jualan kaga bener", "Comment aneh-aneh (komentar yang berbahasa kasar)"),
    ("4nj1nk lu gausah jualan", "Comment aneh-aneh (komentar yang berbahasa kasar)"),
    ("Jancuk lu jualan basi!", "Comment aneh-aneh (komentar yang berbahasa kasar)"),
    ("Woy k*nt*l pesanan gua mana?", "Comment aneh-aneh (komentar yang berbahasa kasar)"),

    # ── Kategori: Comment aneh-aneh (English)
    ("What the fuck is this food, you stupid seller!", "Comment aneh-aneh (komentar yang berbahasa kasar)"),
    ("This store is full of assholes, trash service!", "Comment aneh-aneh (komentar yang berbahasa kasar)"),
    ("F*ck you, scammer bitch!", "Comment aneh-aneh (komentar yang berbahasa kasar)"),
    ("Piece of shit food, go to hell moron", "Comment aneh-aneh (komentar yang berbahasa kasar)"),
    ("Disgusting sh*t, never order from this bastard again", "Comment aneh-aneh (komentar yang berbahasa kasar)")
]

print("=== PENGUJIAN KOMPREHENSIF NLU MODERATOR (33 TEST CASES BILINGUAL ID & EN) ===")
passed = 0
for text, expected in test_comments:
    res = comment_moderator.classify_comment(text)
    actual = res["category"]
    action = res["action"]
    is_ok = (actual == expected)
    if is_ok:
        passed += 1
    status_symbol = "[OK]" if is_ok else "[FAIL]"
    print(f"{status_symbol} Input: {text}")
    print(f"     Expected : {expected}")
    print(f"     Actual   : {actual}")
    print(f"     Action   : {action} (Dashboard: {res['is_delivered_to_dashboard']})")
    print(f"     Aspects  : {res['aspects']}")
    print(f"     Flagged  : {res['flagged_words']}")
    print("-" * 65)

print(f"\nHasil Akhir Akurasi: {passed}/{len(test_comments)} ({passed/len(test_comments)*100:.1f}%)")
