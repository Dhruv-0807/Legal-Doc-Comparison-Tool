"""Semantic similarity backend for clause matching — swappable, with fallback.

This is the "embeddings" guardrail we agreed on. The alignment logic never sees
which backend is used; it just asks for a similarity matrix. Preference order:

  1. sentence-transformers embeddings  -- best at paraphrase / heavy rewording
  2. scikit-learn TF-IDF cosine         -- lightweight, lexical, no torch
  3. None                               -- semantic tier disabled; fuzzy+exact only

So if torch won't install (e.g. on a very new Python), we silently drop to TF-IDF
and the tool still runs. `active_backend()` reports which one is live.
"""

from __future__ import annotations

import functools


@functools.lru_cache(maxsize=1)
def active_backend() -> str:
    """Return 'sentence-transformers', 'tfidf', or 'none' — whichever is available."""
    try:
        import sentence_transformers  # noqa: F401

        return "sentence-transformers"
    except Exception:
        pass
    try:
        import sklearn  # noqa: F401

        return "tfidf"
    except Exception:
        return "none"


@functools.lru_cache(maxsize=2)
def _st_model(model_name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def similarity_matrix(
    a_texts: tuple[str, ...], b_texts: tuple[str, ...], model_name: str
) -> list[list[float]] | None:
    """Cosine similarity between every A text and every B text, in [0, 1].

    Returns None if no semantic backend is available (caller then relies on
    exact + fuzzy matching only). Inputs are tuples so results can be cached.
    """
    backend = active_backend()
    if not a_texts or not b_texts or backend == "none":
        return None

    if backend == "sentence-transformers":
        return _st_matrix(a_texts, b_texts, model_name)
    return _tfidf_matrix(a_texts, b_texts)


def _st_matrix(a_texts, b_texts, model_name) -> list[list[float]]:
    import numpy as np
    from sentence_transformers import util

    model = _st_model(model_name)
    emb_a = model.encode(list(a_texts), convert_to_numpy=True, normalize_embeddings=True)
    emb_b = model.encode(list(b_texts), convert_to_numpy=True, normalize_embeddings=True)
    sims = util.cos_sim(emb_a, emb_b)  # (len_a, len_b)
    return np.clip(np.asarray(sims), 0.0, 1.0).tolist()


def _tfidf_matrix(a_texts, b_texts) -> list[list[float]]:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    # Fit one vocabulary over BOTH documents so the vectors are comparable.
    corpus = list(a_texts) + list(b_texts)
    vec = TfidfVectorizer(stop_words="english").fit(corpus)
    mat_a = vec.transform(a_texts)
    mat_b = vec.transform(b_texts)
    return cosine_similarity(mat_a, mat_b).tolist()
