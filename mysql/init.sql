-- ============================================================
-- DocSign Platform — MySQL 8 Initialization Script
-- Runs once on first container startup via docker-entrypoint
-- ============================================================

-- Use utf8mb4 throughout for full Unicode support (emoji, special chars in names)
ALTER DATABASE docsign CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE docsign;

-- ─── Roles ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS roles (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    -- JSON array of permission strings e.g. ["create_document","sign_document"]
    permissions JSON         NOT NULL DEFAULT ('[]'),
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── Users ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id                  CHAR(36)    NOT NULL PRIMARY KEY,       -- UUID
    email               VARCHAR(255) NOT NULL UNIQUE,
    full_name           VARCHAR(255),
    title               VARCHAR(100),                           -- Job title
    department          VARCHAR(100),
    password_hash       TEXT        NOT NULL,
    mfa_secret          TEXT        NULL,                       -- Fernet-encrypted TOTP secret
    mfa_enabled         BOOLEAN     NOT NULL DEFAULT FALSE,
    -- RSA+Fernet encrypted PNG bytes of the user's registered signature
    signature_encrypted LONGBLOB    NULL,
    signature_iv        TEXT        NULL,                       -- Encryption metadata / key derivation info
    identity_verified   BOOLEAN     NOT NULL DEFAULT FALSE,
    is_active           BOOLEAN     NOT NULL DEFAULT TRUE,
    force_password_change BOOLEAN   NOT NULL DEFAULT FALSE,     -- Admin-created accounts must change password
    created_at          DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── User Roles (many-to-many junction) ──────────────────────
CREATE TABLE IF NOT EXISTS user_roles (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     CHAR(36)    NOT NULL,
    role_id     INT         NOT NULL,
    assigned_by CHAR(36)    NULL,   -- NULL when seeded/self-assigned
    assigned_at DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)     REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id)     REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_by) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE KEY uq_user_role (user_id, role_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── Documents ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS documents (
    id              CHAR(36)        NOT NULL PRIMARY KEY,
    title           VARCHAR(255)    NOT NULL,
    to_field        TEXT            NOT NULL,
    cc_field        TEXT            NULL,
    ref_field       VARCHAR(255)    NULL,
    subject         VARCHAR(500)    NOT NULL,
    body            LONGTEXT        NOT NULL,
    created_by      CHAR(36)        NOT NULL,
    -- Server-set timestamp — legal document records must never use client time
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    locked_at       DATETIME        NULL,     -- Set when document sent for signing
    status          ENUM('draft','in_signing','completed','recalled') NOT NULL DEFAULT 'draft',
    -- SHA-256 of the content JSON at lock time — used to detect tampering
    content_hash    CHAR(64)        NULL,
    final_pdf_path  TEXT            NULL,
    -- SHA-256 of the generated PDF bytes for authenticity verification
    pdf_hash        CHAR(64)        NULL,
    FOREIGN KEY (created_by) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── Document Signatories ────────────────────────────────────
CREATE TABLE IF NOT EXISTS document_signatories (
    id                      INT AUTO_INCREMENT PRIMARY KEY,
    document_id             CHAR(36) NOT NULL,
    user_id                 CHAR(36) NOT NULL,
    order_index             INT      NOT NULL,   -- Sequential signing order (1-based)
    is_final_decision_maker BOOLEAN  NOT NULL DEFAULT FALSE,
    -- waiting = not yet this person's turn; pending = currently active signatory
    status                  ENUM('pending','signed','recommended','not_recommended','waiting') NOT NULL DEFAULT 'waiting',
    recommendation_note     TEXT     NULL,
    notified_at             DATETIME NULL,       -- When signatory email was sent
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)     REFERENCES users(id),
    UNIQUE KEY uq_doc_user (document_id, user_id),
    UNIQUE KEY uq_doc_order (document_id, order_index)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── Signatures ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS signatures (
    id                      CHAR(36)    NOT NULL PRIMARY KEY,
    document_id             CHAR(36)    NOT NULL,
    user_id                 CHAR(36)    NOT NULL,
    -- Server timestamp — legally significant, never from client
    signed_at               DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- Snapshot of decrypted signature at signing time.
    -- Stored separately from user's profile signature so that future signature
    -- updates don't retroactively alter historical signed documents.
    signature_image_snapshot LONGBLOB   NOT NULL,
    recommendation          ENUM('recommended','not_recommended','none') NOT NULL DEFAULT 'none',
    note                    TEXT        NULL,
    ip_address              VARCHAR(45) NOT NULL,
    user_agent              TEXT        NULL,
    -- Confirms MFA was successfully verified immediately before signing
    mfa_verified            BOOLEAN     NOT NULL DEFAULT FALSE,
    FOREIGN KEY (document_id) REFERENCES documents(id),
    FOREIGN KEY (user_id)     REFERENCES users(id),
    -- Prevent double-signing: one signature record per user per document
    UNIQUE KEY uq_doc_user_sig (document_id, user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── Audit Logs ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_logs (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    document_id CHAR(36)     NULL,
    user_id     CHAR(36)     NULL,
    action      VARCHAR(100) NOT NULL,
    -- JSON object with extra context (e.g. {"signatory_count": 3})
    metadata    JSON         NULL,
    ip_address  VARCHAR(45)  NOT NULL DEFAULT '0.0.0.0',
    -- Server timestamp — audit records are legal evidence, must be server-generated
    timestamp   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE SET NULL,
    FOREIGN KEY (user_id)     REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─── Audit Log Immutability Triggers ─────────────────────────
-- These triggers enforce append-only semantics at the DB level.
-- Even if application code has a bug, the DB will reject any modification.
DELIMITER $$

CREATE TRIGGER audit_logs_prevent_update
BEFORE UPDATE ON audit_logs
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = 'Audit log records are immutable and cannot be updated';
END$$

CREATE TRIGGER audit_logs_prevent_delete
BEFORE DELETE ON audit_logs
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = 'Audit log records are immutable and cannot be deleted';
END$$

DELIMITER ;

-- ─── Seed Data ───────────────────────────────────────────────
-- Roles with their permission sets
INSERT IGNORE INTO roles (name, permissions) VALUES
('Admin',    '["manage_users","manage_roles","view_all_documents","create_document","sign_document"]'),
('Director', '["view_all_documents","create_document","sign_document"]'),
('Head of Department', '["create_document","sign_document","view_department_documents"]'),
('Officer',  '["create_document","sign_document"]'),
('Clerk',    '["sign_document"]');

-- Default Admin user
-- Password: Admin@12345 (bcrypt hash generated externally, force_password_change=TRUE)
-- The auth service seed script will insert this with a proper bcrypt hash on startup
-- We use a placeholder here; the Python service overwrites it on first boot
INSERT IGNORE INTO users (
    id, email, full_name, title, department,
    password_hash, is_active, force_password_change, created_at
) VALUES (
    '00000000-0000-0000-0000-000000000001',
    'admin@docsign.local',
    'System Administrator',
    'System Administrator',
    'IT',
    -- bcrypt hash of 'Admin@12345' with cost factor 12 (pre-computed for seed speed)
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMlJVtZC6k0T9JkZo1M4OT8FaK',
    TRUE,
    TRUE,   -- Force password change on first login
    NOW()
);

-- Assign Admin role to admin user
INSERT IGNORE INTO user_roles (user_id, role_id, assigned_by)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    (SELECT id FROM roles WHERE name = 'Admin'),
    NULL
);

-- Seed audit log for initial system setup
INSERT INTO audit_logs (document_id, user_id, action, metadata, ip_address)
VALUES (NULL, '00000000-0000-0000-0000-000000000001', 'system_initialized',
        '{"version": "1.0.0", "seed": true}', '127.0.0.1');
