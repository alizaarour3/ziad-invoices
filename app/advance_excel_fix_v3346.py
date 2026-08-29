from __future__ import annotations

from urllib.parse import quote

from fastapi.responses import Response


XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def install_advance_excel_transport_fix(advance_excel_module) -> None:
    """Send generated XLSX files as a buffered HTTP response.

    Render/browser connections were intermittently surfacing `Failed to fetch`
    while the original implementation used StreamingResponse around BytesIO.
    The workbook is already fully generated in memory before the response is
    created, so streaming has no benefit here. A normal Response gives the
    proxy/browser a deterministic Content-Length and avoids a truncated stream.
    """

    def _buffered_xlsx_response(payload: bytes, filename: str) -> Response:
        encoded = quote(filename)
        return Response(
            content=payload,
            media_type=XLSX_MIME,
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded}",
                "Content-Length": str(len(payload)),
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "X-Ziad-Excel-Transport": "buffered-v3.3.46",
            },
        )

    advance_excel_module._xlsx_response = _buffered_xlsx_response
