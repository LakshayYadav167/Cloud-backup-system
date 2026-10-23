# Phased Development Roadmap

This document outlines the phased milestone progression for the **Cloud Backup System** college project. Every phase adheres strictly to the ₹0 budget mandate.

---

## Phase Breakdown

```mermaid
gantt
    title Cloud Backup System - Project Milestones
    dateFormat  YYYY-MM-DD
    section Phase 1
    Foundation & Monorepo Setup    :done, p1, 2026-10-23, 1d
    section Phase 2
    Backend Core & Storage Engine   :done, p2, 2026-10-23, 1d
    section Phase 3
    Frontend Dashboard & UI         :active, p3, after p2, 2d
    section Phase 4
    Automated Testing & Coverage    :p4, after p3, 2d
    section Phase 5
    Docker & Jenkins CI/CD Pipeline :p5, after p4, 2d
    section Phase 6
    Academic Documentation & Defense:p6, after p5, 1d
```

---

### Phase 1: Workspace Foundation & Baseline Standards (Completed)
- [x] Inspect root workspace and establish clean Git repository.
- [x] Create monorepo folder layout (`frontend/`, `backend/`, `docs/`, `docker/`).
- [x] Author comprehensive root `.gitignore` protecting secrets, virtual environments, node modules, and SQLite files.
- [x] Provide root, backend, and frontend `.env.example` templates.
- [x] Author technical architecture with Mermaid diagrams.
- [x] Lay down root `Jenkinsfile` skeleton for future local CI pipeline.
- [x] Establish minimal backend application scaffold (FastAPI health router, storage interface ABC).
- [x] Establish minimal frontend workspace configuration (Vite, TypeScript, Tailwind design tokens).

---

### Phase 2: Backend Core & Storage Engine (Completed)
- [x] SQLite database schema modeling `files`, `file_versions`, `backups`, and `backup_items` with foreign keys and WAL mode.
- [x] Implement `LocalFileSystemStorage` driver with path traversal prevention and atomic writing.
- [x] Implement optional `S3CompatibleStorage` driver using `boto3` for MinIO / LocalStack compatibility.
- [x] MinIO licensing analysis: verified AGPLv3 vs. commercial editions, zero-budget ₹0 guarantee, and SeaweedFS/LocalStack alternatives.
- [x] Implement file upload endpoint (`POST /api/v1/files/upload`) with SHA-256 calculation, unique immutable object keys, and version preservation.
- [x] Implement file listing (`GET /api/v1/files`) with substring search and pagination.
- [x] Implement file download (`GET /api/v1/files/{file_id}/download`) with ETag, Content-Disposition, and support for downloading historical versions.
- [x] Implement file version history (`GET /api/v1/files/{file_id}/versions`) and point-in-time restore (`POST /api/v1/files/{file_id}/restore/{version_id}`).
- [x] Implement file deletion (`DELETE /api/v1/files/{file_id}`) with physical object cleanup across all versions.
- [x] Implement storage metrics endpoint (`GET /api/v1/storage/stats`) with masked paths.
- [x] Implement backup snapshot trigger (`POST /api/v1/backups/trigger`) and audit history log (`GET /api/v1/backups/history`).
- [x] Comprehensive pytest test suite with 25 passing unit and integration tests using isolated temporary databases and storage directories.

---

### Phase 3: Frontend Implementation & Dashboard UI (Next)
- [ ] Connect React frontend components to actual `/api/v1` REST endpoints.
- [ ] Build drag-and-drop file upload zone with upload progress indicators.
- [ ] Build interactive files table with search, sorting, and single-click download/delete actions.
- [ ] Build version drawer to inspect historical backup versions and trigger one-click restore.
- [ ] Build storage statistics panel with capacity usage bar and file distribution breakdown.
- [ ] Build backup history audit view with manual trigger action button.

---

### Phase 4: Automated Testing & Verification
- [ ] Frontend unit & component tests using `Vitest` and `React Testing Library`.
- [ ] End-to-end integration tests (Upload -> View in table -> Check stats -> Trigger backup -> Download file -> Restore previous version).

---

### Phase 5: Containerization & Local Jenkins CI/CD
- [ ] Create production-ready `Dockerfile` for backend (multi-stage Python runtime).
- [ ] Create production-ready `Dockerfile` for frontend (multi-stage Vite build + Nginx alpine).
- [ ] Author `docker-compose.yml` linking frontend, backend, and optional local MinIO container.
- [ ] Configure local Jenkins pipeline via `Jenkinsfile` for automated build and test quality gates.

---

### Phase 6: Final Hardening, Submission Documentation & Demo Preparation
- [ ] Prepare comprehensive Project Report (PDF/Markdown format) meeting college submission standards.
- [ ] Add Resume Showcase Section: architecture highlights, key technical decisions, zero-budget engineering.
- [ ] Create presentation script & video demonstration guide.
