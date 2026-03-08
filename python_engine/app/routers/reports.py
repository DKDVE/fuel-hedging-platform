"""IFRS 9 hedge effectiveness report API."""

from datetime import date

from fastapi import APIRouter, Depends, Response

from app.dependencies import DatabaseSession, require_permission
from app.services.report_service import IFRS9ReportService

router = APIRouter(prefix="/reports", tags=["reports"])

# Singleton report service
_report_service: IFRS9ReportService | None = None


def get_report_service() -> IFRS9ReportService:
    """Get or create the IFRS9ReportService singleton."""
    global _report_service
    if _report_service is None:
        _report_service = IFRS9ReportService()
    return _report_service


@router.get(
    "/ifrs9/latest",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
async def download_ifrs9_report(
    db: DatabaseSession,
    current_user=Depends(require_permission("view:analytics")),
    report_service: IFRS9ReportService = Depends(get_report_service),
) -> Response:
    """
    Download IFRS 9 hedge effectiveness test report as PDF.
    Requires view:analytics permission (analyst, risk_manager, cfo, admin).
    Returns a formatted PDF with prospective and retrospective test results.
    """
    pdf_bytes = await report_service.generate(db)
    filename = f"ifrs9_effectiveness_report_{date.today().isoformat()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
