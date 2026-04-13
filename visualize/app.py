"""
Vector Database Visualizer — Flask API
=======================================
Query LangChain pgvector embeddings from PostgreSQL,
perform dimensionality reduction (t-SNE / PCA),
and serve an interactive 3D visualization page.

Usage:
    cd visualize && pip install -r requirements.txt && python app.py
"""

import json
import os

import numpy as np
import psycopg2
import psycopg2.extras
from flask import Flask, jsonify, render_template, request
from sklearn.cluster import DBSCAN
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.metrics.pairwise import cosine_similarity

# ── Config ────────────────────────────────────────────────────
DB_DSN = os.getenv(
    "DB_CONNECTION",
    "postgresql",
)
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 5001))

app = Flask(__name__)


# ── Helpers ───────────────────────────────────────────────────
def get_conn():
    """Return a new psycopg2 connection."""
    return psycopg2.connect(DB_DSN)


def _parse_vector(raw: str) -> list[float]:
    """Parse a pgvector string '[0.1,0.2,...]' into a list of floats."""
    if isinstance(raw, (list, np.ndarray)):
        return list(raw)
    if isinstance(raw, str):
        raw = raw.strip("[] ")
        return [float(x) for x in raw.split(",") if x.strip()]
    return []


# ── Routes ────────────────────────────────────────────────────
@app.route("/")
def index():
    """Serve the main visualization page."""
    return render_template("index.html")


@app.route("/api/collections")
def api_collections():
    """List all vector collections with counts."""
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    c.uuid,
                    c.name,
                    c.cmetadata,
                    COUNT(e.id) AS embedding_count
                FROM langchain_pg_collection c
                LEFT JOIN langchain_pg_embedding e ON e.collection_id = c.uuid
                GROUP BY c.uuid, c.name, c.cmetadata
                ORDER BY c.name
            """)
            rows = cur.fetchall()
            # Serialize uuid
            for r in rows:
                r["uuid"] = str(r["uuid"])
                r["embedding_count"] = int(r["embedding_count"])
                if r["cmetadata"] and isinstance(r["cmetadata"], str):
                    r["cmetadata"] = json.loads(r["cmetadata"])
        return jsonify(rows)
    finally:
        conn.close()


@app.route("/api/embeddings")
def api_embeddings():
    """
    Fetch embeddings for given collections, reduce to 3D.

    Query params:
        collections  — comma-separated collection names (empty = all)
        limit        — max embeddings to return (default 500)
        method       — 'tsne' (default) or 'pca'
    """
    collections = request.args.get("collections", "")
    limit = min(int(request.args.get("limit", 500)), 2000)
    method = request.args.get("method", "tsne").lower()

    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if collections:
                names = [n.strip() for n in collections.split(",") if n.strip()]
                placeholders = ",".join(["%s"] * len(names))
                cur.execute(
                    f"""
                    SELECT
                        e.id,
                        e.embedding::text AS embedding,
                        e.document,
                        e.cmetadata,
                        c.name AS collection_name
                    FROM langchain_pg_embedding e
                    JOIN langchain_pg_collection c ON c.uuid = e.collection_id
                    WHERE c.name IN ({placeholders})
                    LIMIT %s
                    """,
                    (*names, limit),
                )
            else:
                cur.execute(
                    """
                    SELECT
                        e.id,
                        e.embedding::text AS embedding,
                        e.document,
                        e.cmetadata,
                        c.name AS collection_name
                    FROM langchain_pg_embedding e
                    JOIN langchain_pg_collection c ON c.uuid = e.collection_id
                    LIMIT %s
                    """,
                    (limit,),
                )
            rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        return jsonify({"points": [], "stats": {"total": 0}})

    # Parse vectors
    vectors = []
    meta = []
    for r in rows:
        vec = _parse_vector(r["embedding"])
        if not vec:
            continue
        vectors.append(vec)
        snippet = (r["document"] or "")[:200]
        cmetadata = r["cmetadata"]
        if isinstance(cmetadata, str):
            cmetadata = json.loads(cmetadata)
        meta.append(
            {
                "id": r["id"],
                "collection": r["collection_name"],
                "snippet": snippet,
                "metadata": cmetadata,
            }
        )

    if not vectors:
        return jsonify({"points": [], "stats": {"total": 0}})

    X = np.array(vectors, dtype=np.float32)
    dim = X.shape[1]

    # Dimensionality reduction → 3D
    n = X.shape[0]
    if n < 4:
        # Too few points for t-SNE — use simple PCA or pad
        if dim >= 3:
            coords = X[:, :3]
        else:
            coords = np.zeros((n, 3), dtype=np.float32)
            coords[:, :dim] = X
    elif method == "pca" or n < 30:
        pca = PCA(n_components=3)
        coords = pca.fit_transform(X)
    else:
        perplexity = min(30, n - 1)
        tsne = TSNE(
            n_components=3,
            perplexity=perplexity,
            random_state=42,
            n_iter=800,
            init="pca",
            learning_rate="auto",
        )
        coords = tsne.fit_transform(X)

    # Build response
    points = []
    for i, m in enumerate(meta):
        points.append(
            {
                "id": m["id"],
                "x": float(coords[i][0]),
                "y": float(coords[i][1]),
                "z": float(coords[i][2]),
                "collection": m["collection"],
                "snippet": m["snippet"],
                "metadata": m["metadata"],
            }
        )

    return jsonify(
        {
            "points": points,
            "stats": {
                "total": len(points),
                "original_dim": dim,
                "method": method if n >= 30 else "pca",
            },
        }
    )


@app.route("/api/similarity")
def api_similarity():
    """
    Find top-K most similar embeddings to a given embedding ID.

    Query params:
        id     — embedding ID
        top_k  — number of neighbours to return (default 10)
    """
    emb_id = request.args.get("id", "")
    top_k = min(int(request.args.get("top_k", 10)), 50)

    if not emb_id:
        return jsonify({"error": "Missing 'id' parameter"}), 400

    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Get the target embedding
            cur.execute(
                """
                SELECT e.embedding::text AS embedding
                FROM langchain_pg_embedding e
                WHERE e.id = %s
                """,
                (emb_id,),
            )
            target_row = cur.fetchone()
            if not target_row:
                return jsonify({"error": "Embedding not found"}), 404

            # Use pgvector cosine distance operator to find neighbours
            cur.execute(
                """
                SELECT
                    e.id,
                    e.document,
                    e.cmetadata,
                    c.name AS collection_name,
                    (e.embedding <=> (
                        SELECT embedding FROM langchain_pg_embedding WHERE id = %s
                    )) AS distance
                FROM langchain_pg_embedding e
                JOIN langchain_pg_collection c ON c.uuid = e.collection_id
                WHERE e.id != %s
                ORDER BY distance ASC
                LIMIT %s
                """,
                (emb_id, emb_id, top_k),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    neighbours = []
    for r in rows:
        cmetadata = r["cmetadata"]
        if isinstance(cmetadata, str):
            cmetadata = json.loads(cmetadata)
        neighbours.append(
            {
                "id": r["id"],
                "collection": r["collection_name"],
                "snippet": (r["document"] or "")[:200],
                "metadata": cmetadata,
                "distance": round(float(r["distance"]), 6),
                "similarity": round(1 - float(r["distance"]), 6),
            }
        )

    return jsonify({"source_id": emb_id, "neighbours": neighbours})


# ── Main ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"🚀 Vector Visualizer running at http://localhost:{PORT}")
    app.run(host=HOST, port=PORT, debug=True)
