# Vector Embedding Visualizer

Interactive 3D visualization of LangChain pgvector embeddings.

## Quick Start

```bash
cd visualize
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open **http://localhost:5001** in your browser.

## Features

- 🎯 **3D Scatter Plot** — embeddings reduced via t-SNE or PCA
- 📦 **Collection Filter** — toggle collections on/off
- 🔗 **Similarity Search** — click a point to see nearest neighbours with connecting lines
- 🔍 **Text Search** — filter by document content
- 🌙 **Dark Mode** — glassmorphism UI

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DB_CONNECTION` | `postgresql://postgres:123456@52.220.77.141:5432/se` | PostgreSQL DSN |
| `PORT` | `5001` | Server port |
