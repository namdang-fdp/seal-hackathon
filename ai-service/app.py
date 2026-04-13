"""
RAGNAROK — Multi-Agent RAG System (v2 — Hybrid Query)
=======================================================
Streamlit app powered by LangGraph.
4 routes: SQL | Vector | Graph | Hybrid (Vector+Graph)
Nodes: Semantic Router → Retriever(s) → Calculator? → Generator → Grader
Retry strategy: synonym rewrite → LLM rewrite → fallback.

Usage:
    cd ai-service && source venv/bin/activate && streamlit run app.py
"""

import os
import re
import ast
import json
import math
from typing import TypedDict

import streamlit as st
from dotenv import load_dotenv

# ── LangGraph ─────────────────────────────────────────────────
from langgraph.graph import StateGraph, END

# ── LangChain ─────────────────────────────────────────────────
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# ── Sentence-Transformers (SBERT Router) ──────────────────────
from sentence_transformers import SentenceTransformer, util

# ── Database ──────────────────────────────────────────────────
from sqlalchemy import create_engine, text as sa_text
import psycopg2
import psycopg2.extras

load_dotenv()

# =============================================================
# CONFIG
# =============================================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Graph JSON path
GRAPH_JSON_PATH = os.path.join(
    os.path.dirname(__file__), "..", "graph-visualize", "graph.json"
)

# SBERT model — đúng model của team (dùng cho Semantic Router)
SBERT_MODEL_NAME = "keepitreal/vietnamese-sbert"

# Vector retrieval model — khớp với dimension trong DB (384-dim)
VECTOR_EMBED_MODEL_NAME = "all-MiniLM-L6-v2"

# SQL tables
SQL_TABLES = ["nhat_ky_dong_goi_lai", "theo_doi_giao_noi_dia"]

# Vector collections (4 collections in DB)
VECTOR_COLLECTIONS = [
    "luat_vien_thong_kho",  # 162 embeddings — luật, quy định, chính sách
    "phieu_dong_goi_vector",  # 2074 embeddings — phiếu đóng gói, biên bản
    "manifest_chuyen_bay_vector",  # 1275 embeddings — manifest chuyến bay
    "to_khai_hai_quan",  # 273 embeddings — tờ khai hải quan
]

# =============================================================
# SYNONYM MAP — Logistics domain Vietnamese synonyms
# =============================================================
SYNONYM_MAP = {
    "hư hỏng": ["bị hỏng", "tổn thất", "thiệt hại", "hỏng", "damage", "broken"],
    "bị hỏng": ["hư hỏng", "tổn thất", "thiệt hại"],
    "thiệt hại": ["hư hỏng", "bị hỏng", "tổn thất"],
    "đóng gói": ["bao gói", "packing", "đóng kiện", "gói hàng", "đóng hàng"],
    "bao gói": ["đóng gói", "packing", "đóng kiện"],
    "vận chuyển": ["giao hàng", "shipping", "chuyển hàng", "giao nội địa", "ship"],
    "giao hàng": ["vận chuyển", "shipping", "chuyển hàng", "delivery"],
    "kho": ["warehouse", "kho hàng", "kho bãi", "nhà kho"],
    "tracking": ["mã vận đơn", "mã theo dõi", "tracking code", "mã tracking"],
    "mã vận đơn": ["tracking", "tracking code", "mã theo dõi"],
    "kiện hàng": ["kiện", "package", "bưu kiện", "hàng hóa"],
    "bẹp": ["méo", "biến dạng", "dented", "bị bẹp"],
    "ẩm ướt": ["ẩm", "ướt", "ngấm nước", "thấm nước"],
    "vỡ": ["nứt", "bể", "gãy", "broken", "bị vỡ"],
    "phí": ["cước", "chi phí", "giá", "cost", "fee"],
    "nhà vận chuyển": ["carrier", "đơn vị vận chuyển", "hãng vận chuyển"],
    "thông quan": ["customs clearance", "hải quan", "khai báo hải quan"],
    "đơn hàng": ["order", "đơn", "đơn đặt hàng"],
    "trả lại": ["hoàn trả", "return", "trả hàng", "hoàn hàng"],
    "thất bại": ["không thành công", "failed", "lỗi giao hàng"],
}

# Đã loại bỏ CALC_KEYWORDS do dùng LLM semantic understanding

# =============================================================
# SEMANTIC ROUTER — Sample sentences (Team's logic)
# =============================================================
SQL_SAMPLES = [
    "Tổng số đơn giao nội địa trong tháng 12",
    "Số lượng đơn hàng đóng gói lại theo trạng thái",
    "Tổng phí vận chuyển nội địa của khách hàng KH00006",
    "Liệt kê các đơn hàng bị trả lại",
    "Đếm số lần giao hàng thất bại theo tỉnh",
    "Tổng phí đóng gói lại trong quý 4 năm 2024",
    "Thống kê đơn giao theo nhà vận chuyển",
    "Tracking code nào có nhiều lần giao nhất",
    "Chi phí vật liệu đóng gói trung bình",
    "Đơn hàng nào có COD lớn nhất",
    "Số đơn giao thành công theo tháng",
    "Nhân viên đóng gói nào xử lý nhiều đơn nhất",
    "Danh sách đơn hàng giao đến Cần Thơ",
    "Trung bình số lần giao hàng theo nhà vận chuyển",
    "So sánh phí vận chuyển giữa GHN và SPX Express",
]

VECTOR_SAMPLES = [
    "Chính sách vận chuyển đường air tuyến quốc tế",
    "Quy định về hàng cồng kềnh",
    "Bảng giá dịch vụ vận chuyển hàng đông lạnh",
    "Quy ước tính cước phí vận chuyển",
    "Chính sách đóng gói hàng dễ vỡ",
    "Luật hải quan về khai báo hàng hóa",
    "Quy trình thông quan xuất nhập khẩu",
    "Quy định về cân nặng và kích thước kiện hàng",
    "Hướng dẫn đóng gói hàng hóa đặc biệt",
    "Phí lưu kho và thời gian lưu kho tối đa",
    "Quy trình xử lý hàng hóa bị hư hỏng",
    "Chính sách bảo hiểm hàng hóa vận chuyển",
    "Thủ tục khai báo thuế nhập khẩu",
    "Danh mục hàng cấm và hàng hạn chế vận chuyển",
    "Quy định đóng gói hàng nguy hiểm",
]

GRAPH_SAMPLES = [
    "Tracking TRK0003227 chứa sản phẩm gì",
    "Kiện hàng nào bị hư hỏng tại kho Hà Nội",
    "Sản phẩm iPhone bị tình trạng gì",
    "Nguyên nhân hư hỏng của tracking TRK0002796",
    "Đề xuất xử lý cho kiện hàng bị bẹp",
    "Mức độ hư hỏng của bao bì ẩm ướt",
    "Tracking nào xảy ra tại kho Đà Nẵng",
    "Vị trí hư hỏng của kiện TRK0005155",
    "Những sản phẩm nào bị vỡ",
    "Kiện hàng nào cần đóng gói lại ngay",
    "Tình trạng hư hỏng của MacBook Air M3",
    "Liên quan giữa tracking và sản phẩm hư hỏng",
    "Kiện nào bị ẩm ướt xâm nhập",
    "Đơn hàng ORD0002699 liên quan tracking nào",
    "Sản phẩm nào cần khiếu nại bảo hiểm",
]

HYBRID_SAMPLES = [
    "Tracking TRK0003227 bị hư gì và quy định đóng gói lại là gì",
    "Kiện hàng bị bẹp tại kho Hà Nội, chính sách bảo hiểm thế nào",
    "Sản phẩm iPhone bị vỡ, quy trình xử lý hàng hóa hư hỏng ra sao",
    "Tracking bị ẩm ướt ở kho Đà Nẵng, quy định đóng gói hàng dễ vỡ",
    "Kiện hàng nào cần đóng gói lại và hướng dẫn đóng gói đặc biệt",
    "Nguyên nhân hư hỏng MacBook và chính sách bồi thường",
    "Mức độ hư hỏng của kiện hàng và quy trình khiếu nại",
    "Sản phẩm bị tổn thất tại kho và luật hải quan liên quan",
    "Tracking bị hỏng bao bì, cần tìm quy định đóng gói và mối quan hệ sản phẩm",
    "Tình trạng kiện hàng trong graph và quy định xử lý trong tài liệu",
    "Kiện nào bị hư hỏng và quy định bảo hiểm hàng hóa vận chuyển",
    "Đề xuất xử lý kiện bị bẹp và chính sách đóng gói hàng cồng kềnh",
    "Sản phẩm nào cần khiếu nại bảo hiểm và thủ tục khai báo",
    "Tracking xảy ra tại kho nào và phí lưu kho tối đa",
    "Liên quan giữa tracking và sản phẩm, kèm quy định vận chuyển",
]


# =============================================================
# LOAD MODELS (cached)
# =============================================================
@st.cache_resource(show_spinner="🔄 Đang tải model SBERT (vietnamese-sbert)...")
def load_sbert_model():
    """Load sentence-transformers model cho Router — cached across reruns."""
    return SentenceTransformer(SBERT_MODEL_NAME)


@st.cache_resource(show_spinner="🔄 Đang tải model embedding cho Vector Retriever...")
def load_vector_embed_model():
    """Load model 384-dim khớp với vectors trong DB — cached across reruns."""
    return SentenceTransformer(VECTOR_EMBED_MODEL_NAME)


@st.cache_resource(show_spinner="🔄 Đang encode sample sentences...")
def encode_samples(_model):
    """Pre-encode sample sentences for the semantic router (4 groups)."""
    sql_embs = _model.encode(SQL_SAMPLES, convert_to_tensor=True)
    vec_embs = _model.encode(VECTOR_SAMPLES, convert_to_tensor=True)
    graph_embs = _model.encode(GRAPH_SAMPLES, convert_to_tensor=True)
    hybrid_embs = _model.encode(HYBRID_SAMPLES, convert_to_tensor=True)
    return sql_embs, vec_embs, graph_embs, hybrid_embs


@st.cache_resource(show_spinner="🔄 Đang tải Knowledge Graph...")
def load_graph():
    """Load graph.json vào memory."""
    path = os.path.abspath(GRAPH_JSON_PATH)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@st.cache_resource(show_spinner="🔄 Đang encode Graph nodes cho embedding search...")
def encode_graph_nodes(_model):
    """Pre-encode tất cả graph node IDs bằng SBERT để embedding-based search."""
    graph = load_graph()
    nodes = graph.get("nodes", [])
    node_labels = [n["id"].replace("_", " ") for n in nodes]
    node_ids = [n["id"] for n in nodes]
    node_types = [n["type"] for n in nodes]
    embeddings = _model.encode(node_labels, convert_to_tensor=True)
    return node_ids, node_types, embeddings


# =============================================================
# LLM INSTANCES (dùng gemini-2.5-pro)
# =============================================================
@st.cache_resource
def get_rewriter_llm():
    """Rewriter LLM — Gemini, temperature=0."""
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        temperature=0,
        google_api_key=GEMINI_API_KEY,
    )


@st.cache_resource
def get_generator_llm():
    """Generator LLM — Gemini for final answer."""
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        temperature=0.3,
        google_api_key=GEMINI_API_KEY,
    )


@st.cache_resource
def get_grader_llm():
    """Hallucination grader LLM."""
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-pro",
        temperature=0,
        google_api_key=GEMINI_API_KEY,
    )


# =============================================================
# LANGGRAPH STATE (enhanced)
# =============================================================
class AgentState(TypedDict):
    question: str
    rewritten_question: str
    synonym_queries: list  # Danh sách câu hỏi biến thể từ synonym tool
    context: str
    vector_context: str  # Context riêng từ VectorDB
    graph_context: str  # Context riêng từ Graph
    answer: str
    route: str  # "sql" | "vector" | "graph" | "hybrid"
    needs_calculation: bool  # Flag cần tính toán
    calculation_result: str  # Kết quả tính toán
    retry_count: int
    retry_strategy: str  # "synonym" | "llm_rewrite"
    grade: str  # "pass" or "fail"
    logs: list  # Agent thinking logs for UI
    token_usage: dict  # {"input": N, "output": N, "total": N, "calls": N}
    target_collections: list  # Phân loại collection qua semantic LLM


# =============================================================
# HELPER: LLM invoke with token tracking
# =============================================================
def invoke_llm_tracked(
    prompt_template, llm, inputs: dict, state: dict, node_name: str = ""
) -> str:
    """
    Invoke LLM through prompt template, extract token usage from response.
    Returns the text output. Accumulates tokens in state['token_usage'].
    """
    # Execute prompt | llm (without StrOutputParser to get AIMessage)
    chain_raw = prompt_template | llm
    ai_message = chain_raw.invoke(inputs)

    # Extract text
    text = ai_message.content if hasattr(ai_message, "content") else str(ai_message)

    # Extract token usage from Gemini's usage_metadata
    usage = state.get(
        "token_usage", {"input": 0, "output": 0, "total": 0, "calls": 0, "details": []}
    )
    if hasattr(ai_message, "usage_metadata") and ai_message.usage_metadata:
        meta = ai_message.usage_metadata
        input_tokens = getattr(meta, "input_tokens", 0) or 0
        output_tokens = getattr(meta, "output_tokens", 0) or 0
        total = input_tokens + output_tokens
        usage["input"] += input_tokens
        usage["output"] += output_tokens
        usage["total"] += total
        usage["calls"] += 1
        usage["details"].append(
            {
                "node": node_name,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total": total,
            }
        )
    else:
        usage["calls"] += 1
        usage["details"].append(
            {"node": node_name, "input_tokens": 0, "output_tokens": 0, "total": 0}
        )

    state["token_usage"] = usage
    return text


# =============================================================
# HELPER: LLM Intent Analyzer (thay thế keyword-based)
# =============================================================
def analyze_intent(question: str, state: dict) -> dict:
    """
    Sử dụng LLM để dự đoán ý định tính toán và vector collection (Semantic parsing).
    """
    prompt = PromptTemplate.from_template("""
Bạn là hệ thống định tuyến ngữ nghĩa cho mô hình Agent RAG về Logistics và Hải Quan.
Nhiệm vụ: Phân tích ngữ nghĩa câu hỏi. Kết quả trả về CẤU TRÚC JSON DUY NHẤT.

{{
  "needs_calculation": boolean, // true nếu câu trả lời đòi hỏi: tính tỉ lệ, đếm, top n, báo cáo, gom nhóm, so sánh, min/max, %
  "collections": [], // lọc cụ thể collection Vector. Nếu cần tra tất cả, đẻ []
  "recommended_route": "sql" | "vector" | "graph" | "hybrid" | ""
}}

// QUY TẮC ĐỊNH TUYẾN QUAN TRỌNG (recommended_route):
- "sql": ĐẶC BIỆT BẮT BUỘC NẾU câu hỏi mang tính chất TÍNH TOÁN TOÀN CỤC (Top n, đếm tổng, tính tỉ lệ giao hàng, gom nhóm toàn bộ hãng). Sẽ bỏ qua Vector/Graph vì chúng bị thiếu dữ liệu diện rộng.
- "vector": tra lookup tài liệu luật, chính sách, tờ khai.
- "graph": tra cứu sự kiện, liên đới của 1, 2 tracking code cụ thể (TRK...).
- "hybrid": pha trộn giữa tài liệu văn bản và mã tracking.

// Các collections VectorDb hiện có:
- "luat_vien_thong_kho": chứa các file luật, điều kiện, quy định, đóng gói, bảo hiểm, chính sách lưu kho, mức đền bù.
- "to_khai_hai_quan": chứa các dạng tờ khai hải quan, thuế nhập khẩu, chi tiết thủ tục thông quan.
- "phieu_dong_goi_vector": phiếu đóng gói, biên bản kiểm tra, nhật ký đóng gói kiện hàng.
- "manifest_chuyen_bay_vector": manifest chuyến bay (flight), thông tin cargo, vận tải hàng không.

LƯU Ý QUAN TRỌNG:
Chỉ in ra JSON thuần túy, không có giải thích nào thêm. Bỏ qua dấu backticks ```.

CÂU HỎI USER: {question}
KẾT QUẢ JSON:
""")
    llm = get_generator_llm()
    try:
        raw_out = invoke_llm_tracked(
            prompt, llm, {"question": question}, state, "Intent Analyzer"
        )
        cleaned = raw_out.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(cleaned)
        return {
            "needs_calculation": parsed.get("needs_calculation", False),
            "collections": parsed.get("collections", []),
            "recommended_route": parsed.get("recommended_route", ""),
        }
    except Exception as e:
        return {"needs_calculation": False, "collections": [], "recommended_route": ""}


# =============================================================
# NODE 1: SEMANTIC ROUTER (SBERT + Confidence-based hybrid)
# =============================================================
def semantic_router_node(state: AgentState) -> dict:
    """
    Dùng SBERT tính Cosine Similarity giữa câu hỏi và 4 list sample.
    Logic mới:
    - Thêm route 'hybrid' khi cả vector và graph đều cao
    - Confidence-based: nếu max_score < 0.4 → hybrid fallback
    - Detect calculation intent
    """
    model = load_sbert_model()
    sql_embs, vec_embs, graph_embs, hybrid_embs = encode_samples(model)

    q = state.get("rewritten_question") or state["question"]
    q_emb = model.encode(q, convert_to_tensor=True)

    # Cosine Similarity cho 4 nhóm
    sql_scores = util.cos_sim(q_emb, sql_embs)[0]
    vec_scores = util.cos_sim(q_emb, vec_embs)[0]
    graph_scores = util.cos_sim(q_emb, graph_embs)[0]
    hybrid_scores = util.cos_sim(q_emb, hybrid_embs)[0]

    sql_max = float(sql_scores.max())
    vec_max = float(vec_scores.max())
    graph_max = float(graph_scores.max())
    hybrid_max = float(hybrid_scores.max())

    # Chọn route
    scores = {
        "sql": sql_max,
        "vector": vec_max,
        "graph": graph_max,
        "hybrid": hybrid_max,
    }
    route = max(scores, key=scores.get)

    # Confidence-based hybrid fallback
    # Nếu top score quá thấp → hybrid (query all non-SQL sources)
    top_score = scores[route]
    if top_score < 0.4:
        route = "hybrid"

    # Nếu vector và graph đều cao và gần nhau → hybrid
    if route != "hybrid" and route != "sql":
        if vec_max > 0.45 and graph_max > 0.45 and abs(vec_max - graph_max) < 0.08:
            route = "hybrid"

    # ========== DUAL-INTENT DETECTION ==========
    # Nếu câu hỏi chứa CẢ entity/tracking reference VÀ policy/regulation keywords
    # → force hybrid vì cần cả Graph (entity) + Vector (policy)
    if route != "hybrid":
        q_lower = q.lower()
        entity_signals = any(
            [
                bool(re.search(r"TRK\d+", q, re.IGNORECASE)),  # Tracking code
                bool(re.search(r"ORD\d+", q, re.IGNORECASE)),  # Order code
                any(
                    kw in q_lower
                    for kw in [
                        "tracking",
                        "kiện hàng",
                        "lô hàng",
                        "đơn hàng",
                        "sản phẩm",
                        "kho",
                        "bị hư",
                        "bị hỏng",
                        "bị bẹp",
                        "bị vỡ",
                        "bị ẩm",
                    ]
                ),
            ]
        )
        policy_signals = any(
            kw in q_lower
            for kw in [
                "quy định",
                "chính sách",
                "hướng dẫn",
                "quy trình",
                "luật",
                "thủ tục",
                "bảng giá",
                "điều khoản",
                "đóng gói",
                "bảo hiểm",
                "bồi thường",
                "khiếu nại",
                "xử lý",
                "phí",
                "cước",
            ]
        )
        if entity_signals and policy_signals:
            route = "hybrid"

    # ========== LLM INTENT ANALYZER (Semantic Parsing) ==========
    intent_data = analyze_intent(q, state)
    needs_calc = intent_data.get("needs_calculation", False)
    target_collections = intent_data.get("collections", [])
    recommended_route = intent_data.get("recommended_route", "")

    # OVERRIDE SBERT ROUTE BẰNG LLM THÔNG MINH
    if needs_calc and recommended_route == "sql":
        route = "sql"

    logs = state.get("logs", [])
    logs.append(
        f"🧭 **Semantic Router**: SQL={sql_max:.4f} | Vector={vec_max:.4f} | "
        f"Graph={graph_max:.4f} | Hybrid={hybrid_max:.4f} → Route: **{route.upper()}**"
    )
    if needs_calc and recommended_route == "sql":
        logs.append(
            "⚠️ **Route Override**: Đã bẻ lái sang SQL vì nhận diện được câu hỏi Thống kê toàn cục."
        )

    if needs_calc:
        logs.append(
            "🔢 **Smart Calculator**: LLM phát hiện câu hỏi cần thống kê tính toán"
        )
    if target_collections:
        logs.append(f"🔍 **Collections Detected**: {', '.join(target_collections)}")

    return {
        "route": route,
        "needs_calculation": needs_calc,
        "target_collections": target_collections,
        "logs": logs,
    }


# =============================================================
# NODE 2: SQL RETRIEVER
# =============================================================
def sql_retriever_node(state: AgentState) -> dict:
    """
    Dùng LLM generate SQL query rồi chạy trên 2 bảng:
    nhat_ky_dong_goi_lai và theo_doi_giao_noi_dia.
    """
    logs = state.get("logs", [])
    logs.append("🗄️ **SQL Retriever**: Đang tạo và thực thi SQL query...")

    q = state.get("rewritten_question") or state["question"]

    # Get table schemas for the LLM
    engine = create_engine(DB_CONNECTION)

    table_info = ""
    with engine.connect() as conn:
        for tbl in SQL_TABLES:
            result = conn.execute(
                sa_text(
                    f"SELECT column_name, data_type FROM information_schema.columns "
                    f"WHERE table_name = '{tbl}' ORDER BY ordinal_position"
                )
            )
            cols = [f"  - {r[0]} ({r[1]})" for r in result]
            row_count = conn.execute(sa_text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
            table_info += f"\nBảng: {tbl} ({row_count} rows)\n" + "\n".join(cols) + "\n"

    # Ask LLM to generate SQL
    sql_prompt = PromptTemplate.from_template("""
Bạn là chuyên gia SQL cho PostgreSQL. Dựa vào schema dưới đây, hãy viết MỘT câu SQL query
để trả lời câu hỏi của người dùng. CHỈ trả về câu SQL, không giải thích.

LƯU Ý ĐẶC BIỆT THỐNG KÊ (NẾU CÓ):
- Cần Lọc TOP / xếp hạng: Dùng `ORDER BY ... DESC LIMIT X`
- Phân loại / Tính tỉ lệ: Dùng `COUNT(CASE WHEN ... THEN 1 END) * 100.0 / COUNT(*)`
- Gom nhóm theo từng hạng mục: Dùng `GROUP BY ...`
Hãy đảm nhiệm tốt các việc phân tích TÙY VÀO yêu cầu user truyền vào. Cố gắng sinh TẤT CẢ trong 1 câu Query.

SCHEMA:
{table_info}

Lưu ý:
- Chỉ dùng SELECT, KHÔNG dùng INSERT/UPDATE/DELETE
- Dùng LIMIT 20 nếu kết quả có thể nhiều (trừ khi họ cần TOP)
- Nếu câu hỏi không liên quan đến dữ liệu, trả về: SELECT 'Không tìm thấy dữ liệu phù hợp'

Câu hỏi: {question}
SQL:
""")

    llm = get_generator_llm()
    raw_sql = invoke_llm_tracked(
        sql_prompt,
        llm,
        {"table_info": table_info, "question": q},
        state,
        "SQL Generator",
    )

    # Clean SQL
    sql_query = raw_sql.strip().strip("```sql").strip("```").strip()
    logs.append(f"📝 **SQL Query**: `{sql_query[:200]}`")

    # Execute SQL
    try:
        with engine.connect() as conn:
            result = conn.execute(sa_text(sql_query))
            rows = result.fetchall()
            columns = list(result.keys())

            if rows:
                context_lines = [" | ".join(columns)]
                context_lines.append("-" * 50)
                for row in rows[:20]:
                    context_lines.append(" | ".join(str(v) for v in row))
                context = "\n".join(context_lines)
            else:
                context = "Không tìm thấy kết quả phù hợp trong cơ sở dữ liệu."

        logs.append(f"✅ **SQL Result**: Trả về {len(rows)} rows")
    except Exception as e:
        context = f"Lỗi khi thực thi SQL: {str(e)}"
        logs.append(f"❌ **SQL Error**: {str(e)[:100]}")

    return {"context": context, "logs": logs}


# =============================================================
# NODE 3: VECTOR RETRIEVER (PGVector) — with collection filter
# =============================================================
def vector_retriever_node(state: AgentState) -> dict:
    """
    Dùng PGVector chọc vào langchain_pg_collection & langchain_pg_embedding.
    Hỗ trợ collection filtering + synonym multi-query.
    """
    logs = state.get("logs", [])
    logs.append("📚 **Vector Retriever**: Đang tìm kiếm tài liệu liên quan...")

    q = state.get("rewritten_question") or state["question"]

    # Synonym multi-query: nếu có synonym_queries, dùng tất cả
    queries = state.get("synonym_queries") or [q]
    if not queries:
        queries = [q]

    # Lấy collection lọc từ LLM semantic analyzer thay vì keyword
    collection_filter = state.get("target_collections", [])
    if collection_filter:
        logs.append(
            f"🔍 **Vector Filter**: LLM chỉ định tìm trong collections `{', '.join(collection_filter)}`"
        )

    # Encode all queries
    model = load_vector_embed_model()
    all_results = []
    seen_ids = set()

    conn = psycopg2.connect(DB_CONNECTION)
    try:
        for query_text in queries[:3]:  # Max 3 queries
            q_emb = model.encode(query_text).tolist()
            vec_str = "[" + ",".join(str(x) for x in q_emb) + "]"

            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if collection_filter:
                    cur.execute(
                        """
                        SELECT
                            e.id,
                            e.document,
                            e.cmetadata,
                            c.name AS collection_name,
                            (e.embedding <=> %s::vector) AS distance
                        FROM langchain_pg_embedding e
                        JOIN langchain_pg_collection c ON c.uuid = e.collection_id
                        WHERE c.name = ANY(%s)
                        ORDER BY distance ASC
                        LIMIT 5
                    """,
                        (vec_str, collection_filter),
                    )
                else:
                    cur.execute(
                        """
                        SELECT
                            e.id,
                            e.document,
                            e.cmetadata,
                            c.name AS collection_name,
                            (e.embedding <=> %s::vector) AS distance
                        FROM langchain_pg_embedding e
                        JOIN langchain_pg_collection c ON c.uuid = e.collection_id
                        ORDER BY distance ASC
                        LIMIT 5
                    """,
                        (vec_str,),
                    )
                results = cur.fetchall()

                for r in results:
                    rid = r.get("id", "")
                    if rid not in seen_ids:
                        seen_ids.add(rid)
                        all_results.append(r)
    finally:
        conn.close()

    # Sort all results by distance, take top 5
    all_results.sort(key=lambda r: float(r["distance"]))
    top_results = all_results[:5]

    if top_results:
        context_parts = []
        for i, r in enumerate(top_results, 1):
            similarity = round(1 - float(r["distance"]), 4)
            source = ""
            if r["cmetadata"]:
                meta = r["cmetadata"] if isinstance(r["cmetadata"], dict) else {}
                source = meta.get("filename", meta.get("source", r["collection_name"]))
            doc_text = (r["document"] or "")[:500]
            context_parts.append(
                f"[{i}] (Similarity: {similarity} | Source: {source} | Collection: {r['collection_name']})\n{doc_text}"
            )
        context = "\n\n---\n\n".join(context_parts)
        top_sim = round(1 - float(top_results[0]["distance"]), 4)
        logs.append(
            f"✅ **Vector Result**: Tìm thấy {len(top_results)} tài liệu (Top similarity: {top_sim})"
        )
        if len(queries) > 1:
            logs.append(f"🔄 **Multi-Query**: Đã dùng {len(queries)} biến thể câu hỏi")
    else:
        context = "Không tìm thấy tài liệu liên quan trong vector database."
        logs.append("⚠️ **Vector Result**: Không tìm thấy tài liệu nào.")

    return {"context": context, "vector_context": context, "logs": logs}


# =============================================================
# NODE 3b: GRAPH RETRIEVER — Embedding-based search
# =============================================================
def graph_retriever_node(state: AgentState) -> dict:
    """
    Tìm kiếm trong Knowledge Graph (graph.json).
    V2: Dùng embedding similarity thay vì substring match.
    """
    logs = state.get("logs", [])
    logs.append("🕸️ **Graph Retriever**: Đang tìm kiếm trong Knowledge Graph...")

    q = (state.get("rewritten_question") or state["question"]).lower()
    graph = load_graph()

    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    # Build lookup dicts
    node_map = {n["id"]: n["type"] for n in nodes}

    # ── Phase 1: Exact match (tracking/order codes) ──
    matched_nodes = []
    seen = set()

    trk_matches = re.findall(r"trk\d{7}", q, re.IGNORECASE)
    ord_matches = re.findall(r"ord\d{7}", q, re.IGNORECASE)
    for code in trk_matches + ord_matches:
        code_upper = code.upper()
        if code_upper in node_map:
            matched_nodes.append({"id": code_upper, "type": node_map[code_upper]})
            seen.add(code_upper)

    # ── Phase 2: Embedding-based search ──
    model = load_sbert_model()
    node_ids, node_types, node_embs = encode_graph_nodes(model)

    q_emb = model.encode(q, convert_to_tensor=True)
    cos_scores = util.cos_sim(q_emb, node_embs)[0]

    # Get top-10 similar nodes (threshold > 0.3)
    top_k = min(10, len(node_ids))
    top_indices = cos_scores.argsort(descending=True)[:top_k]

    for idx in top_indices:
        idx = int(idx)
        score = float(cos_scores[idx])
        if score < 0.3:
            break
        nid = node_ids[idx]
        if nid not in seen:
            seen.add(nid)
            matched_nodes.append({"id": nid, "type": node_types[idx], "_score": score})

    # ── Phase 3: Fallback — LLM entity extraction ──
    if len(matched_nodes) < 2:
        extract_prompt = PromptTemplate.from_template("""
Trích xuất các entity (tên sản phẩm, mã tracking TRK..., mã đơn ORD..., địa điểm kho, loại hư hỏng)
từ câu hỏi sau. Trả về danh sách entity, mỗi cái trên 1 dòng, không giải thích.

Câu hỏi: {question}
""")
        llm = get_generator_llm()
        entities_raw = invoke_llm_tracked(
            extract_prompt, llm, {"question": q}, state, "Graph Entity Extractor"
        )
        entities = [
            e.strip().replace(" ", "_")
            for e in entities_raw.strip().split("\n")
            if e.strip()
        ]

        for entity in entities:
            entity_lower = entity.lower()
            for n in nodes:
                if entity_lower in n["id"].lower() or n["id"].lower() in entity_lower:
                    if n["id"] not in seen:
                        seen.add(n["id"])
                        matched_nodes.append(n)

    logs.append(f"🔍 **Graph Match**: Tìm thấy {len(matched_nodes)} entity trong graph")

    # ── Build context from edges ──
    context_parts = []
    related_edges_count = 0
    for node in matched_nodes[:10]:
        node_id = node["id"]
        node_type = node["type"]
        score_info = (
            f" (sim: {node.get('_score', '-'):.4f})" if "_score" in node else ""
        )
        context_parts.append(f"📌 **{node_id}** (Loại: {node_type}){score_info}")

        for edge in edges:
            if edge["source"] == node_id or edge["target"] == node_id:
                src = edge["source"]
                tgt = edge["target"]
                rel = edge.get("relation", "LIÊN_QUAN")
                src_type = node_map.get(src, "?")
                tgt_type = node_map.get(tgt, "?")
                context_parts.append(
                    f"  → [{src_type}] {src} --({rel})--> [{tgt_type}] {tgt}"
                )
                related_edges_count += 1

    if context_parts:
        context = "\n".join(context_parts)
        logs.append(
            f"✅ **Graph Result**: {len(matched_nodes)} nodes, {related_edges_count} relationships"
        )
    else:
        context = "Không tìm thấy thông tin liên quan trong Knowledge Graph."
        logs.append("⚠️ **Graph Result**: Không tìm thấy entity nào trong graph.")

    return {"context": context, "graph_context": context, "logs": logs}


# =============================================================
# NODE 3c: HYBRID RETRIEVER (Vector + Graph combined)
# =============================================================
def hybrid_retriever_node(state: AgentState) -> dict:
    """
    Chạy cả Vector Retriever và Graph Retriever, merge context.
    Dùng khi câu hỏi cần thông tin từ cả 2 nguồn.
    """
    logs = state.get("logs", [])
    logs.append(
        "🔀 **Hybrid Retriever**: Đang query cả VectorDB lẫn Knowledge Graph..."
    )

    # ── Run Vector Retriever ──
    vec_result = vector_retriever_node(state)
    vec_context = vec_result.get("vector_context", vec_result.get("context", ""))
    logs = vec_result.get("logs", logs)

    # ── Run Graph Retriever ──
    # Update state with current logs before passing to graph retriever
    graph_state = dict(state)
    graph_state["logs"] = logs
    graph_result = graph_retriever_node(graph_state)
    graph_context = graph_result.get("graph_context", graph_result.get("context", ""))
    logs = graph_result.get("logs", logs)

    # ── Merge contexts ──
    merged_parts = []
    if vec_context and "Không tìm thấy" not in vec_context:
        merged_parts.append(f"═══ THÔNG TIN TỪ TÀI LIỆU (VectorDB) ═══\n{vec_context}")
    if graph_context and "Không tìm thấy" not in graph_context:
        merged_parts.append(f"═══ THÔNG TIN TỪ KNOWLEDGE GRAPH ═══\n{graph_context}")

    if merged_parts:
        context = "\n\n" + "\n\n".join(merged_parts)
    else:
        context = (
            "Không tìm thấy thông tin liên quan trong cả VectorDB lẫn Knowledge Graph."
        )

    logs.append(f"✅ **Hybrid Merge**: Đã kết hợp context từ {len(merged_parts)} nguồn")

    return {
        "context": context,
        "vector_context": vec_context,
        "graph_context": graph_context,
        "logs": logs,
    }


# =============================================================
# NODE 4: CALCULATOR (Smart Data Analyst LLM)
# =============================================================
def calculator_node(state: AgentState) -> dict:
    """
    Agent Data Analyst: Thực hiện đọc hiểu và trích xuất số liệu / tính toán trực tiếp bằng LLM reasoning.
    Không dùng safe_eval nữa.
    """
    logs = state.get("logs", [])

    if not state.get("needs_calculation", False):
        return {"calculation_result": "", "logs": logs}

    logs.append(
        "🔢 **Data Analyst Node**: Đang phân tích ngữ nghĩa và tính toán số liệu..."
    )

    q = state.get("rewritten_question") or state["question"]
    context = state.get("context", "")
    route = state.get("route", "")

    calc_prompt = PromptTemplate.from_template("""
Bạn là chuyên gia Data Analyst xuất sắc. 
Hãy đọc dữ liệu từ MẢNG DỮ LIỆU/CONTEXT bên dưới và trả lời trực tiếp vào trọng tâm câu hỏi của người dùng.
Nguồn dữ liệu: {route}

HƯỚNG DẪN XỬ LÝ LÕI:
1. Nếu dữ liệu từ SQL (bảng biểu): Rất có thể câu SQL đã GOM NHÓM (GROUP BY) và TÍNH TOÁN sẵn rồi. Việc của bạn chỉ là: "Đọc bảng, Viết một báo cáo trả lời ĐÚNG CÂU HỎI rõ ràng" (ví dụ: bôi đậm các chỉ số TOP). Không cần tính nếu đã tính sẵn.
2. Nếu dữ liệu từ Vector/Graph (văn bản): Tự động trích xuất các con số tương ứng để phép toán (cộng sum, trung bình,...) và xuất kết quả báo cáo.
3. CHỈ VIẾT KẾT QUẢ/BÁO CÁO PHÂN TÍCH, KHÔNG OUTPUT CODE PYTHON, KHÔNG GIẢI THÍCH LANG MANG.

CONTEXT SỐ LIỆU ĐANG CÓ:
{context}

CÂU HỎI USER: {question}

BÁO CÁO PHÂN TÍCH CHỐT LẠI:
""")

    llm = get_generator_llm()
    calc_output = invoke_llm_tracked(
        calc_prompt,
        llm,
        {"context": context, "question": q, "route": route},
        state,
        "Smart Calculator",
    )

    logs.append(
        "✅ **Data Analyst Node**: Bảng / Báo cáo tính toán nội suy đã sinh xong."
    )

    return {"calculation_result": calc_output, "logs": logs}


# =============================================================
# NODE 5: GENERATOR (Gemini)
# =============================================================
def generator_node(state: AgentState) -> dict:
    """Tổng hợp context (+ calculation nếu có) và trả lời câu hỏi."""
    logs = state.get("logs", [])
    logs.append("🤖 **Generator**: Đang tổng hợp câu trả lời...")

    q = state.get("rewritten_question") or state["question"]
    context = state.get("context", "")
    route = state.get("route", "")
    calc_result = state.get("calculation_result", "")

    # Append calculation results to context if available
    if calc_result and "KHÔNG_ĐỦ_DỮ_LIỆU" not in calc_result:
        context += f"\n\n═══ KẾT QUẢ TÍNH TOÁN ═══\n{calc_result}"

    gen_prompt = PromptTemplate.from_template("""
Bạn là trợ lý AI chuyên về Hải Quan và Logistics Việt Nam.
Hãy trả lời câu hỏi dựa HOÀN TOÀN vào ngữ cảnh (context) được cung cấp.
Nguồn dữ liệu: {route}
Nếu context không đủ thông tin, hãy nói rõ là không tìm thấy.
Trả lời bằng tiếng Việt, rõ ràng và chuyên nghiệp.
Nếu dữ liệu là bảng SQL, hãy format kết quả dạng bảng dễ đọc.
Nếu dữ liệu là Knowledge Graph, hãy mô tả mối quan hệ giữa các entity.
Nếu có kết quả tính toán, hãy trình bày rõ phép tính và kết quả.
Nếu nguồn là hybrid (VectorDB + Graph), hãy tổng hợp từ cả 2 nguồn.

CONTEXT:
{context}

CÂU HỎI: {question}

TRẢ LỜI:
""")

    llm = get_generator_llm()
    answer = invoke_llm_tracked(
        gen_prompt,
        llm,
        {"context": context, "question": q, "route": route},
        state,
        "Generator",
    )

    logs.append("✅ **Generator**: Đã tạo câu trả lời.")

    return {"answer": answer, "logs": logs}


# =============================================================
# NODE 6: HALLUCINATION GRADER
# =============================================================
def hallucination_grader_node(state: AgentState) -> dict:
    """
    LLM đánh giá answer có bịa đặt so với context không.
    Trả về "pass" hoặc "fail" lưu vào state.
    """
    logs = state.get("logs", [])
    logs.append("🔍 **Hallucination Grader**: Đang kiểm tra độ chính xác...")

    grader_prompt = PromptTemplate.from_template("""
Bạn là một chuyên gia đánh giá chất lượng câu trả lời.
Hãy kiểm tra xem CÂU TRẢ LỜI có được hỗ trợ bởi CONTEXT hay không.

CONTEXT:
{context}

CÂU TRẢ LỜI:
{answer}

Hãy đánh giá:
- Nếu câu trả lời ĐÚNG dựa trên context hoặc thể hiện rõ rằng không đủ thông tin → trả về "pass"
- Nếu câu trả lời BỊA ĐẶT thông tin không có trong context → trả về "fail"

CHỈ trả về đúng một từ: pass hoặc fail
""")

    llm = get_grader_llm()
    grade = (
        invoke_llm_tracked(
            grader_prompt,
            llm,
            {
                "context": state.get("context", ""),
                "answer": state.get("answer", ""),
            },
            state,
            "Hallucination Grader",
        )
        .strip()
        .lower()
    )

    # Normalize
    if "pass" in grade:
        grade = "pass"
    else:
        grade = "fail"

    if grade == "pass":
        logs.append("✅ **Grader**: Câu trả lời đạt chất lượng (PASS)")
    else:
        logs.append(
            f"⚠️ **Grader**: Phát hiện ảo giác! (FAIL) — Retry count: {state.get('retry_count', 0)}"
        )

    return {"grade": grade, "logs": logs}


# =============================================================
# NODE 7a: SYNONYM REWRITER (v2 — expand with synonyms)
# =============================================================
def synonym_rewriter_node(state: AgentState) -> dict:
    """
    Dùng synonym map để expand câu hỏi thành nhiều biến thể.
    Ưu tiên chạy trước LLM rewrite (retry lần 1).
    """
    logs = state.get("logs", [])
    retry = state.get("retry_count", 0) + 1
    logs.append(f"🔄 **Synonym Rewriter**: Đang expand từ đồng nghĩa (lần {retry})...")

    q = state.get("rewritten_question") or state["question"]
    variants = expand_with_synonyms(q)

    if len(variants) > 1:
        logs.append(f"📝 **Synonym Variants**: Tạo {len(variants)} biến thể:")
        for i, v in enumerate(variants):
            logs.append(f"  [{i + 1}] {v[:100]}")
        rewritten = variants[1]  # Use first synonym variant as primary
    else:
        # No synonyms found, do a light LLM rewrite instead
        logs.append(
            "⚠️ **Synonym Rewriter**: Không tìm thấy từ đồng nghĩa, dùng LLM rewrite nhẹ..."
        )
        rewrite_prompt = PromptTemplate.from_template("""
Viết lại câu hỏi sau bằng các từ đồng nghĩa chuyên ngành logistics/hải quan.
Giữ nguyên ý nghĩa, chỉ thay thế từ khóa. CHỈ trả về câu hỏi mới.

Câu hỏi: {question}
""")
        llm = get_rewriter_llm()
        rewritten = invoke_llm_tracked(
            rewrite_prompt, llm, {"question": q}, state, "Synonym Rewriter"
        ).strip()
        variants = [q, rewritten]

    logs.append(f"📝 **Primary Rewrite**: {rewritten[:150]}")

    return {
        "rewritten_question": rewritten,
        "synonym_queries": variants,
        "retry_count": retry,
        "retry_strategy": "synonym",
        "logs": logs,
    }


# =============================================================
# NODE 7b: LLM REWRITER (Team's PromptTemplate — retry lần 2)
# =============================================================
def rewriter_node(state: AgentState) -> dict:
    """
    Dùng Gemini + PromptTemplate viết lại câu hỏi
    Hải Quan/Logistics (deep rewrite, retry lần 2).
    """
    logs = state.get("logs", [])
    retry = state.get("retry_count", 0) + 1
    logs.append(f"✏️ **LLM Rewriter**: Đang viết lại câu hỏi sâu (lần {retry})...")

    rewrite_prompt = PromptTemplate.from_template("""
Bạn là chuyên gia về Hải Quan và Logistics Việt Nam.
Hãy viết lại câu hỏi sau để rõ ràng hơn, chính xác hơn,
và phù hợp hơn cho việc tìm kiếm thông tin trong hệ thống quản lý kho vận.

Lưu ý:
- Giữ nguyên ý nghĩa gốc của câu hỏi
- Thêm các từ khóa chuyên ngành nếu phù hợp
- Sử dụng từ đồng nghĩa để mở rộng phạm vi tìm kiếm
- Cụ thể hóa các khái niệm mơ hồ
- Nếu câu hỏi có tracking code hoặc mã đơn, giữ nguyên
- Trả về CHỈ câu hỏi đã viết lại, không giải thích

Câu hỏi gốc: {question}

Câu hỏi viết lại:
""")

    llm = get_rewriter_llm()
    rewritten = invoke_llm_tracked(
        rewrite_prompt,
        llm,
        {"question": state.get("rewritten_question") or state["question"]},
        state,
        "LLM Deep Rewriter",
    )

    logs.append(f"📝 **Rewritten**: {rewritten[:150]}")

    return {
        "rewritten_question": rewritten.strip(),
        "synonym_queries": [],  # Clear synonym queries for fresh retrieval
        "retry_count": retry,
        "retry_strategy": "llm_rewrite",
        "logs": logs,
    }


# =============================================================
# NODE 8: FALLBACK
# =============================================================
def fallback_node(state: AgentState) -> dict:
    """Trả về câu fallback khi hết retry."""
    logs = state.get("logs", [])
    logs.append("😅 **Fallback**: Hệ thống không thể tìm thấy câu trả lời chính xác.")

    return {
        "answer": "Câu này khó quá, hệ thống không tìm thấy thông tin sếp ơi haha 😅",
        "logs": logs,
    }


# =============================================================
# CONDITIONAL EDGES
# =============================================================
def route_after_router(state: AgentState) -> str:
    """Điều hướng sau Semantic Router → sql / vector / graph / hybrid."""
    return state["route"]


def route_after_grader(state: AgentState) -> str:
    """
    Điều hướng sau Hallucination Grader:
    - pass → END
    - fail + retry_count == 0 → synonym_rewriter (expand từ đồng nghĩa)
    - fail + retry_count == 1 → rewriter (LLM deep rewrite)
    - fail + retry_count >= 2 → fallback
    """
    grade = state.get("grade", "fail")

    if grade == "pass":
        return "pass"

    retry_count = state.get("retry_count", 0)
    if retry_count == 0:
        return "synonym_rewrite"
    elif retry_count == 1:
        return "rewrite"
    else:
        return "fallback"


# =============================================================
# BUILD LANGGRAPH
# =============================================================
@st.cache_resource
def build_graph():
    """Xây dựng LangGraph State Graph (v2 — hybrid + calculator)."""
    workflow = StateGraph(AgentState)

    # ── Add Nodes ──
    workflow.add_node("semantic_router", semantic_router_node)
    workflow.add_node("sql_retriever", sql_retriever_node)
    workflow.add_node("vector_retriever", vector_retriever_node)
    workflow.add_node("graph_retriever", graph_retriever_node)
    workflow.add_node("hybrid_retriever", hybrid_retriever_node)
    workflow.add_node("calculator", calculator_node)
    workflow.add_node("generator", generator_node)
    workflow.add_node("hallucination_grader", hallucination_grader_node)
    workflow.add_node("synonym_rewriter", synonym_rewriter_node)
    workflow.add_node("rewriter", rewriter_node)
    workflow.add_node("fallback", fallback_node)

    # ── Set Entry Point ──
    workflow.set_entry_point("semantic_router")

    # ── Conditional Edge: Router → SQL / Vector / Graph / Hybrid ──
    workflow.add_conditional_edges(
        "semantic_router",
        route_after_router,
        {
            "sql": "sql_retriever",
            "vector": "vector_retriever",
            "graph": "graph_retriever",
            "hybrid": "hybrid_retriever",
        },
    )

    # ── Retriever → Calculator ──
    workflow.add_edge("sql_retriever", "calculator")
    workflow.add_edge("vector_retriever", "calculator")
    workflow.add_edge("graph_retriever", "calculator")
    workflow.add_edge("hybrid_retriever", "calculator")

    # ── Calculator → Generator ──
    workflow.add_edge("calculator", "generator")

    # ── Generator → Grader ──
    workflow.add_edge("generator", "hallucination_grader")

    # ── Conditional Edge: Grader → END / Synonym / Rewriter / Fallback ──
    workflow.add_conditional_edges(
        "hallucination_grader",
        route_after_grader,
        {
            "pass": END,
            "synonym_rewrite": "synonym_rewriter",
            "rewrite": "rewriter",
            "fallback": "fallback",
        },
    )

    # ── Rewriters → Router (loop back) ──
    workflow.add_edge("synonym_rewriter", "semantic_router")
    workflow.add_edge("rewriter", "semantic_router")

    # ── Fallback → END ──
    workflow.add_edge("fallback", END)

    return workflow.compile()


# =============================================================
# STREAMLIT UI
# =============================================================
def main():
    st.set_page_config(
        page_title="RAGNAROK — Multi-Agent RAG",
        page_icon="⚡",
        layout="wide",
    )

    # ── Custom CSS ──
    st.markdown(
        """
    <style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
    }
    .main-header h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 800;
    }
    .main-header p {
        color: #888;
        font-size: 1rem;
    }
    .stChatMessage { border-radius: 12px; }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # ── Header ──
    st.markdown(
        """
    <div class="main-header">
        <h1>⚡ RAGNAROK v2</h1>
        <p>Hệ thống Multi-Agent RAG — Hybrid Query — Hải Quan & Logistics</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # ── Sidebar: System info ──
    with st.sidebar:
        st.header("🧠 Agent Brain v2")
        st.markdown("---")
        st.markdown("**Model Router:** `vietnamese-sbert`")
        st.markdown("**Model Rewriter:** `gemini-2.5-pro`")
        st.markdown("**Model Generator:** `gemini-2.5-pro`")
        st.markdown("**Model Grader:** `gemini-2.5-pro`")
        st.markdown("---")
        st.markdown("**📊 System Statistics:**")
        st.markdown("**🗄️ SQL Database:**")
        st.markdown("- `nhat_ky_dong_goi_lai` (600 rows, 18 cols)")
        st.markdown("- `theo_doi_giao_noi_dia` (8,664 rows, 19 cols)")
        st.markdown("**📄 Vector Collections (384-dim):**")
        st.markdown("- `phieu_dong_goi_vector` (2,074)")
        st.markdown("- `manifest_chuyen_bay_vector` (919)")
        st.markdown("- `to_khai_hai_quan` (273)")
        st.markdown("- `luat_vien_thong_kho` (162)")
        st.markdown("- **Total: 3,428 embeddings**")
        st.markdown("**🔗 Knowledge Graph:**")
        st.markdown("- 221 nodes (10 types)")
        st.markdown("- 745 edges")
        st.markdown("**📁 Dataset:**")
        st.markdown(
            "- 1,100 files (500 phiếu + 398 manifest + 120 biên bản + 60 tờ khai + 20 policy + 2 CSV)"
        )
        st.markdown("---")
        st.markdown("**🏗️ Architecture:**")
        st.markdown("- 11 LangGraph nodes")
        st.markdown("- 7 LLM invoke points")
        st.markdown("- Model: Gemini 2.5 Pro")
        st.markdown("- Embedding: all-MiniLM-L6-v2")
        st.markdown("---")
        st.markdown("**🆕 v2 Features:**")
        st.markdown("- 🔀 Hybrid Query (Vector+Graph)")
        st.markdown("- 🔄 Synonym Rewrite Tool")
        st.markdown("- 🔢 Calculator Tool (safe_eval)")
        st.markdown("- 🎯 Collection Filtering (4 collections)")
        st.markdown("- 🧲 Embedding Graph Search (SBERT)")
        st.markdown("- 📊 Token Usage Tracking")
        st.markdown("---")
        st.markdown("**🧠 Agent Thinking Log:**")
        agent_log_placeholder = st.empty()

    # ── Initialize chat history ──
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "agent_logs" not in st.session_state:
        st.session_state.agent_logs = []

    # ── Display chat history ──
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ── Chat input ──
    prompt = st.chat_input("Hỏi về Hải Quan & Logistics...")

    if prompt:
        # Show user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Build & run graph
        graph = build_graph()

        with st.chat_message("assistant"):
            with st.status("🧠 Agent đang suy nghĩ...", expanded=True) as status:
                thinking_logs = []

                # ── Initialize state ──
                initial_state: AgentState = {
                    "question": prompt,
                    "rewritten_question": "",
                    "synonym_queries": [],
                    "context": "",
                    "vector_context": "",
                    "graph_context": "",
                    "answer": "",
                    "route": "",
                    "needs_calculation": False,
                    "calculation_result": "",
                    "retry_count": 0,
                    "retry_strategy": "",
                    "grade": "",
                    "logs": [],
                    "token_usage": {
                        "input": 0,
                        "output": 0,
                        "total": 0,
                        "calls": 0,
                        "details": [],
                    },
                    "target_collections": [],
                }

                st.write("⏳ Đang khởi tạo pipeline...")

                # ── Stream through LangGraph ──
                accumulated_state = dict(initial_state)
                for step_output in graph.stream(initial_state, stream_mode="updates"):
                    for node_name, node_state in step_output.items():
                        # Merge node output vào accumulated state
                        accumulated_state.update(node_state)

                        # Update logs from node
                        if "logs" in node_state:
                            new_logs = node_state["logs"]
                            for log_entry in new_logs:
                                if log_entry not in thinking_logs:
                                    thinking_logs.append(log_entry)
                                    st.write(log_entry)

                        # Update sidebar
                        with agent_log_placeholder.container():
                            for log_entry in thinking_logs:
                                st.markdown(f"- {log_entry}")

                # ── Get final answer ──
                answer = accumulated_state.get("answer", "")
                if not answer:
                    answer = "Xin lỗi, có lỗi xảy ra trong quá trình xử lý."

                status.update(label="✅ Hoàn tất!", state="complete", expanded=False)

            # Display answer
            st.markdown(answer)

            # ── Display Token Usage ──
            token_usage = accumulated_state.get("token_usage", {})
            if token_usage and token_usage.get("total", 0) > 0:
                st.markdown("---")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("📥 Input Tokens", f"{token_usage.get('input', 0):,}")
                col2.metric("📤 Output Tokens", f"{token_usage.get('output', 0):,}")
                col3.metric("📊 Total Tokens", f"{token_usage.get('total', 0):,}")
                col4.metric("🔄 LLM Calls", f"{token_usage.get('calls', 0)}")

                with st.expander("📋 Chi tiết Token theo Node"):
                    details = token_usage.get("details", [])
                    if details:
                        for d in details:
                            st.markdown(
                                f"- **{d['node']}**: "
                                f"input={d['input_tokens']:,} | "
                                f"output={d['output_tokens']:,} | "
                                f"total={d['total']:,}"
                            )

        # Save to history
        st.session_state.messages.append({"role": "assistant", "content": answer})
        st.session_state.agent_logs = thinking_logs


if __name__ == "__main__":
    main()

