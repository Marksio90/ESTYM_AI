# ESTYM_AI

AI-powered multi-agent platform for automated cost estimation and technology planning of steel products.

## Overview

ESTYM_AI automates the RFQ (Request for Quote) workflow for steel manufacturing — from email intake through CAD/PDF drawing analysis, cost calculation, to ERP export. It handles products made from wire, tubes, profiles, sheet metal, flat bars, angles, and bars.

**Core pipeline:** Email → File Processing → Drawing Analysis → Cost Calculation → QA Validation → Human Review → ERP Export

## Architecture

- **Multi-agent orchestration** — LangGraph StateGraph with supervisor pattern
- **Hybrid drawing analysis** — CAD geometric parsing (ezdxf, PythonOCC) + multimodal LLM vision (GPT-4o, Claude)
- **Parametric + ML cost engine** — deterministic time norms as baseline, XGBoost residual correction
- **Product similarity search** — pgvector cosine similarity with composite feature/text embeddings
- **HDBSCAN clustering** — automatic product family discovery

## Tech Stack

| Layer | Technology |
|---|---|
| Orchestration | LangGraph |
| API | FastAPI |
| Database | PostgreSQL 17 + pgvector |
| Graph DB | Neo4j 5 |
| Object Storage | MinIO |
| Task Queue | Celery + Redis |
| ML | XGBoost, SHAP, HDBSCAN |
| CAD Parsing | ezdxf, PythonOCC, trimesh |
| PDF Processing | PyMuPDF, pdfplumber |
| LLM | OpenAI GPT-4o, Anthropic Claude |

## Quick Start

```bash
# Clone and configure
cp .env.example .env
# Edit .env with your API keys and settings

# Start all services
docker compose up -d

# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

## Project Structure

```
src/estym_ai/
├── agents/         # LangGraph multi-agent workflow
│   ├── workflow.py     # Main StateGraph orchestration
│   ├── state.py        # Shared RFQ state
│   ├── intake_agent.py # Email classification
│   ├── drawing_agent.py # CAD/PDF analysis
│   ├── cost_agent.py   # Cost calculation
│   ├── qa_agent.py     # Quality validation
│   └── erp_agent.py    # Graffiti ERP export
├── models/         # Pydantic data contracts
│   ├── inquiry.py      # InquiryCase
│   ├── part_spec.py    # PartSpec (drawing extraction)
│   ├── tech_plan.py    # TechPlan (PSI graph)
│   └── quote.py        # Quote (cost breakdown)
├── pipeline/       # File processing pipeline
│   ├── file_router.py  # Format detection
│   ├── dxf_parser.py   # DXF geometric extraction
│   ├── pdf_processor.py # PDF rendering + table extraction
│   ├── step_analyzer.py # STEP B-Rep analysis
│   └── vision_analyzer.py # VLM drawing analysis
├── calc/           # Cost calculation engine
│   ├── time_norms.py   # Parametric formulas
│   ├── cost_engine.py  # TechPlan + Quote generation
│   └── ml_corrector.py # XGBoost residual model
├── similarity/     # Product similarity search
│   ├── embeddings.py   # Feature/text embeddings
│   └── clustering.py   # HDBSCAN product families
├── db/             # Database layer
│   ├── models.py       # SQLAlchemy ORM + pgvector
│   ├── session.py      # Async session management
│   └── repository.py   # CRUD + vector search
├── api/            # FastAPI REST endpoints
│   └── routes/
├── config/         # Application settings
└── integrations/   # ERP and external services
```

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run linter
ruff check src/

# Run type checker
mypy src/
```

## License

MIT
