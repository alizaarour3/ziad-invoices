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
        assert {item["code"] for item in types.json()} == {"RV", "PR", "PV", "VM", "TR"}

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
        me = client.get("/api/auth/me", headers=viewer_headers)
        assert me.status_code == 200
        assert "documents.TR" in me.json()["page_permissions"]
        assert "loans" in me.json()["page_permissions"]
        assert "advances" in me.json()["page_permissions"]
        assert client.get("/api/documents", headers=viewer_headers).status_code == 200
        assert client.post("/api/documents", headers=viewer_headers, json={"type_code": "PR", "fields": {}}).status_code == 403
        assert client.get("/api/users", headers=viewer_headers).status_code == 403
        assert client.get("/api/permissions", headers=viewer_headers).status_code == 403

        editor = client.post(
            "/api/users",
            headers=admin_headers,
            json={"full_name": "Transfer Editor", "username": "transfer.editor", "password": "EditorPass123!", "role": "editor"},
        ).json()
        permissions = client.get("/api/permissions", headers=admin_headers)
        assert permissions.status_code == 200
        assert {page["key"] for page in permissions.json()["pages"]} == {
            "dashboard", "loans", "advances", "documents.RV", "documents.PR", "documents.PV", "documents.VM", "documents.TR"
        }
        changed = client.put(
            f"/api/permissions/users/{editor['id']}",
            headers=admin_headers,
            json={"page_keys": ["dashboard", "documents.TR"]},
        )
        assert changed.status_code == 200

        editor_token = client.post("/api/auth/login", json={"username": "transfer.editor", "password": "EditorPass123!"}).json()["token"]
        editor_headers = auth_headers(editor_token)
        editor_types = client.get("/api/document-types", headers=editor_headers)
        assert editor_types.status_code == 200
        assert [item["code"] for item in editor_types.json()] == ["TR"]
        assert client.get("/api/documents?type_code=PR", headers=editor_headers).status_code == 403
        transfer = client.post(
            "/api/documents",
            headers=editor_headers,
            json={"type_code": "TR", "status": "draft", "fields": {"pay_to": "شركة اختبار", "amount": "500"}},
        )
        assert transfer.status_code == 201, transfer.text
        assert transfer.json()["document_number"] == "TR-000001"
        assert transfer.json()["fields"]["pay_to"] == "شركة اختبار"
        assert client.post("/api/documents", headers=editor_headers, json={"type_code": "PV", "fields": {}}).status_code == 403

        removed_dashboard = client.put(
            f"/api/permissions/users/{editor['id']}",
            headers=admin_headers,
            json={"page_keys": ["documents.TR"]},
        )
        assert removed_dashboard.status_code == 200
        assert client.get("/api/dashboard", headers=editor_headers).status_code == 403
        assert client.get(f"/api/documents/{transfer.json()['id']}", headers=editor_headers).status_code == 200

        admin_id = client.get("/api/users", headers=admin_headers).json()[0]["id"]
        if admin_id == editor["id"]:
            admin_id = next(item["id"] for item in client.get("/api/users", headers=admin_headers).json() if item["role"] == "admin")
        assert client.put(
            f"/api/permissions/users/{admin_id}", headers=admin_headers, json={"page_keys": []}
        ).status_code == 422


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
        assert status_data['version'] == '3.3.19'
        assert status_data['database']['ok'] is True
        assert status_data['printing']['ready'] is True
        assert status_data['printing']['chromium'] is True
        assert status_data['printing']['playwright'] is True
        assert status_data['counts']['documents'] == 1
        assert len(status_data['templates']) == 15
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
            assert 'app/static/form-templates/receipt-voucher.html' in names
            assert 'app/static/form-templates/request-transfer.html' in names
            manifest = json.loads(archive.read('manifest.json'))
            assert manifest['version'] == '3.3.19'
            assert manifest['files']


def test_html_template_static_urls_are_served():
    template_names = [
        'receipt-voucher.html',
        'payment-request.html',
        'payment-voucher.html',
        'vehicle-maintenance.html',
        'request-transfer.html',
    ]
    with TestClient(app) as client:
        for name in template_names:
            response = client.get(f'/form-templates/{name}')
            assert response.status_code == 200, f'{name}: {response.text[:200]}'
            assert response.headers['content-type'].startswith('text/html')
            assert '<html' in response.text.lower() or '<!doctype html' in response.text.lower()


def test_failed_login_attempts_never_lock_account_and_password_change():
    with TestClient(app) as client:
        client.post('/api/setup/admin', json={'full_name':'Admin','username':'admin','password':'StrongPass123!'})
        for _ in range(12):
            response = client.post('/api/auth/login', json={'username':'admin','password':'wrong-password'})
            assert response.status_code == 401

        # v3.3.19 explicitly removes automatic account lockout. Even a stale
        # locked_until value left by an older release must not block a valid login.
        from app.db import connect
        conn = connect()
        try:
            conn.execute("UPDATE users SET locked_until='2099-01-01T00:00:00+00:00' WHERE username='admin'")
        finally:
            conn.close()

        login = client.post('/api/auth/login', json={'username':'admin','password':'StrongPass123!'})
        assert login.status_code == 200
        conn = connect()
        try:
            row = conn.execute("SELECT failed_login_count, locked_until FROM users WHERE username='admin'").fetchone()
            assert row['failed_login_count'] == 0
            assert row['locked_until'] is None
        finally:
            conn.close()
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

    transfer_output = TEST_DATA / 'arabic-transfer.pdf'
    render_document_pdf(config['TR'], {
        'date': '2026-08-10',
        'department': 'قسم الحسابات',
        'pay_to': 'شركة التكامل العربي',
        'purpose': 'تحويل دفعة مستحقة\nحسب الاتفاق',
        'transfer_entity': 'مصرف الاختبار',
        'amount': '250000',
        'currency': 'IQD',
        'written_amount': 'مائتان وخمسون ألف دينار عراقي\nفقط لا غير',
        'prepared_by': 'علي حسن',
        'accounts': 'محمد كريم',
        'approval': 'موافق',
    }, transfer_output)
    assert transfer_output.exists() and transfer_output.stat().st_size > 10_000
    assert len(PdfReader(str(transfer_output)).pages) == 1


def test_exact_html_templates_are_immutable_and_all_field_selectors_exist():
    import hashlib
    import json
    from bs4 import BeautifulSoup

    project = Path(__file__).resolve().parents[1]
    config = json.loads((project / 'config' / 'templates.json').read_text(encoding='utf-8'))
    expected_hashes = {}
    for line in (project / 'HTML_TEMPLATE_HASHES.sha256').read_text(encoding='utf-8').splitlines():
        digest, relative = line.split(maxsplit=1)
        expected_hashes[relative] = digest

    for code, item in config.items():
        assert item['template_engine'] == 'html'
        html_path = project / 'app' / 'static' / 'form-templates' / item['html_template']
        relative = html_path.relative_to(project).as_posix()
        assert html_path.exists()
        assert hashlib.sha256(html_path.read_bytes()).hexdigest() == expected_hashes[relative]
        soup = BeautifulSoup(html_path.read_text(encoding='utf-8'), 'html.parser')
        assert soup.select_one(item['html_root']) is not None
        for field in item['fields']:
            selectors = field.get('html_selectors') or [field.get('html_selector')]
            assert selectors and all(selectors), f"{code}:{field['key']} has no HTML selector"
            for selector in selectors:
                assert soup.select_one(selector) is not None, f"{code}:{field['key']} missing {selector}"



def test_loans_lifecycle_payments_and_permissions():
    with TestClient(app) as client:
        client.post('/api/setup/admin', json={'full_name':'Admin','username':'admin','password':'StrongPass123!'})
        token = client.post('/api/auth/login', json={'username':'admin','password':'StrongPass123!'}).json()['token']
        headers = auth_headers(token)

        created = client.post('/api/loans', headers=headers, json={
            'borrower_name':'أحمد علي حسن',
            'principal_amount':1200,
            'months_total':12,
            'minimum_payment':100,
        })
        assert created.status_code == 201, created.text
        loan = created.json()
        assert loan['remaining_amount'] == '1200.00'
        assert loan['remaining_months'] == 12
        assert loan['payment_count'] == 0

        too_small = client.post(f"/api/loans/{loan['id']}/payments", headers=headers, json={'amount':50,'notes':''})
        assert too_small.status_code == 422
        paid = client.post(f"/api/loans/{loan['id']}/payments", headers=headers, json={'amount':100,'notes':'الدفعة الأولى'})
        assert paid.status_code == 201, paid.text
        assert paid.json()['remaining_amount'] == '1100.00'
        assert paid.json()['remaining_months'] == 11
        assert paid.json()['payment_count'] == 1
        assert paid.json()['payments'][0]['notes'] == 'الدفعة الأولى'

        edited = client.put(f"/api/loans/{loan['id']}", headers=headers, json={
            'borrower_name':'أحمد علي حسن',
            'principal_amount':1300,
            'months_total':13,
            'minimum_payment':100,
        })
        assert edited.status_code == 200, edited.text
        assert edited.json()['remaining_amount'] == '1200.00'
        assert edited.json()['remaining_months'] == 12

        # A final exact payoff is accepted and forces remaining months to zero.
        payoff = client.post(f"/api/loans/{loan['id']}/payments", headers=headers, json={'amount':1200,'notes':'إقفال القرض'})
        assert payoff.status_code == 201, payoff.text
        assert payoff.json()['remaining_amount'] == '0.00'
        assert payoff.json()['remaining_months'] == 0
        assert payoff.json()['status'] == 'paid'

        viewer = client.post('/api/users', headers=headers, json={
            'full_name':'Loan Viewer','username':'loan.viewer','password':'ViewerPass123!','role':'viewer'
        }).json()
        client.put(f"/api/permissions/users/{viewer['id']}", headers=headers, json={'page_keys':['loans']})
        viewer_token = client.post('/api/auth/login', json={'username':'loan.viewer','password':'ViewerPass123!'}).json()['token']
        viewer_headers = auth_headers(viewer_token)
        assert client.get('/api/loans', headers=viewer_headers).status_code == 200
        assert client.post('/api/loans', headers=viewer_headers, json={
            'borrower_name':'مستخدم اختبار ثلاثي','principal_amount':100,'months_total':1,'minimum_payment':100
        }).status_code == 403

        removed = client.put(f"/api/permissions/users/{viewer['id']}", headers=headers, json={'page_keys':[]})
        assert removed.status_code == 200
        assert client.get('/api/loans', headers=viewer_headers).status_code == 403

        bad_delete = client.request('DELETE', f"/api/loans/{loan['id']}/permanent", headers=headers, json={'confirmation':'delete'})
        assert bad_delete.status_code == 422
        deleted = client.request('DELETE', f"/api/loans/{loan['id']}/permanent", headers=headers, json={'confirmation':'حذف نهائي'})
        assert deleted.status_code == 200
        assert client.get(f"/api/loans/{loan['id']}", headers=headers).status_code == 404



def test_advances_lifecycle_payments_and_permissions():
    with TestClient(app) as client:
        client.post('/api/setup/admin', json={'full_name':'Admin','username':'admin','password':'StrongPass123!'})
        token = client.post('/api/auth/login', json={'username':'admin','password':'StrongPass123!'}).json()['token']
        headers = auth_headers(token)

        invalid_month = client.post('/api/advances', headers=headers, json={
            'person_name':'أحمد علي حسن',
            'amount':500,
            'advance_month':'2026-13',
            'notes':'اختبار',
        })
        assert invalid_month.status_code == 422

        created = client.post('/api/advances', headers=headers, json={
            'person_name':'أحمد علي حسن',
            'amount':500,
            'advance_month':'2026-08',
            'notes':'سلفة شهر آب',
        })
        assert created.status_code == 201, created.text
        advance = created.json()
        assert advance['remaining_amount'] == '500.00'
        assert advance['paid_amount'] == '0.00'
        assert advance['advance_month'] == '2026-08'
        assert advance['notes'] == 'سلفة شهر آب'

        paid = client.post(f"/api/advances/{advance['id']}/payments", headers=headers, json={'amount':125,'notes':'دفعة أولى'})
        assert paid.status_code == 201, paid.text
        assert paid.json()['remaining_amount'] == '375.00'
        assert paid.json()['paid_amount'] == '125.00'
        assert paid.json()['payments'][0]['notes'] == 'دفعة أولى'

        overpay = client.post(f"/api/advances/{advance['id']}/payments", headers=headers, json={'amount':400,'notes':''})
        assert overpay.status_code == 422

        edited = client.put(f"/api/advances/{advance['id']}", headers=headers, json={
            'person_name':'أحمد علي حسن',
            'amount':600,
            'advance_month':'2026-09',
            'notes':'تم تعديل السلفة',
        })
        assert edited.status_code == 200, edited.text
        assert edited.json()['remaining_amount'] == '475.00'
        assert edited.json()['advance_month'] == '2026-09'

        viewer = client.post('/api/users', headers=headers, json={
            'full_name':'Advance Viewer','username':'advance.viewer','password':'ViewerPass123!','role':'viewer'
        }).json()
        client.put(f"/api/permissions/users/{viewer['id']}", headers=headers, json={'page_keys':['advances']})
        viewer_token = client.post('/api/auth/login', json={'username':'advance.viewer','password':'ViewerPass123!'}).json()['token']
        viewer_headers = auth_headers(viewer_token)
        assert client.get('/api/advances', headers=viewer_headers).status_code == 200
        assert client.post('/api/advances', headers=viewer_headers, json={
            'person_name':'مستخدم اختبار ثلاثي','amount':100,'advance_month':'2026-08','notes':''
        }).status_code == 403

        removed = client.put(f"/api/permissions/users/{viewer['id']}", headers=headers, json={'page_keys':[]})
        assert removed.status_code == 200
        assert client.get('/api/advances', headers=viewer_headers).status_code == 403

        payoff = client.post(f"/api/advances/{advance['id']}/payments", headers=headers, json={'amount':475,'notes':'إقفال السلفة'})
        assert payoff.status_code == 201, payoff.text
        assert payoff.json()['remaining_amount'] == '0.00'
        assert payoff.json()['status'] == 'paid'

        bad_delete = client.request('DELETE', f"/api/advances/{advance['id']}/permanent", headers=headers, json={'confirmation':'delete'})
        assert bad_delete.status_code == 422
        deleted = client.request('DELETE', f"/api/advances/{advance['id']}/permanent", headers=headers, json={'confirmation':'حذف نهائي'})
        assert deleted.status_code == 200
        assert client.get(f"/api/advances/{advance['id']}", headers=headers).status_code == 404


def test_v3319_exact_16pt_line_alignment_and_advances_ui_contract():
    import json
    project = Path(__file__).resolve().parents[1]
    javascript = (project / 'app' / 'static' / 'app.js').read_text(encoding='utf-8')
    pdf_service = (project / 'app' / 'services' / 'pdf_service.py').read_text(encoding='utf-8')
    stylesheet = (project / 'app' / 'static' / 'styles.css').read_text(encoding='utf-8')
    templates = json.loads((project / 'config' / 'templates.json').read_text(encoding='utf-8'))

    assert 'TEMPLATE_DATA_FONT_PT = 16' in javascript
    assert "element.style.setProperty('font-size', `${TEMPLATE_DATA_FONT_PT}pt`, 'important')" in javascript
    assert 'installHtmlSplitLineEditor' in javascript
    assert 'data-ziad-line-field' in javascript
    assert 'HTML_DATA_FONT_PT = 16' in pdf_service
    assert 'ziad-print-split-lines' in pdf_service
    assert 'font-size:16pt !important' in pdf_service
    assert all(any(field.get('html_line') for field in templates[code]['fields']) for code in ('RV','PR','PV','VM','TR'))
    assert "renderAdvances" in javascript
    assert "renderAdvanceDetails" in javascript
    assert "renderAdvanceReport" in javascript
    assert "openAdvancePaymentModal" in javascript
    assert "canViewPage('advances')" in javascript
    assert ".advance-table" in stylesheet

def test_v3314_transfer_workspace_and_dashboard_ui_contract():
    import hashlib

    project = Path(__file__).resolve().parents[1]
    javascript = (project / 'app' / 'static' / 'app.js').read_text(encoding='utf-8')
    stylesheet = (project / 'app' / 'static' / 'styles.css').read_text(encoding='utf-8')
    transfer_html = project / 'app' / 'static' / 'form-templates' / 'request-transfer.html'

    assert 'renderTransferList' in javascript
    assert 'transfer-page-hero' in javascript
    assert 'dashboard-hero' in javascript
    assert 'dashboard-finance-panel' in javascript
    assert 'transfer-document-header' in javascript
    assert '.transfer-summary-grid' in stylesheet
    assert '.dashboard-kpi-grid' in stylesheet
    assert hashlib.sha256(transfer_html.read_bytes()).hexdigest() == '02560523c3cf78c0e4bd948e6b2961e38e10ae727deacd5c076c3783cb21ad48'


def test_v3315_loan_report_is_in_app_and_popup_free():
    project = Path(__file__).resolve().parents[1]
    javascript = (project / 'app' / 'static' / 'app.js').read_text(encoding='utf-8')
    stylesheet = (project / 'app' / 'static' / 'styles.css').read_text(encoding='utf-8')

    assert "navigate(`/loans/${loan.id}/report`)" in javascript
    assert "renderLoanReport" in javascript
    assert "loanReportMatch" in javascript
    assert "اسمح للنظام بفتح نافذة التقرير" not in javascript
    assert "window.open('', '_blank')" not in javascript
    assert ".loan-report-paper" in stylesheet
    assert "loan-report-print-btn" in javascript




def test_print_renderer_has_calibrated_pdf_fallback(monkeypatch):
    import json
    from app.services import pdf_service

    project = Path(__file__).resolve().parents[1]
    config = json.loads((project / 'config' / 'templates.json').read_text(encoding='utf-8'))

    def fail_html(*_args, **_kwargs):
        raise RuntimeError('simulated browser renderer failure')

    monkeypatch.setattr(pdf_service, '_render_html_template_pdf', fail_html)
    output = TEST_DATA / 'fallback-pr.pdf'
    pdf_service.render_document_pdf(config['PR'], {
        'requester_name': 'اختبار الطباعة',
        'amount': '50000',
        'currency': 'IQD',
    }, output)
    assert output.exists() and output.stat().st_size > 10_000
    reader = PdfReader(str(output))
    assert len(reader.pages) == 1
    width_mm = float(reader.pages[0].mediabox.width) * 25.4 / 72
    height_mm = float(reader.pages[0].mediabox.height) * 25.4 / 72
    assert width_mm == pytest.approx(210, abs=0.2)
    assert height_mm == pytest.approx(297, abs=0.2)

def test_supabase_security_hardening_statements():
    from app.db import SUPABASE_APP_TABLES, _harden_supabase_public_schema

    class Result:
        def __init__(self, rows=None):
            self.rows = rows or []

        def fetchall(self):
            return self.rows

    class FakeConn:
        is_postgres = True

        def __init__(self):
            self.statements = []

        def execute(self, sql, params=()):
            self.statements.append(sql)
            if "FROM pg_roles" in sql:
                return Result([
                    {"rolname": "anon"},
                    {"rolname": "authenticated"},
                    {"rolname": "service_role"},
                ])
            return Result()

    conn = FakeConn()
    _harden_supabase_public_schema(conn)
    sql = "\n".join(conn.statements)
    for table in SUPABASE_APP_TABLES:
        assert f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY' in sql
        assert f'REVOKE ALL PRIVILEGES ON TABLE public."{table}" FROM anon, authenticated' in sql
    assert "REVOKE USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated" in sql
    assert "ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM anon, authenticated" in sql
