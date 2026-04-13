"""
Database probe script — Inspect table schemas, vector dimensions, and sample data.
"""

import psycopg2
import psycopg2.extras


def main():
    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # 1. List all tables
    print("=" * 60)
    print("1. ALL TABLES IN DATABASE")
    print("=" * 60)
    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' ORDER BY table_name
    """)
    for row in cur.fetchall():
        print(f"  - {row['table_name']}")

    # 2. Schema for SQL tables
    for tbl in ["nhat_ky_dong_goi_lai", "theo_doi_giao_noi_dia"]:
        print(f"\n{'=' * 60}")
        print(f"2. SCHEMA: {tbl}")
        print(f"{'=' * 60}")
        cur.execute(f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = '{tbl}' ORDER BY ordinal_position
        """)
        for row in cur.fetchall():
            print(
                f"  {row['column_name']:30s} {row['data_type']:20s} nullable={row['is_nullable']}"
            )
        cur.execute(f"SELECT COUNT(*) as cnt FROM {tbl}")
        print(f"  → Total rows: {cur.fetchone()['cnt']}")

    # 3. Vector collections
    print(f"\n{'=' * 60}")
    print("3. LANGCHAIN COLLECTIONS")
    print(f"{'=' * 60}")
    cur.execute("SELECT uuid, name, cmetadata FROM langchain_pg_collection")
    collections = cur.fetchall()
    for c in collections:
        print(f"  Collection: {c['name']} (uuid={c['uuid']})")
        print(f"    Metadata: {c['cmetadata']}")

    # 4. Embedding table schema
    print(f"\n{'=' * 60}")
    print("4. SCHEMA: langchain_pg_embedding")
    print(f"{'=' * 60}")
    cur.execute("""
        SELECT column_name, data_type, udt_name
        FROM information_schema.columns
        WHERE table_name = 'langchain_pg_embedding' ORDER BY ordinal_position
    """)
    for row in cur.fetchall():
        print(
            f"  {row['column_name']:30s} {row['data_type']:20s} udt={row['udt_name']}"
        )

    # 5. Vector dimension — get one embedding and check length
    print(f"\n{'=' * 60}")
    print("5. VECTOR DIMENSION CHECK")
    print(f"{'=' * 60}")
    cur.execute("SELECT embedding::text FROM langchain_pg_embedding LIMIT 1")
    row = cur.fetchone()
    if row:
        vec_str = row["embedding"].strip("[]")
        dim = len(vec_str.split(","))
        print(f"  Vector dimension: {dim}")
    else:
        print("  No embeddings found!")

    # 6. Sample embedding metadata
    print(f"\n{'=' * 60}")
    print("6. SAMPLE EMBEDDINGS (3 rows)")
    print(f"{'=' * 60}")
    cur.execute("""
        SELECT e.id, e.document, e.cmetadata, c.name as collection_name
        FROM langchain_pg_embedding e
        JOIN langchain_pg_collection c ON c.uuid = e.collection_id
        LIMIT 3
    """)
    for row in cur.fetchall():
        print(f"  ID: {row['id']}")
        print(f"  Collection: {row['collection_name']}")
        print(f"  Document (first 300 chars): {(row['document'] or '')[:300]}")
        print(f"  Metadata: {row['cmetadata']}")
        print()

    # 7. Embedding count per collection
    print(f"{'=' * 60}")
    print("7. EMBEDDING COUNT PER COLLECTION")
    print(f"{'=' * 60}")
    cur.execute("""
        SELECT c.name, COUNT(e.id) as cnt
        FROM langchain_pg_collection c
        LEFT JOIN langchain_pg_embedding e ON e.collection_id = c.uuid
        GROUP BY c.name ORDER BY c.name
    """)
    for row in cur.fetchall():
        print(f"  {row['name']}: {row['cnt']} embeddings")

    # 8. Sample SQL data
    for tbl in ["nhat_ky_dong_goi_lai", "theo_doi_giao_noi_dia"]:
        print(f"\n{'=' * 60}")
        print(f"8. SAMPLE DATA: {tbl} (2 rows)")
        print(f"{'=' * 60}")
        cur.execute(f"SELECT * FROM {tbl} LIMIT 2")
        for row in cur.fetchall():
            for k, v in row.items():
                print(f"  {k}: {v}")
            print()

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
