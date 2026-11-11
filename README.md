---
title: Tenantify AI Backend
emoji: 🚀
colorFrom: indigo
colorTo: blue
sdk: gradio
sdk_version: 6.31.0
python_version: "3.12"
app_file: app.py
pinned: false
---

# Tenantify AI — Recommendation & NLU Moderation Backend

Microservice REST API untuk rekomendasi produk UMKM berbasis Content-Based Filtering menggunakan model multilingual `BAAI/bge-m3` + FAISS Index, serta sistem NLU Text Moderation untuk filter komentar.

## Endpoints

- `GET /docs` — Swagger UI API Documentation
- `GET /health` — Service Health Check
- `GET /products` — Ambil daftar produk
- `GET /orders` — Ambil daftar riwayat order
- `POST /recommend/by-product` — Rekomendasi berdasarkan produk pilihan
- `POST /recommend/by-order` — Rekomendasi pelengkap berdasarkan keranjang pesanan
- `POST /comments/classify` — Klasifikasi satu komentar pembeli
- `POST /comments/moderate-batch` — Moderasi batch komentar sekaligus
