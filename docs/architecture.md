# System Architecture & Technical Design

## 1. Executive Summary & Objective

**Cloud Backup System** is an enterprise-grade, self-hosted file backup and storage management application built under strict **₹0 budget constraints** for academic evaluation, portfolio presentation, and resume building.

The system empowers users to:
- Upload and inspect files through a modern, responsive web dashboard.
- Monitor real-time local storage metrics, quota consumption, and file distribution.
- Track automated backup snapshots and historical restore points.
- Benefit from a modular storage provider abstraction layer that runs seamlessly on the local filesystem today while remaining 100% pluggable for object storage (e.g., MinIO or S3) in the future.

---

## 2. Zero-Budget Philosophy (₹0 Spent)

Every component is intentionally selected to require **no credit card, no cloud provider account, no subscription, and no paid third-party API**:

| Subsystem | Selection | Justification |
| :--- | :--- | :--- |
| **Frontend** | React 19 + Vite + TypeScript + Tailwind CSS | Fast compilation, modern UX, open source, zero licensing fees. |
| **Backend** | Python 3 + FastAPI + Uvicorn | High-throughput asynchronous REST API, auto-generated OpenAPI docs. |
| **Database** | SQLite 3 | Serverless, zero-maintenance, zero-cost embedded relational engine. |
| **File Storage** | Local Host Filesystem | Zero storage egress or bucket cost; abstracted behind a generic interface. |
| **Testing** | pytest + Vitest | Industry-standard open-source testing frameworks. |
| **CI / CD** | Local Jenkins Pipeline | Automated build and test pipeline running locally on port 8080. |
| **Containerization** | Docker & Docker Compose | Multi-container reproducible runtime without cloud registry fees. |

---

## 3. High-Level Architecture Diagram

The system follows a decoupled, three-tier architecture with an abstract storage provider layer:

```mermaid
graph TB
    subgraph Client_Tier["Client Presentation Tier (Browser)"]
        UI["React 19 + Vite + TypeScript"]
        Tailwind["Tailwind CSS Design System<br/>(Light Surface, Navy Text, Green Accents)"]
        Dashboard["Dashboard Modules:<br/>Upload Zone | File Grid | Metrics | Backup Log"]
        UI --> Tailwind
        UI --> Dashboard
    end

    subgraph API_Gateway["Communication & Network Tier"]
        HTTP_Client["Axios / Fetch API"]
        CORS["CORS Middleware (Port 5173 &rarr; Port 8000)"]
        REST["RESTful Endpoints (/api/v1)"]
        Dashboard --> HTTP_Client
        HTTP_Client -->|HTTP/JSON & Multipart| CORS
        CORS --> REST
    end

    subgraph Backend_Tier["Backend Application Tier (FastAPI)"]
        App["FastAPI Core Engine"]
        Routers["Routers (/files, /storage, /backups, /health)"]
        Services["Service Domain Layer:<br/>FileService | BackupManager | MetricsCollector"]
        Security["Validation & Sanitization (Pydantic v2)"]
        
        REST --> App
        App --> Routers
        Routers --> Security
        Security --> Services
    end

    subgraph Storage_Tier["Data & Persistence Tier"]
        DB_Interface["SQLite Engine (Database Layer)"]
        SQLite_File[("cloud_backup.db<br/>Metadata & Audit History")]
        
        Storage_ABC["StorageProvider (Abstract Base Class)"]
        Local_Driver["LocalFileSystemStorage Driver"]
        Future_Driver["[Future Extension]<br/>MinIO / S3 Compatible Driver"]
        
        FS_Storage[("Local Disk Directory<br/>backend/data/storage/")]
        
        Services --> DB_Interface
        DB_Interface --> SQLite_File
        
        Services --> Storage_ABC
        Storage_ABC -.->|Active Implementation| Local_Driver
        Storage_ABC -.->|Future Drop-in| Future_Driver
        Local_Driver --> FS_Storage
    end

    subgraph Automation_Tier["DevOps & CI/CD Tier (₹0 Self-Hosted)"]
        GitRepo["Git Repository (Local & GitHub)"]
        Jenkins["Jenkins Local Server (Port 8080)"]
        Docker["Docker Engine & Compose"]
        
        GitRepo -->|Trigger Webhook / Poll| Jenkins
        Jenkins -->|Run Tests & Lint| Backend_Tier
        Jenkins -->|Build & Verify| Client_Tier
        Jenkins -->|Package Images| Docker
    end

    style Client_Tier fill:#f8fafc,stroke:#334155,stroke-width:1px
    style Backend_Tier fill:#f0fdf4,stroke:#16a34a,stroke-width:1px
    style Storage_Tier fill:#f1f5f9,stroke:#0284c7,stroke-width:1px
    style Automation_Tier fill:#fefce8,stroke:#ca8a04,stroke-width:1px
```

---

## 4. Key Component Breakdown

### 4.1 Frontend Tier (`frontend/`)
- **Technology**: React 19, Vite, TypeScript, Tailwind CSS, Lucide React icons.
- **Visual Design Identity**:
  - **Background**: Crisp clean light surfaces (`#f8fafc`, `#ffffff`).
  - **Typography & Structural Elements**: Deep navy blue (`#0f172a`, `#1e293b`).
  - **Accent & Actions**: Emerald & mint greens (`#10b981`, `#059669`, `#34d399`) representing health, backup integrity, and secure status.
- **Key Modules**:
  1. *Quick Stats Banner*: Total storage utilized, file count, and last successful backup timestamp.
  2. *Interactive Drag & Drop Upload Zone*: Real-time file validation (extension, size, hashing).
  3. *Files Inventory Table*: Sortable, searchable listing with metadata (name, size, mime type, hash, creation date).
  4. *Backup History & Trigger*: Instant manual snapshot trigger with chronological audit table.

### 4.2 Backend Tier (`backend/`)
- **Technology**: Python 3.10+, FastAPI, Uvicorn, Pydantic v2.
- **Responsibilities**:
  - Request validation, multipart streaming for memory-efficient uploads.
  - Computing cryptographic hashes (SHA-256) for deduplication and file verification.
  - Exposing structured JSON responses adhering to OpenAPI / Swagger standards (`/docs`).
  - Graceful error handling and standardized response envelopes.

### 4.3 Database & Metadata Tier (`backend/app/db/`)
- **Engine**: SQLite 3 with WAL (Write-Ahead Logging) enabled for concurrency.
- **Primary Entities**:
  - `files`: File ID (UUID), original filename, stored filename, file size, SHA-256 hash, mime type, creation timestamp, status.
  - `backups`: Backup ID, snapshot timestamp, total files count, total size bytes, checksum, status (COMPLETED, FAILED).
  - `backup_items`: Join table linking files to specific backup snapshots.

### 4.4 Storage Abstraction Layer (`backend/app/storage/`)
- A strict interface (`StorageProvider`) isolates application logic from physical disk operations:
  ```python
  class StorageProvider(ABC):
      async def save_file(self, file_id: str, content: BinaryIO) -> StoredFileInfo: ...
      async def get_file(self, file_id: str) -> BinaryIO: ...
      async def delete_file(self, file_id: str) -> bool: ...
      async def get_stats(self) -> StorageStats: ...
  ```
- Current Implementation: `LocalFileSystemStorage` writes to `backend/data/storage/`.
- Future compatibility: Changing storage backends requires zero changes to routers or business logic.

---

## 5. Security & Reliability Guidelines
- **Path Traversal Protection**: Uploaded files are renamed using secure UUID v4 tokens on disk; original filenames are stored in the SQLite database only.
- **MIME & Extension Sanitization**: Validation occurs before committing payloads to disk.
- **CORS Safeguards**: Strict origin headers allow only trusted local dev ports (`http://localhost:5173`, `http://127.0.0.1:5173`).
- **Secret Isolation**: Configuration is decoupled via `.env` with `.env.example` templates committed without secrets.
