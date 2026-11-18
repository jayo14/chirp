# 🐤 Chirp — University Class Assignment Bot

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7%2B-blue.svg)](https://www.typescriptlang.org)
[![Baileys](https://img.shields.io/badge/WhatsApp-Baileys-25D366.svg)](https://github.com/WhiskeySockets/Baileys)
[![SQLAlchemy](https://img.shields.io/badge/ORM-SQLAlchemy%202.0%20(Async)-red.svg)](https://www.sqlalchemy.org/)

**Chirp** is an AI-powered WhatsApp assistant engineered to help university classes track academic assignments, understand requirements, preserve original documents/diagrams, and prevent missed deadlines.

Initial target deployment: **LASUSTECH Class WhatsApp Group**.

---

## 🏛️ Architecture Overview

Chirp uses a modular clean architecture with two independent services:

```text
┌────────────────────────────────────────────────────────┐
│                   WhatsApp Network                     │
│  (Class Group Chat & Private Forwarding / Admin Chat)  │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│        WhatsApp Gateway (TypeScript + Baileys)         │
│  • Persistent Session Auth (auth_info_baileys)         │
│  • QR Terminal Generation                              │
│  • Connection Life-cycle & Auto-reconnect              │
│  • Media & Document Downloader                         │
│  • Webhook Dispatcher (X-Gateway-Secret signed)        │
└──────────────────────────┬─────────────────────────────┘
                           │ HTTP POST /api/v1/webhook/whatsapp
                           ▼
┌────────────────────────────────────────────────────────┐
│             Python Backend (FastAPI + Async)           │
│  • Clean Architecture (API, Models, Repos, Services)   │
│  • Media Processing & PyPDF Text Extraction            │
│  • Multimodal AI Extraction (Gemini / OpenAI / Mock)   │
│  • Human-in-the-Loop Admin Review Queue                │
│  • African/Lagos (WAT) Timezone Deadline Engine        │
│  • Persistent APScheduler / DB-backed Notification Hub │
│  • PostgreSQL / SQLite with Alembic Migrations         │
└────────────────────────────────────────────────────────┘
```

---

## 🚀 Key Features (MVP Scope)

- **WhatsApp Group Monitoring & Private Forwarding:** Listens to class announcements and accepts student/rep private forwards.
- **Multimodal AI Extraction:** Extracts course code, course title, assignment title, questions, instructions, and deadlines from text, photos of handwritten sheets, and PDFs.
- **Diagram & Original File Preservation:** Retains source attachments; never discards original academic diagrams.
- **Human-in-the-Loop Admin Review:** New assignments are queued for administrator verification. Admins approve/reject directly via WhatsApp private chat or REST API.
- **Africa/Lagos Timezone Awareness:** All deadlines and reminders are calculated and formatted in West Africa Time (`Africa/Lagos`).
- **Automated 24h Deadline Reminders:** Schedules pre-deadline alerts 24 hours prior to submission.
- **Sunday Weekly Assignment Digest:** Generates and publishes a consolidated summary of outstanding assignments every Sunday at 5:00 PM WAT.
- **Duplicate Message Suppression:** Strictly prevents duplicate publications and duplicate reminder dispatches.
- **Deadline Modification Tracking:** Contextually associates follow-up messages (e.g., *"deadline moved to Wednesday"*) with existing assignments, updating reminders automatically.

---

## 📁 Repository Structure

```text
chirp/
├── backend/
│   ├── app/
│   │   ├── api/routes/          # REST & Webhook routes (health, webhook, assignments, admin)
│   │   ├── core/                # Config, async database session, security verification
│   │   ├── models/              # SQLAlchemy 2.0 DeclarativeBase entities
│   │   ├── schemas/             # Pydantic v2 validation and transfer schemas
│   │   ├── repositories/        # Clean data access layer (Assignment, Admin, Notification, Settings)
│   │   ├── integrations/
│   │   │   ├── ai/              # Provider abstraction (Gemini, OpenAI, Mock)
│   │   │   ├── storage/         # Storage abstraction (Local file storage & Supabase Storage)
│   │   │   └── whatsapp_gateway.py # HTTP client communicating with Baileys Gateway
│   │   ├── services/
│   │   │   ├── media_processing/       # Base64 decoder, PDF text extractor, storage writer
│   │   │   ├── assignment_detection/   # Heuristic & AI intent classifier
│   │   │   ├── assignment_extraction/  # Multimodal structured extractor
│   │   │   ├── assignment_review/      # Approval / rejection workflows
│   │   │   ├── assignment_publishing/  # Announcement builder conforming to PRD
│   │   │   ├── deadline_management/    # Timezone conversion & reminder math
│   │   │   ├── notifications/          # 24h reminders & Sunday digest builder
│   │   │   ├── admin_commands/         # In-chat interactive admin commands
│   │   │   └── orchestrator.py         # End-to-end incoming message coordinator
│   │   ├── scheduler/           # Persistent notification loop & Sunday digest worker
│   │   └── main.py              # FastAPI application entrypoint
│   ├── migrations/              # Alembic async database migrations
│   ├── tests/                   # Pytest test suite (100% passing)
│   └── requirements.txt
│
├── whatsapp-gateway/
│   ├── src/
│   │   ├── connection.ts        # Baileys socket & session handling
│   │   ├── message-handler.ts   # Normalizes incoming messages
│   │   ├── media-handler.ts     # Downloads media & converts to buffer/base64
│   │   ├── sender.ts            # Outbound text & media delivery
│   │   ├── webhook-client.ts    # Signed HTTP webhook client to FastAPI
│   │   ├── types.ts             # TypeScript interfaces
│   │   └── index.ts             # Express gateway server
│   ├── package.json
│   └── tsconfig.json
│
├── docker-compose.yml           # Complete containerized stack
├── .env.example                 # Documented environment variables
└── README.md
```

---

## 🛠️ Getting Started

### Prerequisites

- **Python 3.12+**
- **Node.js 20+**
- **PostgreSQL** (or SQLite for local dev/testing)

---

### Method 1: Local Development

#### 1. Setup Environment Variables
```bash
cp .env.example .env
```
Edit `.env` to configure your admin phone numbers, class group JID, and AI keys.

#### 2. Start the Backend
```bash
# Navigate to backend directory
cd backend

# Create virtual environment and activate
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start FastAPI server
uvicorn backend.app.main:app --reload --port 8000
```
Backend will be live at `http://localhost:8000`. API docs available at `http://localhost:8000/docs`.

#### 3. Start the WhatsApp Gateway
```bash
# In a new terminal, navigate to whatsapp-gateway
cd whatsapp-gateway

# Install dependencies
npm install

# Build TypeScript
npm run build

# Start Gateway
npm start
```
Upon startup, a **QR Code** will be printed in the terminal. Open WhatsApp on the bot's phone, navigate to **Linked Devices > Link a Device**, and scan the QR code. The session will be persistently saved in `whatsapp-gateway/auth_info_baileys`.

---

### Method 2: Docker Compose (Production Ready)

Run the entire stack with one command:
```bash
docker compose up -d --build
```
To view the QR code for WhatsApp linking:
```bash
docker compose logs -f gateway
```

---

## 💬 WhatsApp Admin Commands

Class representatives and administrators can manage assignments directly inside their private WhatsApp chat with the bot:

| Command | Description | Example |
|---|---|---|
| `/pending` | List all assignments awaiting administrator review | `/pending` |
| `/approve <ID>` | Approve candidate and publish announcement to class group | `/approve A7B2` |
| `/reject <ID> [reason]` | Reject candidate and prevent publication | `/reject A7B2 Invalid announcement` |
| `/edit <ID> [fields]` | Correct or modify assignment title, deadline, or course | `/edit A7B2 title=Updated Title deadline=2026-11-25` |
| `/upcoming` | List currently active upcoming deadlines | `/upcoming` |
| `/assignments` | List recently tracked assignments | `/assignments` |
| `/help` | Display command cheat sheet | `/help` |

> *Note: Only WhatsApp numbers registered in `INITIAL_ADMIN_JIDS` or added via the admin table are authorized to execute administrative commands.*

---

## 🧪 Running Tests

Chirp includes a thorough unit and integration test suite covering intent classification, multimodal extraction, deadline and timezone calculations, admin workflows, announcement formatting, weekly digests, and webhook idempotency.

```bash
cd backend
source .venv/bin/activate
pytest -v
```

---

## 🔒 Security & Best Practices

- **Shared Gateway Secret:** Inter-service communication between the WhatsApp Gateway and FastAPI backend is authenticated using the `X-Gateway-Secret` header with constant-time verification.
- **Idempotency & Duplicate Prevention:** Every WhatsApp message ID is indexed with unique constraints to prevent double-processing.
- **Timezone Reliability:** Internally stores all dates as UTC in the database, but strictly interprets and formats dates in `Africa/Lagos` (WAT) for Nigerian university contexts.
- **Non-blocking Scheduling:** APScheduler and persistent DB queues guarantee that reminders survive service restarts and disconnections.
- **Original Document Integrity:** Original attachments and student photos are preserved and stored securely without alteration.

---

## 📄 License
ISC / MIT
