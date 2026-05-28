# PharmaClear

PharmaClear is a centralized compliance platform designed to unify fragmented pharmaceutical data and drug recall logs from global regulatory bodies into a single, reliable dashboard.

By combining asynchronous web data extraction with LLM-powered inference (**Neuro-Symbolic AI** principles), it transforms complex, unstructured raw data into clean, structured compliance reporting.

---

### Key Features

* **Multi-Source Aggregation:** Real-time data pulling via the **openFDA API** coupled with targeted asynchronous web scraping of **Health Canada** Enforcement Reports using **BeautifulSoup4**.
* **Neuro-Symbolic Reasoning:** Integrates data extraction across heterogeneous web layouts with **Llama 3 (via Groq)** to anchor processing in real-world facts, mitigating LLM hallucinations.
* **Interactive RAG Chat:** An on-dashboard **Retrieval-Augmented Generation** chat system allowing compliance analysts to query context-specific details of the active search results.
* **Automated Risk Profiles:** Generates downloadable, styled PDF risk reports dynamically using **ReportLab**.
* **User Session Persistence:** Structured persistence using **SQLAlchemy** to store persistent watchlists, secure JWT user access, and local search histories.

---

### Architecture & Tech Stack

* **Frontend:** React.js, Tailwind CSS, Lucide Icons, PostCSS
* **Backend:** FastAPI (Python), SQLAlchemy ORM, Httpx (Async I/O requests), BeautifulSoup4 & Lxml
* **Database & Migrations:** PostgreSQL, Alembic
* **Inference Engine:** Groq Cloud API (`llama-3.1-8b-instant`)

---

### Repository Structure

```text
PharmaClear/
├── backend/               # FastAPI application layer
│   ├── main.py            # Core endpoints & search orchestration
│   ├── crud.py            # DB operations (Watchlist, Search History)
│   ├── auth.py            # JWT authentication logic
│   ├── database.py        # SQLAlchemy connection setup
│   ├── models.py          # SQLAlchemy DB models
│   ├── schemas.py         # Pydantic data validation schemas
│   ├── alerter.py         # Background scheduler for automated tracking
│   └── requirements.txt   # Python service dependencies
├── frontend/              # User interface layer
│   └── pharmaclear/       # React SPA source project
│       ├── src/
│       │   ├── DashboardPage.js  # Main search workspace & RAG UI
│       │   └── AuthContext.js    # Session token state tracking
├── alembic/               # Database migration scripts
├── .gitignore             # Kept to isolate sensitive environment credentials
├── alembic.ini            # Database migration configuration settings
└── README.md              # Project documentation

```

---

### Local Development Quick Start

#### 1. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
# Create a .env file containing your DATABASE_URL and GROQ_API_KEY
uvicorn main:app --reload

```

#### 2. Frontend Setup

```bash
cd frontend/pharmaclear
npm install
npm start

```
