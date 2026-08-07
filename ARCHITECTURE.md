# Architecture Notes

## Design principles

1. Original templates are immutable assets.
2. Document data is stored separately from template files.
3. Sequence allocation and document insertion occur in one immediate database transaction.
4. Permanent deletion is restricted to administrators and requires explicit confirmation.
5. Every critical operation creates an audit record.
6. Attachments are stored outside the database; metadata and SHA-256 digests are stored inside it.
7. Generated print files are derived artifacts and can be recreated from saved data.

## Runtime components

- FastAPI HTTP application.
- SQLite database with foreign keys, WAL mode, and revision history.
- Dependency-free browser frontend written in HTML/CSS/JavaScript.
- WeasyPrint-based HTML-to-PDF rendering with Arabic shaping.
- pypdf for deterministic page merging.
- Pillow for converting image attachments into printable A4 pages.
- LibreOffice integration for DOCX/ODT/RTF attachment conversion when installed.

## Security controls in this build

- Scrypt password hashing.
- Random bearer session tokens; only SHA-256 token hashes are stored.
- Role-based authorization at API endpoints.
- Content Security Policy and common browser security headers.
- File-size limits and sanitized attachment names.
- Attachment ownership validation during print bundle generation.
- Last-active-admin protection.
- No default credentials.
