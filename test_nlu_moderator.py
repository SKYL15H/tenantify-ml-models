from comment_moderator import comment_moderator

test_comments = [
    ("Makanannya enak bgt, porsinya pas dan packing rapi!", "Kritik & Saran Positif"),
    ("Kopinya mantap, mungkin ke depannya bisa sediain varian oat milk ya kak", "Kritik & Saran Positif"),
    ("Saran saya packagingnya diganti paper bag ya biar lebih eco friendly", "Kritik & Saran Positif"),
    ("Ayamnya masih mentah bagian dalam kak, tolong lebih teliti lagi masaknya", "Kritik & Saran Negatif"),
    ("Pesanan sampai 1 jam lebih, makanannya sudah dingin dan kuahnya tumpah", "Kritik & Saran Negatif"),
    ("Adminnya judes banget dichat ga dibales", "Kritik & Saran Negatif"),
    ("porsinya dikit banget min, nyesel beli mahal-mahal", "Kritik & Saran Negatif"),
    ("Woy babi lu jualan makanan basi anjing!", "Comment aneh-aneh (komentar yang berbahasa kasar)"),
    ("Penjual t0l0l, nyesel beli di toko sampah ini gblk", "Comment aneh-aneh (komentar yang berbahasa kasar)"),
    ("makanan baji***an lu nipu gue", "Comment aneh-aneh (komentar yang berbahasa kasar)"),
    ("b.a.b.i lu jualan kaga bener", "Comment aneh-aneh (komentar yang berbahasa kasar)"),
    ("4nj1nk lu gausah jualan", "Comment aneh-aneh (komentar yang berbahasa kasar)")
]

print("=== PENGUJIAN KOMPREHENSIF NLU MODERATOR (12 TEST CASES) ===")
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
