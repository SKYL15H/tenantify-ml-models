import os

# Disable Gradio's Node SSR proxy so it does not bind port 7860 before Uvicorn starts.
os.environ["GRADIO_SSR_MODE"] = "false"

try:
    import spaces
except ImportError:
    class _FallbackSpaces:
        """No-op fallback when running outside Hugging Face ZeroGPU."""

        @staticmethod
        def GPU(fn=None, **_kwargs):
            if fn is None:
                return lambda func: func
            return fn

    spaces = _FallbackSpaces()

import gradio as gr
import numpy as np
import uvicorn

from main import (
    app as fastapi_app,
    comment_moderator,
    embedder,
    products,
    recommender,
)

_PRODUCT_BY_ID = {p.id: p for p in products}
_PRODUCT_INDEX_BY_ID = {p.id: idx for idx, p in enumerate(products)}
_PRODUCT_CHOICES = [
    (f"{p.name} ({p.category} — {p.tenantName})", p.id) for p in products
]
_PRODUCT_LABEL_TO_ID = {label: pid for label, pid in _PRODUCT_CHOICES}

_PAIRING_CONNECTORS = {
    "pendamping",
    "pendampingnya",
    "pelengkap",
    "pelengkapnya",
    "pasangan",
    "pasangannya",
    "temen",
    "temennya",
    "teman",
    "temannya",
}
_ANCHOR_FILLER_WORDS = {
    "rekomendasi",
    "cari",
    "carikan",
    "apa",
    "aja",
    "saja",
    "ya",
    "yang",
    "enak",
    "cocok",
    "buat",
    "untuk",
    "sama",
    "ama",
    "dengan",
    "makan",
    "minum",
}
_WANT_GENERIC_WORDS = _ANCHOR_FILLER_WORDS | {"makanan", "menu", "item", "produk"}


def _is_zero_gpu_enabled() -> bool:
    """Return True only when Hugging Face ZeroGPU runtime is explicitly active."""
    if hasattr(spaces, "GPU") and not isinstance(spaces, _FallbackSpaces):
        return True
    config_mod = getattr(spaces, "config", None)
    config_cls = getattr(config_mod, "Config", None)
    if getattr(config_cls, "zero_gpu", False):
        return True
    return os.environ.get("SPACES_ZERO_GPU", "").strip().lower() in {"1", "true", "yes"}


USE_ZERO_GPU = _is_zero_gpu_enabled()


def _clean_tokens(tokens: list[str], stop_words: set[str]) -> str:
    """Filter filler words and strip punctuation from tokens into a clean phrase."""
    cleaned = []
    for tok in tokens:
        word = tok.strip(".,!?;:\"'()[]{}")
        if word and word.lower() not in stop_words:
            cleaned.append(word)
    return " ".join(cleaned)


def _extract_pairing_parts(query: str) -> tuple[str, str, bool] | None:
    """Parse pairing queries into (anchor_query, specific_want, drink_only)."""
    tokens = query.split()
    split_idx = next(
        (
            i
            for i, tok in enumerate(tokens)
            if tok.strip(".,!?;:\"'()[]{}").lower() in _PAIRING_CONNECTORS
        ),
        None,
    )
    if split_idx is None:
        return None

    left_tokens, right_tokens = tokens[:split_idx], tokens[split_idx + 1 :]
    right_anchor = _clean_tokens(right_tokens, _ANCHOR_FILLER_WORDS)
    left_anchor = _clean_tokens(left_tokens, _ANCHOR_FILLER_WORDS)

    if right_anchor:
        anchor_text, want_tokens = right_anchor, left_tokens
    elif left_anchor:
        anchor_text, want_tokens = left_anchor, []
    else:
        return None

    specific_want = _clean_tokens(want_tokens, _WANT_GENERIC_WORDS)
    drink_only = any(
        tok.strip(".,!?;:\"'()[]{}").lower() == "minuman" for tok in want_tokens
    )
    return anchor_text, specific_want, drink_only


def _format_semantic_matches(scores: np.ndarray, limit: int) -> str:
    """Format top-k pure semantic search results into Markdown."""
    ranked_indices = np.argsort(scores)[::-1][:limit]
    lines = []
    for rank, idx in enumerate(ranked_indices, start=1):
        product = products[int(idx)]
        score_pct = int(np.clip(scores[int(idx)], 0.0, 1.0) * 100)
        lines.append(
            f"**{rank}. {product.name}** ({product.category} — {product.tenantName})  \n"
            f"Harga: Rp{product.price:,} | Skor semantik: {score_pct}%"
        )
    return "\n\n".join(lines)


def _format_hybrid_recommendations(
    results,
    limit: int,
    want_scores: np.ndarray | None = None,
) -> str:
    """Format hybrid RecommendationResult items with optional preference re-ranking."""
    scored_items = []
    for rec in results:
        final_score = rec.hybrid_score
        if want_scores is not None:
            p_idx = _PRODUCT_INDEX_BY_ID.get(rec.product.id)
            if p_idx is not None:
                want_sim = float(np.clip(want_scores[p_idx], 0.0, 1.0))
                final_score = 0.65 * rec.hybrid_score + 0.35 * want_sim
        scored_items.append((final_score, rec))

    if want_scores is not None:
        scored_items.sort(key=lambda item: item[0], reverse=True)

    lines = []
    for rank, (final_score, rec) in enumerate(scored_items[:limit], start=1):
        product = rec.product
        lines.append(
            f"**{rank}. {product.name}** ({product.category} — {product.tenantName})  \n"
            f"Harga: Rp{product.price:,} | Skor cocok: {int(round(final_score * 100))}% "
            f"(komplementer {int(round(rec.complementary_score * 100))}%, "
            f"semantik {int(round(rec.semantic_score * 100))}%)  \n"
            f"Alasan: {rec.reason}"
        )
    return "\n\n".join(lines)


def _run_pairing_recommendation(
    anchor_text: str,
    specific_want: str,
    drink_only: bool,
    limit: int,
) -> str | None:
    """Resolve an anchor product from text and recommend complementary pairings."""
    anchor_scores = embedder.get_similarities_from_vector(embedder.encode([anchor_text])[0])
    if len(anchor_scores) == 0:
        return None
    best_idx = int(np.argmax(anchor_scores))
    if float(anchor_scores[best_idx]) < 0.30:
        return None

    anchor_product = products[best_idx]
    category_filter = "Minuman" if drink_only else None
    fetch_n = len(products) if specific_want else limit
    recs = recommender.recommend(
        anchor_product.id,
        top_n=fetch_n,
        exclude_same_tenant=False,
        category_filter=category_filter,
    )
    if not recs and category_filter is not None:
        recs = recommender.recommend(
            anchor_product.id,
            top_n=fetch_n,
            exclude_same_tenant=False,
        )
    if not recs:
        return None

    want_scores = (
        embedder.get_similarities_from_vector(embedder.encode([specific_want])[0])
        if specific_want
        else None
    )
    header = (
        f"_Menampilkan pendamping untuk **{anchor_product.name}** "
        f"({anchor_product.category} — {anchor_product.tenantName})_\n\n"
    )
    return header + _format_hybrid_recommendations(recs, limit=limit, want_scores=want_scores)


def _run_semantic_search(query: str, top_n: int = 5, use_cuda: bool = False) -> str:
    """Encode the query and rank matching or complementary products from FAISS."""
    if not products:
        return "Katalog produk kosong."
    if use_cuda:
        import torch

        if torch.cuda.is_available():
            embedder.model.to("cuda")

    limit = max(1, min(int(top_n), len(products)))
    pairing_parts = _extract_pairing_parts(query)
    if pairing_parts is not None:
        anchor_text, specific_want, drink_only = pairing_parts
        pairing_output = _run_pairing_recommendation(anchor_text, specific_want, drink_only, limit)
        if pairing_output is not None:
            return pairing_output

    query_vec = embedder.encode([query])[0]
    scores = embedder.get_similarities_from_vector(query_vec)
    return _format_semantic_matches(scores, limit)


if USE_ZERO_GPU:
    @spaces.GPU
    def _run_semantic_search_gpu(query: str, top_n: int = 5) -> str:
        """Run semantic search inside a Hugging Face ZeroGPU worker."""
        return _run_semantic_search(query, top_n, use_cuda=True)
else:
    _run_semantic_search_gpu = None


def semantic_product_search(query: str, top_n: int = 5) -> str:
    """Run semantic search with ZeroGPU when available and CPU fallback otherwise."""
    if not query or not query.strip():
        return "Masukkan kata kunci pencarian (contoh: `minuman dingin buat temen gorengan`)."

    cleaned_query = query.strip()
    limit = int(top_n)
    if _run_semantic_search_gpu is not None:
        try:
            return _run_semantic_search_gpu(cleaned_query, limit)
        except Exception as exc:
            print(
                f"⚠️ ZeroGPU inference failed ({exc!r}); falling back to CPU.",
                flush=True,
            )

    return _run_semantic_search(cleaned_query, limit, use_cuda=False)


def moderate_comment_demo(comment: str) -> str:
    """Classify and moderate a buyer comment via the NLU moderator."""
    res = comment_moderator.classify_comment(comment or "")
    aspects = ", ".join(res["aspects"]) if res["aspects"] else "-"
    flagged = ", ".join(res["flagged_words"]) if res["flagged_words"] else "-"
    return (
        f"**Kategori:** {res['category']}  \n"
        f"**Action:** `{res['action']}` | **Sentimen:** `{res['sentiment']}`  \n"
        f"**Aspek:** {aspects} | **Kata Terdeteksi:** {flagged}  \n"
        f"**Alasan:** {res['moderation_reason']}"
    )


def recommend_product_hybrid(
    product_selection: str,
    top_n: int = 5,
    exclude_same_tenant: bool = False,
) -> str:
    """Recommend complementary products using the hybrid recommender."""
    if not product_selection:
        return "Pilih produk acuan terlebih dahulu."

    product_id = (
        product_selection
        if product_selection in _PRODUCT_BY_ID
        else _PRODUCT_LABEL_TO_ID.get(product_selection, "")
    )
    anchor = _PRODUCT_BY_ID.get(product_id)
    if anchor is None:
        return f"Produk `{product_selection}` tidak ditemukan."

    limit = max(1, min(int(top_n), len(products)))
    results = recommender.recommend(
        product_id=anchor.id,
        top_n=limit,
        exclude_same_tenant=bool(exclude_same_tenant),
    )
    if not results:
        return "Tidak ada rekomendasi yang memenuhi filter saat ini."

    header = (
        f"_Rekomendasi pendamping untuk **{anchor.name}** "
        f"({anchor.category} — {anchor.tenantName})_\n\n"
    )
    return header + _format_hybrid_recommendations(results, limit=limit)


with gr.Blocks() as demo:
    gr.Markdown(
        "# Tenantify AI — Recommendation & NLU Moderation Backend\n"
        "Dokumentasi REST API lengkap tersedia di **[Swagger UI (/docs)](/docs)** "
        "dan status layanan di **[/health](/health)**."
    )

    with gr.Tab("Semantic Product Search (ZeroGPU)"):
        query_input = gr.Textbox(
            label="Cari Produk / Kebutuhan",
            placeholder="Contoh: minuman dingin pendamping gorengan",
        )
        top_n_slider = gr.Slider(
            minimum=1,
            maximum=10,
            value=5,
            step=1,
            label="Jumlah Rekomendasi",
        )
        search_btn = gr.Button("Cari Rekomendasi", variant="primary")
        search_output = gr.Markdown()
        search_btn.click(
            fn=semantic_product_search,
            inputs=[query_input, top_n_slider],
            outputs=search_output,
        )

    with gr.Tab("Rekomendasi Produk (Hybrid)"):
        product_dropdown = gr.Dropdown(
            choices=_PRODUCT_CHOICES,
            value=products[0].id if products else None,
            label="Pilih Produk Acuan",
        )
        hybrid_top_n_slider = gr.Slider(
            minimum=1,
            maximum=10,
            value=5,
            step=1,
            label="Jumlah Rekomendasi",
        )
        exclude_same_tenant_chk = gr.Checkbox(
            value=False,
            label="Hanya rekomendasikan dari tenant lain (pemerataan UMKM)",
        )
        hybrid_btn = gr.Button("Lihat Rekomendasi Pendamping", variant="primary")
        hybrid_output = gr.Markdown()
        hybrid_btn.click(
            fn=recommend_product_hybrid,
            inputs=[product_dropdown, hybrid_top_n_slider, exclude_same_tenant_chk],
            outputs=hybrid_output,
        )

    with gr.Tab("Comment NLU Moderation"):
        comment_input = gr.Textbox(
            label="Komentar Pembeli",
            placeholder="Contoh: Makanannya enak banget, porsinya pas!",
        )
        moderate_btn = gr.Button("Cek Moderasi", variant="primary")
        moderate_output = gr.Markdown()
        moderate_btn.click(
            fn=moderate_comment_demo,
            inputs=comment_input,
            outputs=moderate_output,
        )


# Let Gradio serve "/" while keeping FastAPI routes (/docs, /health, /recommend/*, /comments/*) active.
fastapi_app.router.routes = [
    route
    for route in fastapi_app.router.routes
    if getattr(route, "path", None) != "/"
]

app = gr.mount_gradio_app(fastapi_app, demo, path="/", ssr_mode=False)


if __name__ == "__main__":
    if USE_ZERO_GPU:
        zero_mod = getattr(spaces, "zero", None)
        if zero_mod is not None and hasattr(zero_mod, "startup"):
            try:
                zero_mod.startup()
            except Exception as exc:
                print(f"⚠️ ZeroGPU startup skipped: {exc!r}", flush=True)

    port = int(os.environ.get("GRADIO_SERVER_PORT") or os.environ.get("PORT") or 7860)
    print(f"🚀 Menjalankan Tenantify AI (Gradio + FastAPI) di port {port}...", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=port)
