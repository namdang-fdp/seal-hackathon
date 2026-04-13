import json
import os
from neo4j import GraphDatabase

# =======================================================
# Kịch bản đổ dữ liệu Graph JSON vào cơ sở dữ liệu Neo4j
# Yêu cầu cài đặt driver: pip install neo4j
# =======================================================

# Đổi thông tin thành Username/Password của Database Neo4j của bạn
# (Nếu chạy Neo4j Docker mặc định thì pass là 'neo4j' hoặc 'test')
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "password")


def import_graph_to_neo4j():
    file_path = "./graph.json"

    if not os.path.exists(file_path):
        print(f"❌ Không tìm thấy file: {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    print(
        f"🔥 Sẵn sàng nạp {len(nodes)} Nút (Nodes) và {len(edges)} Cạnh (Edges) vào Neo4j..."
    )

    try:
        with GraphDatabase.driver(URI, auth=AUTH) as driver:
            with driver.session() as session:
                # -------------------------
                # 1. Đẩy các Nodes vào Neo4j
                # -------------------------
                created_nodes = 0
                for node in nodes:
                    node_id = node["id"]
                    node_type = node.get("type", "Mặc_định")

                    # Dùng MERGE để nạp Node mà không sợ bị trùng (Upsert)
                    query = f"MERGE (n:`{node_type}` {{id: $id}})"
                    session.run(query, parameters={"id": node_id})
                    created_nodes += 1

                print(f"✅ Nạp thành công {created_nodes} Mạng lưới Nút (Nodes)!")

                # -------------------------
                # 2. Đẩy các Edges (Mối quan hệ)
                # -------------------------
                created_edges = 0
                for edge in edges:
                    source = edge["source"]
                    target = edge["target"]
                    relation = edge.get("relation", "LIÊN_KẾT")

                    # Tìm 2 Node có sẵn và kéo 1 đường quan hệ (Mũi tên) nối tụi nó
                    query = f"""
                    MATCH (a {{id: $source}})
                    MATCH (b {{id: $target}})
                    MERGE (a)-[r:`{relation}`]->(b)
                    """
                    session.run(query, parameters={"source": source, "target": target})
                    created_edges += 1

                print(f"✅ Đã dệt xong {created_edges} Dây liên kết (Edges)!")
                print(
                    "🎉 HOÀN TẤT! Hãy mở màn hình Neo4j Browser để tận hưởng thành quả."
                )

    except Exception as e:
        print(f"🚨 Gặp lỗi khi cố kết nối tới Neo4j: {e}")
        print(
            "💡 Gợi ý: Kiểm tra xem đã bật ứng dụng Neo4j Desktop/Docker chưa? Pass đúng chưa?"
        )


if __name__ == "__main__":
    import_graph_to_neo4j()
