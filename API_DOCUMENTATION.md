# 🛒 Tenantify AI — API Documentation (Untuk Fullstack)

Dokumentasi REST API Rekomendasi Tenantify berbasis AI Hybrid Scoring (`BAAI/bge-m3` + FAISS + Category Complementary).

---

## 🚀 Cara Menjalankan AI Service

Pastikan library sudah terinstall, lalu jalankan di terminal:

```bash
# 1. Install dependencies (sekali saja)
pip install -r requirements.txt

# 2. Jalankan server
python main.py
```

* **Live Base URL (Production HF Space):** `https://s4usan-tenantify-models.hf.space`
* **Live Interactive Swagger UI:** [`https://s4usan-tenantify-models.hf.space/docs`](https://s4usan-tenantify-models.hf.space/docs) (bisa langsung dicoba di browser)
* **Local Development Base URL:** `http://localhost:8000`
* **Local Swagger UI:** [`http://localhost:8000/docs`](http://localhost:8000/docs)
* **CORS:** Sudah di-enable untuk semua origin (`*`), jadi aman dipanggil dari React / Next.js / Vue (port 3000, 5173, dll).

---

## 📌 Endpoints

### 1. Health Check
Mengecek status server dan model AI.

* **Method:** `GET`
* **URL:** `/health`
* **Response `200 OK`:**
```json
{
  "status": "ok",
  "model": "BAAI/bge-m3",
  "total_products": 48,
  "total_tenants": 19,
  "total_orders": 25
}
```

---

### 2. Rekomendasi Berdasarkan Satu Produk
> **Gunakan pada:** Halaman detail produk / modal produk (seksi *"Cocok dinikmati bersama"*).

* **Method:** `POST`
* **URL:** `/recommend/by-product`
* **Request Headers:** `Content-Type: application/json`
* **Request Body:**
```json
{
  "product_id": "gk-1",
  "top_n": 5,
  "exclude_same_tenant": true,
  "category_filter": null
}
```

| Field | Type | Default | Keterangan |
|---|---|---|---|
| `product_id` | `string` | *(wajib)* | ID produk yang sedang dilihat user (contoh: `"gk-1"`, `"cp-1"`) |
| `top_n` | `number` | `5` | Jumlah rekomendasi yang dikembalikan (1 - 20) |
| `exclude_same_tenant` | `boolean` | `true` | `true` = hanya rekomendasi dari tenant lain (pemerataan UMKM) |
| `category_filter` | `string` / `null` | `null` | Filter kategori spesifik: `"Minuman"`, `"Makanan"`, `"Camilan"`, `"Dessert"`, dll |

* **Response `200 OK`:**
```json
{
  "query_product": {
    "id": "gk-1",
    "name": "Kue Ikan Isi Coklat",
    "tenantId": "tenant-7",
    "tenantName": "Gorengan & Kue Ikan Kak Sari",
    "boothNumber": "Blok B-07",
    "category": "Camilan",
    "price": 5000,
    "description": "Kue ikan crispy berbentuk ikan dengan isian coklat lumer...",
    "rating": 4.8,
    "image": "/images/kue-ikan-coklat.jpg",
    "soldCount": 450,
    "isPopular": true
  },
  "recommendations": [
    {
      "product": {
        "id": "cp-1",
        "name": "Kopi Susu Gula Aren",
        "tenantId": "tenant-1",
        "tenantName": "Kopi & Roti Nusantara",
        "boothNumber": "Blok A-04",
        "category": "Minuman",
        "price": 18000,
        "description": "Kopi espresso pilihan dipadukan susu creamy dan sirup gula aren asli...",
        "rating": 4.9,
        "image": "/images/kopi-susu.jpg",
        "soldCount": 1240,
        "isPopular": true
      },
      "hybrid_score": 1.0,
      "semantic_score": 1.0,
      "complementary_score": 1.0,
      "reason": "Minuman ini sangat cocok dipadukan dengan Camilan 'Kue Ikan Isi Coklat' (relevansi konteks: 100%)."
    }
  ],
  "total_returned": 1
}
```

---

### 3. Rekomendasi Berdasarkan Pesanan Aktif (Cart / Checkout)
> **Gunakan pada:** Halaman keranjang belanja / ringkasan order (seksi *"Tambahkan ke pesananmu"*).

* **Method:** `POST`
* **URL:** `/recommend/by-order`
* **Request Body:** (Bisa langsung passing array `items` dari order object frontend)
```json
{
  "items": [
    {
      "productName": "Kopi Susu Gula Aren",
      "tenantName": "Kopi & Roti Nusantara",
      "price": 18000,
      "quantity": 1,
      "notes": "Gula aren sedikit"
    },
    {
      "productName": "Paket Ayam Geprek Krispi + Nasi",
      "tenantName": "Ayam Geprek Sambal Korek",
      "price": 25000,
      "quantity": 1,
      "notes": "Pedas sedang"
    }
  ],
  "top_n": 5
}
```

* **Response `200 OK`:**
```json
{
  "ordered_products": [ ... ],
  "recommendations": [
    {
      "product": {
        "id": "jp-1",
        "name": "Klepon Pandan Original",
        "tenantName": "Jajanan Pasar Mbok Darmi",
        "boothNumber": "Blok A-09",
        "category": "Camilan",
        "price": 8000,
        "rating": 4.9,
        ...
      },
      "hybrid_score": 0.814,
      "semantic_score": 0.69,
      "complementary_score": 1.0,
      "reason": "Camilan ini cocok melengkapi pesananmu yang didominasi Minuman (relevansi: 69%)."
    }
  ],
  "total_returned": 1
}
```

---

### 4. Rekomendasi Langsung dari ID Pesanan
> **Gunakan pada:** Halaman status pesanan / detail order yang sudah tersimpan di database.

* **Method:** `POST`
* **URL:** `/recommend/by-order-id/{order_id}?top_n=5`
* **Path Parameter:** `order_id` (contoh: `ORD-9201` atau `ORD-9205`)
* **Query Parameter:** `top_n` (opsional, default: 5)
* **Response `200 OK`:** Format sama persis dengan `/recommend/by-order` di atas.

---

### 5. Manajemen Data Pesanan (Orders)
> **Gunakan pada:** Dashboard kasir, tenant view, atau tracking status pesanan.

* **List Orders:** `GET /orders?status=Siap Diambil&order_type=Dine-in`
  * Query parameters opsional:
    * `status`: `Siap Diambil` | `Sedang Diproses` | `Selesai`
    * `order_type`: `Dine-in` | `Takeaway`
* **Detail Order:** `GET /orders/{order_id}` (contoh: `/orders/ORD-9201`)

---

## 💻 Contoh Snippet Kode Frontend (Next.js / React)

### Menggunakan Native `fetch` (JavaScript / TypeScript)
```typescript
const AI_BASE_URL = "http://localhost:8000";

// 1. Rekomendasi by Product
export async function getRecommendationsByProduct(productId: string, topN = 5) {
  const res = await fetch(`${AI_BASE_URL}/recommend/by-product`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      product_id: productId,
      top_n: topN,
      exclude_same_tenant: true,
    }),
  });
  if (!res.ok) throw new Error("Gagal mengambil rekomendasi AI");
  return res.json();
}

// 2. Rekomendasi by Active Order Items (Cart State)
export async function getRecommendationsByOrder(orderItems: any[], topN = 5) {
  const res = await fetch(`${AI_BASE_URL}/recommend/by-order`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      items: orderItems,
      top_n: topN,
    }),
  });
  if (!res.ok) throw new Error("Gagal mengambil rekomendasi cart");
  return res.json();
}

// 3. Rekomendasi by Order ID yang sudah tersimpan
export async function getRecommendationsByOrderId(orderId: string, topN = 5) {
  const res = await fetch(`${AI_BASE_URL}/recommend/by-order-id/${orderId}?top_n=${topN}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Gagal mengambil rekomendasi order ID");
  return res.json();
}
```



---

## 🛡️ NLU Comment Classification & Moderation (Fitur Baru)
Microservice NLU (Natural Language Understanding) untuk memoderasi dan mengklasifikasi komentar pelanggan toko/penjual.

### 📋 3 Parameter Klasifikasi & Business Logic:
| Parameter Klasifikasi | Action Sistem | Dashboard Toko / Penjual | Keterangan |
|---|---|---|---|
| **`Kritik & Saran Positif`** | `DELIVERED_TO_DASHBOARD` | ✅ Ditampilkan (Badge: *Apresiasi & Rekomendasi*) | Pujian, review puas, atau saran positif yang membangun |
| **`Kritik & Saran Negatif`** | `DELIVERED_TO_DASHBOARD` | ✅ Ditampilkan (Badge: *Perlu Perhatian / Evaluasi*) | Keluhan/komplain konstruktif santun tanpa bahasa kasar |
| **`Comment aneh-aneh (komentar yang berbahasa kasar)`** | `AUTO_REMOVED` | ❌ Otomatis Dihapus (Tidak masuk dashboard) | Mengandung kata kotor, makian kasar, sensor leetspeak, ujaran kebencian |

---

### 1. Klasifikasi Komentar Tunggal (Real-time Submission)
> **Gunakan pada:** Form submit ulasan / review pembeli saat selesai transaksi.

* **Method:** `POST`
* **URL:** `/comments/classify`
* **Request Body:**
```json
{
  "comment_text": "Makanannya enak banget kak, porsinya pas dan packingnya rapi!",
  "comment_id": "cmt-101",
  "tenant_id": "tenant-7",
  "rating": 5.0
}
```

* **Response `200 OK` (Contoh Positif):**
```json
{
  "comment_id": "cmt-101",
  "tenant_id": "tenant-7",
  "original_text": "Makanannya enak banget kak, porsinya pas dan packingnya rapi!",
  "cleaned_text": "makanannya enak banget kak porsinya pas dan kemasannya rapi",
  "category": "Kritik & Saran Positif",
  "action": "DELIVERED_TO_DASHBOARD",
  "is_delivered_to_dashboard": true,
  "confidence_score": 0.94,
  "sentiment": "POSITIVE",
  "aspects": [
    "Rasa & Kualitas",
    "Porsi & Takaran",
    "Kemasan & Kebersihan"
  ],
  "flagged_words": [],
  "moderation_reason": "Komentar berupa feedback apresiasi atau saran positif yang membangun. Diteruskan ke dashboard toko.",
  "dashboard_badge": "Apresiasi & Rekomendasi"
}
```

* **Response `200 OK` (Contoh Komentar Kasar / Terblokir):**
```json
{
  "comment_id": "cmt-102",
  "tenant_id": "tenant-7",
  "original_text": "Woy babi lu jualan makanan basi anjing!",
  "cleaned_text": "woy babi kamu jualan makanan basi anjing",
  "category": "Comment aneh-aneh (komentar yang berbahasa kasar)",
  "action": "AUTO_REMOVED",
  "is_delivered_to_dashboard": false,
  "confidence_score": 0.98,
  "sentiment": "TOXIC",
  "aspects": [
    "Rasa & Kualitas"
  ],
  "flagged_words": [
    "babi",
    "anjing"
  ],
  "moderation_reason": "Terdeteksi kata-kata kasar / makian: babi, anjing. Sesuai aturan moderasi, komentar otomatis di-remove.",
  "dashboard_badge": "DIBLOKIR / REMOVED"
}
```

---

### 2. Batch Moderasi Komentar
> **Gunakan pada:** Background sync, import review lama, atau moderasi berkala.

* **Method:** `POST`
* **URL:** `/comments/moderate-batch`
* **Request Body:**
```json
{
  "comments": [
    {
      "comment_id": "c-1",
      "tenant_id": "tenant-1",
      "comment_text": "Kopinya mantap, packaging rapi!",
      "rating": 5.0
    },
    {
      "comment_id": "c-2",
      "tenant_id": "tenant-1",
      "comment_text": "Pesanan sampai 1 jam kuahnya tumpah",
      "rating": 2.0
    },
    {
      "comment_id": "c-3",
      "tenant_id": "tenant-1",
      "comment_text": "Penjual t0l0l makanan ga jelas",
      "rating": 1.0
    }
  ]
}
```

* **Response `200 OK`:**
```json
{
  "total_processed": 3,
  "total_delivered_to_dashboard": 2,
  "total_auto_removed": 1,
  "summary_by_category": {
    "Kritik & Saran Positif": 1,
    "Kritik & Saran Negatif": 1,
    "Comment aneh-aneh (komentar yang berbahasa kasar)": 1
  },
  "delivered_comments": [ ... ],
  "removed_comments": [ ... ],
  "all_results": [ ... ]
}
```

---

### 3. Metadata Parameter Klasifikasi
> **Gunakan pada:** Dropdown filter atau tooltip info di dashboard seller.

* **Method:** `GET`
* **URL:** `/comments/categories`
