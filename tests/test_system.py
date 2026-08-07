from __future__ import annotations

import io
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfReader

TEST_DATA = Path(__file__).resolve().parent / ".test-data"
os.environ["ZIAD_DATA_DIR"] = str(TEST_DATA)

from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def clean_data():
    if TEST_DATA.exists():
        import shutil
        shutil.rmtree(TEST_DATA)
    TEST_DATA.mkdir(parents=True, exist_ok=True)
    yield


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_full_document_lifecycle():
    with TestClient(app) as client:
        assert client.get("/api/setup/status").json() == {"needs_setup": True}
        setup = client.post(
            "/api/setup/admin",
            json={"full_name": "System Admin", "username": "admin", "password": "StrongPass123!"},
        )
        assert setup.status_code == 201

        login = client.post("/api/auth/login", json={"username": "admin", "password": "StrongPass123!"})
        assert login.status_code == 200
        token = login.json()["token"]
        headers = auth_headers(token)

        types = client.get("/api/document-types", headers=headers)
        assert types.status_code == 200
        assert {item["code"] for item in types.json()} == {"RV", "PR", "PV", "VM"}

        vehicle = client.post(
            "/api/documents",
            headers=headers,
            json={
                "type_code": "VM",
                "status": "draft",
                "fields": {"maintenance_date": "2026-08-06", "vehicle": "سيارة اختبار"},
            },
        )
        assert vehicle.status_code == 201, vehicle.text
        assert vehicle.json()["document_number"] == "VM-000001"
        assert vehicle.json()["fields"]["vehicle"] == "سيارة اختبار"

        created = client.post(
            "/api/documents",
            headers=headers,
            json={"type_code": "RV", "status": "draft", "fields": {"date": "2026-08-03", "received_from": "شركة الاختبار"}},
        )
        assert created.status_code == 201, created.text
        document = created.json()
        assert document["document_number"] == "RV-000001"
        assert document["fields"]["document_number"] == "RV-000001"

        second = client.post("/api/documents", headers=headers, json={"type_code": "RV", "status": "draft", "fields": {}})
        assert second.json()["document_number"] == "RV-000002"

        updated = client.put(
            f"/api/documents/{document['id']}",
            headers=headers,
            json={
                "status": "saved",
                "fields": {
                    "date": "2026-08-03",
                    "received_from": "شركة الاختبار",
                    "currency": "USD",
                    "amount": "1250",
                    "written_amount": "ألف ومئتان وخمسون دولاراً",
                    "about": "دفعة اختبار",
                    "receiver_name": "علي",
                },
            },
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["revision"] == 2
        assert updated.json()["status"] == "saved"

        image = Image.new("RGB", (200, 120), "white")
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        upload = client.post(
            f"/api/documents/{document['id']}/attachments",
            headers={**headers, "X-File-Name": "receipt.png", "Content-Type": "image/png"},
            content=buffer.getvalue(),
        )
        assert upload.status_code == 201, upload.text
        attachment_id = upload.json()["id"]

        fetched = client.get(f"/api/documents/{document['id']}", headers=headers)
        assert fetched.status_code == 200
        assert len(fetched.json()["attachments"]) == 1

        printed = client.post(
            f"/api/documents/{document['id']}/print",
            headers=headers,
            json={"attachment_ids": [attachment_id]},
        )
        assert printed.status_code == 200, printed.text
        assert printed.headers["content-type"].startswith("application/pdf")
        reader = PdfReader(io.BytesIO(printed.content))
        assert len(reader.pages) >= 2
        for page in reader.pages:
            width_mm = float(page.mediabox.width) * 25.4 / 72
            height_mm = float(page.mediabox.height) * 25.4 / 72
            assert width_mm == pytest.approx(210, abs=0.2)
            assert height_mm == pytest.approx(297, abs=0.2)

        wrong_delete = client.request(
            "DELETE",
            f"/api/documents/{document['id']}/permanent",
            headers=headers,
            json={"confirmation": "delete"},
        )
        assert wrong_delete.status_code == 422
        deleted = client.request(
            "DELETE",
            f"/api/documents/{document['id']}/permanent",
            headers=headers,
            json={"confirmation": "حذف نهائي"},
        )
        assert deleted.status_code == 200
        assert client.get(f"/api/documents/{document['id']}", headers=headers).status_code == 404


def test_users_and_permissions():
    with TestClient(app) as client:
        client.post("/api/setup/admin", json={"full_name": "Admin", "username": "admin", "password": "StrongPass123!"})
        token = client.post("/api/auth/login", json={"username": "admin", "password": "StrongPass123!"}).json()["token"]
        admin_headers = auth_headers(token)
        new_user = client.post(
            "/api/users",
            headers=admin_headers,
            json={"full_name": "Viewer User", "username": "viewer", "password": "ViewerPass123!", "role": "viewer"},
        )
        assert new_user.status_code == 201
        viewer_token = client.post("/api/auth/login", json={"username": "viewer", "password": "ViewerPass123!"}).json()["token"]
        viewer_headers = auth_headers(viewer_token)
        assert client.get("/api/documents", headers=viewer_headers).status_code == 200
        assert client.post("/api/documents", headers=viewer_headers, json={"type_code": "PR", "fields": {}}).status_code == 403
        assert client.get("/api/users", headers=viewer_headers).status_code == 403


def test_system_status_and_backup():
    import json
    import zipfile

    with TestClient(app) as client:
        client.post('/api/setup/admin', json={'full_name':'Admin','username':'admin','password':'StrongPass123!'})
        token = client.post('/api/auth/login', json={'username':'admin','password':'StrongPass123!'}).json()['token']
        headers = auth_headers(token)
        client.post('/api/documents', headers=headers, json={'type_code':'PR','status':'saved','fields':{'amount':'100'}})

        status_response = client.get('/api/system/status', headers=headers)
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data['version'] == '3.3.4'
        assert status_data['database']['ok'] is True
        assert status_data['counts']['documents'] == 1
        assert len(status_data['templates']) == 10
        assert all(item['ok'] is True for item in status_data['templates'])

        backup = client.post('/api/system/backup', headers=headers)
        assert backup.status_code == 200
        assert backup.headers['content-type'].startswith('application/zip')
        archive_path = TEST_DATA / 'test-backup.zip'
        archive_path.write_bytes(backup.content)
        with zipfile.ZipFile(archive_path) as archive:
            names = set(archive.namelist())
            assert 'database/ziad_documents.sqlite3' in names
            assert 'manifest.json' in names
            assert 'templates/receipt-voucher.docx' in names
            assert 'templates/originals/receipt-voucher-original.docx' in names
            assert 'app/static/templates/receipt-voucher.png' in names
            manifest = json.loads(archive.read('manifest.json'))
            assert manifest['version'] == '3.3.4'
            assert manifest['files']


def test_account_lockout_and_password_change():
    with TestClient(app) as client:
        client.post('/api/setup/admin', json={'full_name':'Admin','username':'admin','password':'StrongPass123!'})
        for _ in range(5):
            response = client.post('/api/auth/login', json={'username':'admin','password':'wrong-password'})
            assert response.status_code == 401
        locked = client.post('/api/auth/login', json={'username':'admin','password':'StrongPass123!'})
        assert locked.status_code == 423

        from app.db import connect
        conn = connect()
        try:
            conn.execute("UPDATE users SET locked_until=NULL, failed_login_count=0 WHERE username='admin'")
        finally:
            conn.close()

        login = client.post('/api/auth/login', json={'username':'admin','password':'StrongPass123!'})
        assert login.status_code == 200
        token = login.json()['token']
        changed = client.post('/api/auth/change-password', headers=auth_headers(token), json={
            'current_password':'StrongPass123!', 'new_password':'NewStrongPass456!'
        })
        assert changed.status_code == 200
        assert client.get('/api/auth/me', headers=auth_headers(token)).status_code == 401
        assert client.post('/api/auth/login', json={'username':'admin','password':'NewStrongPass456!'}).status_code == 200


def test_dashboard_metrics_are_calculated_from_real_records():
    with TestClient(app) as client:
        client.post('/api/setup/admin', json={'full_name':'Admin','username':'admin','password':'StrongPass123!'})
        token = client.post('/api/auth/login', json={'username':'admin','password':'StrongPass123!'}).json()['token']
        headers = auth_headers(token)
        saved = client.post('/api/documents', headers=headers, json={
            'type_code':'PR', 'status':'saved', 'fields':{'requester_name':'Ali', 'amount':'100'}
        }).json()
        client.post('/api/documents', headers=headers, json={
            'type_code':'PR', 'status':'draft', 'fields':{'requester_name':'Omar', 'amount':'200'}
        })
        image = Image.new('RGB', (40, 40), 'white')
        buffer = io.BytesIO(); image.save(buffer, format='PNG')
        upload = client.post(
            f"/api/documents/{saved['id']}/attachments",
            headers={**headers, 'X-File-Name':'proof.png', 'Content-Type':'image/png'},
            content=buffer.getvalue(),
        )
        assert upload.status_code == 201
        printed = client.post(f"/api/documents/{saved['id']}/print", headers=headers, json={'attachment_ids':[]})
        assert printed.status_code == 200

        response = client.get('/api/dashboard', headers=headers)
        assert response.status_code == 200
        dashboard = response.json()
        assert dashboard['total_documents'] == 2
        assert dashboard['saved_documents'] == 1
        assert dashboard['draft_documents'] == 1
        assert dashboard['total_attachments'] == 1
        assert dashboard['printed_total'] == 1
        assert len(dashboard['weekly_activity']) == 7
        pr = next(item for item in dashboard['types'] if item['code'] == 'PR')
        assert pr['count'] == 2
        assert pr['saved_count'] == 1
        assert pr['draft_count'] == 1


def test_line_by_line_template_contract_and_frontend_cleanup():
    import json

    project = Path(__file__).resolve().parents[1]
    template_config = json.loads((project / 'config' / 'templates.json').read_text(encoding='utf-8'))
    expected_lines = {
        ('RV', 'about'): 4,
        ('RV', 'written_amount'): 3,
        ('PR', 'purpose'): 2,
        ('PR', 'written_amount'): 2,
        ('PV', 'purpose'): 3,
        ('PV', 'written_amount'): 3,
    }
    for (code, key), count in expected_lines.items():
        field = next(item for item in template_config[code]['fields'] if item['key'] == key)
        assert len(field['line_positions']) == count
        assert field['line_height'] > 0
        assert field['enter_moves_next'] is True

    javascript = (project / 'app' / 'static' / 'app.js').read_text(encoding='utf-8')
    stylesheet = (project / 'app' / 'static' / 'styles.css').read_text(encoding='utf-8')
    assert 'template-line-field' in javascript
    assert 'data-field-line' in javascript
    assert 'حفظ كمسودة' not in javascript
    assert 'sidebar-collapsed' in javascript
    assert 'Desktop hide mode' in stylesheet
    assert 'documentActionButtons' in javascript
    assert 'row-actions' in javascript
    assert 'row-action' in stylesheet
    assert 'action-menu' not in javascript
    assert 'action-menu-popover' not in stylesheet
    assert 'type_code: Literal["RV", "PR", "PV"]' not in (project / 'app' / 'schemas.py').read_text(encoding='utf-8')


def test_user_marked_field_alignment_contract():
    import json

    project = Path(__file__).resolve().parents[1]
    config = json.loads((project / 'config' / 'templates.json').read_text(encoding='utf-8'))

    def field(code: str, key: str):
        return next(item for item in config[code]['fields'] if item['key'] == key)

    # Anchor fields from each of the four user-provided alignment images.
    expected = {
        ('RV', 'document_number'): (24.78, 26.97, 14.73, 2.68),
        ('RV', 'receiver_name'): (5.13, 86.57, 60.04, 2.25),
        ('PR', 'document_number'): (22.07, 31.54, 17.57, 2.38),
        ('PR', 'approval'): (70.72, 87.48, 26.58, 2.22),
        ('PV', 'amount'): (26.43, 64.54, 42.64, 2.34),
        ('PV', 'accountant'): (36.34, 90.60, 27.63, 2.25),
        ('VM', 'vehicle'): (56.03, 7.79, 29.91, 2.25),
        ('VM', 'accounts_manager'): (45.76, 91.55, 34.60, 2.19),
    }
    for (code, key), values in expected.items():
        item = field(code, key)
        actual = tuple(round(float(item[name]), 2) for name in ('x', 'y', 'w', 'h'))
        assert actual == values

    exact_line_counts = {
        ('RV', 'about'): 4,
        ('RV', 'written_amount'): 3,
        ('PR', 'purpose'): 2,
        ('PR', 'written_amount'): 2,
        ('PV', 'purpose'): 3,
        ('PV', 'written_amount'): 3,
    }
    for (code, key), count in exact_line_counts.items():
        boxes = field(code, key)['line_boxes']
        assert len(boxes) == count
        assert all({'x', 'y', 'w', 'h'} <= set(box) for box in boxes)

    # The two summary rows in the maintenance form expose every grey marked cell.
    for key in (
        'maintenance_total_notes', 'maintenance_total_shop', 'maintenance_total',
        'returned_amount_notes', 'returned_amount_shop', 'returned_amount',
    ):
        assert field('VM', key)

    javascript = (project / 'app' / 'static' / 'app.js').read_text(encoding='utf-8')
    pdf_service = (project / 'app' / 'services' / 'pdf_service.py').read_text(encoding='utf-8')
    assert 'field.line_boxes' in javascript
    assert 'field.get("line_boxes")' in pdf_service


def test_arabic_rtl_rendering_engine_and_pdf_output():
    import json
    from PIL import Image, features
    from app.services.pdf_service import render_document_pdf

    # CI/development builds must expose the shaping features required by the
    # production renderer. The Dockerfile independently verifies the same
    # requirement on Render.
    assert features.check('raqm') is True
    assert features.check('harfbuzz') is True
    assert features.check('fribidi') is True

    project = Path(__file__).resolve().parents[1]
    config = json.loads((project / 'config' / 'templates.json').read_text(encoding='utf-8'))
    output = TEST_DATA / 'arabic-pr.pdf'
    render_document_pdf(config['PR'], {
        'document_number': 'PR-000777',
        'date': '2026-08-07',
        'requester_name': 'محمد علي حسن',
        'department': 'قسم الصيانة',
        'pay_to': 'شركة التكامل العربي',
        'purpose': 'شراء مواد صيانة للسيارة\nمع أجور النقل والخدمات',
        'amount': '135000',
        'currency': 'IQD',
        'written_amount': 'مائة وخمسة وثلاثون ألف دينار عراقي فقط لا غير',
        'prepared_by': 'علي حسن',
        'verified_by': 'محمد كريم',
        'approval': 'موافق',
    }, output)
    assert output.exists() and output.stat().st_size > 10_000
    reader = PdfReader(str(output))
    assert len(reader.pages) == 1
