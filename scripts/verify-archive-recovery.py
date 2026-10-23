#!/usr/bin/env python3
"""Phase 8 Genuine Portable Archive Recovery & Isolation Verification Script.

Executes a full, isolated disaster-recovery audit:
1. Provisions temporary source SQLite database and storage directory.
2. Creates multi-version file assets.
3. Exports a portable ZIP archive.
4. Verifies manifest structure and SHA-256 digests.
5. Provisions a completely separate, clean target database and storage directory.
6. Tests corrupted archive rejection (verifying zero destination modifications).
7. Tests path traversal / unsafe archive entry rejection (verifying zero destination modifications).
8. Restores the valid archive into the isolated target environment.
9. Validates recovered file contents, active version pointer, historical versions, and checksums.
10. Automatically cleans up all temporary directories, leaving actual application data untouched.
"""

from io import BytesIO
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys
import tempfile
import zipfile

# Add backend directory to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.database import get_db, init_db, get_db_connection
from app.main import app as main_app
from app.storage.local import LocalFileSystemStorage
from app.services.archive_service import ArchiveService


def run_isolated_recovery_audit() -> bool:
    print("=" * 80)
    print("  PHASE 8: INDEPENDENT PORTABLE ARCHIVE RECOVERY AUDIT")
    print("=" * 80)

    # Create root temporary workspace
    temp_dir = Path(tempfile.mkdtemp(prefix="cloud_backup_recovery_audit_"))
    print(f"[*] Isolated temporary workspace created at: {temp_dir}")

    try:
        source_dir = temp_dir / "source"
        source_db_path = source_dir / "source_backup.db"
        source_storage_dir = source_dir / "storage"
        source_storage_dir.mkdir(parents=True, exist_ok=True)

        target_dir = temp_dir / "target"
        target_db_path = target_dir / "target_recovery.db"
        target_storage_dir = target_dir / "storage"
        target_storage_dir.mkdir(parents=True, exist_ok=True)

        # Save original settings
        orig_storage_path = settings.LOCAL_STORAGE_PATH
        orig_storage_provider = settings.STORAGE_PROVIDER

        # ----------------------------------------------------------------------
        # STEP 1: Set up Source Environment & Create Multi-Version Asset
        # ----------------------------------------------------------------------
        print("\n--- STEP 1: Setting up Source Environment ---")
        settings.LOCAL_STORAGE_PATH = str(source_storage_dir)
        settings.STORAGE_PROVIDER = "local"

        src_conn = get_db_connection(str(source_db_path))
        init_db(src_conn)
        src_conn.close()

        def get_source_db():
            conn = get_db_connection(str(source_db_path))
            try:
                yield conn
            finally:
                conn.close()

        # Temporary app overrides for source
        main_app.dependency_overrides[get_db] = get_source_db
        src_client = TestClient(main_app)

        v1_payload = b"# Disaster Recovery Test Document v1\nInitial content for capstone audit.\n"
        v2_payload = b"# Disaster Recovery Test Document v2\nUpdated content with architecture changes.\n"
        v1_sha = hashlib.sha256(v1_payload).hexdigest()
        v2_sha = hashlib.sha256(v2_payload).hexdigest()

        print("  Uploading version 1 of 'disaster_recovery_spec.md'...")
        r1 = src_client.post(
            "/api/v1/files/upload?change_summary=Version+1+Draft",
            files={"file": ("disaster_recovery_spec.md", BytesIO(v1_payload), "text/markdown")},
        )
        assert r1.status_code == 201, f"Failed v1 upload: {r1.text}"

        print("  Uploading version 2 of 'disaster_recovery_spec.md'...")
        r2 = src_client.post(
            "/api/v1/files/upload?change_summary=Version+2+Final",
            files={"file": ("disaster_recovery_spec.md", BytesIO(v2_payload), "text/markdown")},
        )
        assert r2.status_code == 201, f"Failed v2 upload: {r2.text}"

        print("  Uploading second file 'incident_runbook.json'...")
        runbook_payload = b'{"procedure": "failover", "priority": "high", "timeout_sec": 30}'
        r3 = src_client.post(
            "/api/v1/files/upload",
            files={"file": ("incident_runbook.json", BytesIO(runbook_payload), "application/json")},
        )
        assert r3.status_code == 201, f"Failed runbook upload: {r3.text}"

        # ----------------------------------------------------------------------
        # STEP 2: Export Portable Backup Archive (.zip)
        # ----------------------------------------------------------------------
        print("\n--- STEP 2: Exporting Portable Backup Archive ---")
        export_resp = src_client.get("/api/v1/archives/export?notes=Phase+8+Genuine+Disaster+Recovery+Verification")
        assert export_resp.status_code == 200, f"Export failed: {export_resp.text}"
        archive_bytes = export_resp.content
        print(f"  Archive generated successfully ({len(archive_bytes)} bytes).")

        # ----------------------------------------------------------------------
        # STEP 3: Verify Archive Structure, Format & SHA-256 Digests
        # ----------------------------------------------------------------------
        print("\n--- STEP 3: Verifying Archive Internal Manifest & Hashes ---")
        with zipfile.ZipFile(BytesIO(archive_bytes), mode="r") as zf:
            assert "manifest.json" in zf.namelist(), "Missing manifest.json"
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
            assert manifest["archive_format_version"] == "1.0.0"
            assert manifest["total_files"] == 2
            assert manifest["total_versions"] == 3
            print(f"  Format version: {manifest['archive_format_version']}")
            print(f"  Total declared files: {manifest['total_files']}, versions: {manifest['total_versions']}")

            # Verify individual blobs
            spec_file = next(f for f in manifest["files"] if f["filename"] == "disaster_recovery_spec.md")
            assert len(spec_file["versions"]) == 2
            v1_meta = next(v for v in spec_file["versions"] if v["version_number"] == 1)
            v2_meta = next(v for v in spec_file["versions"] if v["version_number"] == 2)
            assert v1_meta["sha256"] == v1_sha
            assert v2_meta["sha256"] == v2_sha

            v1_blob = zf.read(v1_meta["archive_path"])
            v2_blob = zf.read(v2_meta["archive_path"])
            assert v1_blob == v1_payload, "Extracted v1 payload does not match original"
            assert v2_blob == v2_payload, "Extracted v2 payload does not match original"
            print("  All uncompressed payloads cryptographically verified.")

        # ----------------------------------------------------------------------
        # STEP 4: Switch to Isolated, Clean Target Environment
        # ----------------------------------------------------------------------
        print("\n--- STEP 4: Switching to Clean Target Environment ---")
        settings.LOCAL_STORAGE_PATH = str(target_storage_dir)
        settings.STORAGE_PROVIDER = "local"

        tgt_conn = get_db_connection(str(target_db_path))
        init_db(tgt_conn)
        tgt_conn.close()

        def get_target_db():
            conn = get_db_connection(str(target_db_path))
            try:
                yield conn
            finally:
                conn.close()

        main_app.dependency_overrides[get_db] = get_target_db
        tgt_client = TestClient(main_app)

        # Confirm target is completely empty
        initial_list = tgt_client.get("/api/v1/files").json()
        assert initial_list["total"] == 0, "Target environment is not empty!"
        print("  Confirmed target environment is 100% clean (0 files, 0 versions).")

        # ----------------------------------------------------------------------
        # STEP 5: Test Corrupted Archive Rejection & Zero Catalog Mutation
        # ----------------------------------------------------------------------
        print("\n--- STEP 5: Testing Corrupted Archive Rejection ---")
        corrupted_buf = BytesIO()
        with zipfile.ZipFile(BytesIO(archive_bytes), "r") as z_in, zipfile.ZipFile(corrupted_buf, "w") as z_out:
            for item in z_in.infolist():
                content = z_in.read(item.filename)
                if "disaster_recovery_spec" in item.filename:
                    # Tamper with byte content to invalidate SHA-256
                    content = content + b"\nTAMPERED_MALICIOUS_BYTE"
                z_out.writestr(item, content)

        corrupted_buf.seek(0)
        corrupt_resp = tgt_client.post(
            "/api/v1/archives/restore",
            files={"file": ("corrupt.zip", corrupted_buf, "application/zip")},
            data={"conflict_strategy": "rename"},
        )
        assert corrupt_resp.status_code == 400, f"Expected 400 on corrupted archive, got: {corrupt_resp.status_code}"
        print("  Corrupted archive properly rejected with HTTP 400.")

        # Confirm zero target modification
        post_corrupt_list = tgt_client.get("/api/v1/files").json()
        assert post_corrupt_list["total"] == 0, "Corrupted archive modified target catalog!"
        print("  Confirmed zero partial files or records imported into target.")

        # ----------------------------------------------------------------------
        # STEP 6: Test Unsafe Archive Entry (Path Traversal) Rejection
        # ----------------------------------------------------------------------
        print("\n--- STEP 6: Testing Unsafe Archive Entry Rejection ---")
        unsafe_buf = BytesIO()
        with zipfile.ZipFile(unsafe_buf, "w") as z_out:
            z_out.writestr("manifest.json", json.dumps({"archive_format_version": "1.0.0", "files": []}))
            z_out.writestr("../../../etc/passwd", b"root:x:0:0::/root:/bin/bash\n")

        unsafe_buf.seek(0)
        unsafe_resp = tgt_client.post(
            "/api/v1/archives/restore",
            files={"file": ("unsafe.zip", unsafe_buf, "application/zip")},
            data={"conflict_strategy": "rename"},
        )
        assert unsafe_resp.status_code == 400, f"Expected 400 on unsafe archive, got: {unsafe_resp.status_code}"
        print("  Path traversal archive entry properly rejected with HTTP 400.")

        # Confirm zero target modification
        post_unsafe_list = tgt_client.get("/api/v1/files").json()
        assert post_unsafe_list["total"] == 0, "Unsafe archive modified target catalog!"
        print("  Confirmed target catalog remains completely clean.")

        # ----------------------------------------------------------------------
        # STEP 7: Restore Valid Archive into Clean Target Environment
        # ----------------------------------------------------------------------
        print("\n--- STEP 7: Restoring Valid Archive into Target Environment ---")
        restore_resp = tgt_client.post(
            "/api/v1/archives/restore",
            files={"file": ("valid_backup.zip", BytesIO(archive_bytes), "application/zip")},
            data={"conflict_strategy": "rename"},
        )
        assert restore_resp.status_code == 200, f"Valid restore failed: {restore_resp.text}"
        restore_data = restore_resp.json()
        assert restore_data["success"] is True
        assert restore_data["imported_files_count"] == 2
        assert restore_data["imported_versions_count"] == 3
        print(f"  Restore successful: {restore_data['imported_files_count']} files, {restore_data['imported_versions_count']} versions imported.")

        # ----------------------------------------------------------------------
        # STEP 8: Verify Recovered Content in Isolated System
        # ----------------------------------------------------------------------
        print("\n--- STEP 8: Verifying Recovered File Content & Version History ---")
        target_files = tgt_client.get("/api/v1/files").json()
        assert target_files["total"] == 2, f"Expected 2 recovered files, found {target_files['total']}"

        spec_file_tgt = next(f for f in target_files["items"] if f["filename"] == "disaster_recovery_spec.md")
        assert spec_file_tgt["total_versions"] == 2, "Expected 2 versions"
        assert spec_file_tgt["current_version_number"] == 2, "Active version must be v2"
        print("  Target file metadata and active version pointer validated.")

        # Download active version (v2) from target instance
        dl_v2 = tgt_client.get(f"/api/v1/files/{spec_file_tgt['id']}/download")
        assert dl_v2.status_code == 200
        assert dl_v2.content == v2_payload, "Recovered v2 content does not match original"
        print("  Active version payload (v2) matches byte-for-byte.")

        # Download historical version (v1) from target instance
        versions_tgt = tgt_client.get(f"/api/v1/files/{spec_file_tgt['id']}/versions").json()
        v1_tgt_meta = next(v for v in versions_tgt if v["version_number"] == 1)
        dl_v1 = tgt_client.get(f"/api/v1/files/{spec_file_tgt['id']}/download?version_id={v1_tgt_meta['id']}")
        assert dl_v1.status_code == 200
        assert dl_v1.content == v1_payload, "Recovered v1 content does not match original"
        print("  Historical version payload (v1) matches byte-for-byte.")

        # Download second file (incident_runbook.json)
        runbook_tgt = next(f for f in target_files["items"] if f["filename"] == "incident_runbook.json")
        dl_rb = tgt_client.get(f"/api/v1/files/{runbook_tgt['id']}/download")
        assert dl_rb.status_code == 200
        assert dl_rb.content == runbook_payload, "Runbook payload mismatch"
        print("  Runbook file matches byte-for-byte.")

        print("\n" + "=" * 80)
        print("  ALL 8 ISOLATED RECOVERY AUDIT STEPS PASSED SUCCESSFULLY!")
        print("=" * 80)
        return True

    finally:
        # Reset dependency overrides and restored settings
        main_app.dependency_overrides.clear()
        settings.LOCAL_STORAGE_PATH = orig_storage_path
        settings.STORAGE_PROVIDER = orig_storage_provider
        # Clean up temporary directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
            print(f"[*] Ephemeral test environment cleaned up cleanly: {temp_dir}\n")


if __name__ == "__main__":
    success = run_isolated_recovery_audit()
    sys.exit(0 if success else 1)
