"""
report_service.py

Generates IFRS 9 hedge accounting effectiveness test documentation as a
professionally formatted PDF.

This is what an external auditor would request during a hedge accounting review.
The document demonstrates compliance with IFRS 9 paras 6.4.1(c) and B6.4.14.

Never raises for missing data — returns a valid PDF with "No data available"
sections if positions or analytics runs are absent.
"""

import io
from datetime import date, datetime, timezone, timedelta
from typing import Any
from uuid import uuid4

import structlog
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    HRFlowable,
    PageTemplate,
    Frame,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.constants import IFRS9_R2_MIN_PROSPECTIVE, IFRS9_RETRO_HIGH, IFRS9_RETRO_LOW
from app.repositories.analytics import AnalyticsRepository
from app.repositories.market_data import MarketDataRepository
from app.repositories.positions import PositionRepository
from app.services.price_service import get_price_service

log = structlog.get_logger()

NAVY = colors.HexColor("#0f172a")
GREY = colors.HexColor("#374151")
GREEN = colors.HexColor("#16a34a")
AMBER = colors.HexColor("#d97706")
RED = colors.HexColor("#dc2626")
LIGHT_BG = colors.HexColor("#f8fafc")


class IFRS9ReportService:
    """Generates IFRS 9 hedge effectiveness PDF reports."""

    async def generate(self, db: AsyncSession) -> bytes:
        """
        Generate IFRS 9 report PDF.
        Returns bytes — caller streams as file download.
        Never raises — returns a valid PDF even with no data.
        """
        settings = get_settings()
        analytics_repo = AnalyticsRepository(db)
        positions_repo = PositionRepository(db)
        market_repo = MarketDataRepository(db)

        latest_run = await analytics_repo.get_latest_completed()
        positions = await positions_repo.get_open_positions()

        # Get current price for retrospective test
        current_price: float | None = None
        last_tick = get_price_service().get_last_tick()
        if last_tick:
            current_price = last_tick.jet_fuel_spot
        if current_price is None:
            db_tick = await market_repo.get_latest_tick()
            if db_tick:
                current_price = float(db_tick.jet_fuel_spot)

        generated_at = datetime.now(timezone.utc)
        report_meta = {
            "report_id": str(uuid4()),
            "generated_at": generated_at.isoformat(),
            "period_end": date.today().isoformat(),
            "next_test_date": (date.today() + timedelta(days=90)).isoformat(),
            "entity_name": settings.REPORTING_ENTITY_NAME,
            "currency": settings.REPORTING_CURRENCY,
            "analytics_run_id": str(latest_run.id) if latest_run is not None else "N/A",
            "analytics_run_date": str(latest_run.run_date) if latest_run is not None else "N/A",
            "positions_count": len(positions),
            "price_source": "live_feed" if last_tick is not None else ("db_last_tick" if current_price is not None else "none"),
            "current_price": current_price,
        }

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )
        story: list[Any] = []

        report_v2_enabled = settings.IFRS9_REPORT_V2

        story += self._build_header(report_meta, include_evidence=report_v2_enabled)
        if report_v2_enabled:
            story += self._build_methodology_and_controls(report_meta)
        story += self._build_designation_summary(positions)
        story += self._build_prospective_test(latest_run)
        story += self._build_retrospective_test(positions, current_price)
        if report_v2_enabled:
            story += self._build_data_quality_section(latest_run, positions, current_price)
        story += self._build_conclusion(positions, latest_run)
        if report_v2_enabled:
            story += self._build_appendix_evidence(latest_run, positions, current_price, report_meta)
            story += self._build_signoff_section(report_meta)

        def add_footer(canvas, doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(GREY)
            page_num = canvas.getPageNumber()
            canvas.drawString(
                2 * cm,
                1 * cm,
                f"CONFIDENTIAL — For internal use only | Page {page_num}",
            )
            canvas.restoreState()

        doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)
        return buffer.getvalue()

    def _styles(self) -> dict[str, ParagraphStyle]:
        styles = getSampleStyleSheet()
        custom = {
            "navy_header": ParagraphStyle(
                name="navy_header",
                parent=styles["Heading1"],
                fontSize=12,
                textColor=NAVY,
                spaceAfter=6,
            ),
            "body": ParagraphStyle(
                name="body",
                parent=styles["Normal"],
                fontSize=9,
                textColor=GREY,
                spaceAfter=6,
            ),
        }
        # StyleSheet.byName is the name->style mapping; dict(styles) yields indices, not names
        return {**styles.byName, **custom}

    def _build_header(self, report_meta: dict[str, Any], include_evidence: bool = True) -> list[Any]:
        today = date.today()
        quarter_start = date(today.year, ((today.month - 1) // 3) * 3 + 1, 1)
        styles = self._styles()

        return [
            Paragraph(
                "HEDGE EFFECTIVENESS TEST REPORT",
                ParagraphStyle(
                    name="title",
                    fontSize=16,
                    textColor=NAVY,
                    fontName="Helvetica-Bold",
                    spaceAfter=4,
                ),
            ),
            Paragraph("Aviation Fuel Hedging Platform", styles["body"]),
            Spacer(1, 12),
            Paragraph(f"<b>Prepared:</b> {today.isoformat()}", styles["body"]),
            Paragraph(
                f"<b>Period:</b> {quarter_start.isoformat()} – {today.isoformat()}",
                styles["body"],
            ),
            Paragraph(
                f"<b>Entity:</b> {report_meta['entity_name']}",
                styles["body"],
            ),
            Paragraph(
                "<b>Standard:</b> IFRS 9 Financial Instruments — Hedge Accounting",
                styles["body"],
            ),
            Paragraph(
                "<b>Reference:</b> Paragraphs 6.4.1(c), B6.4.1–B6.4.19",
                styles["body"],
            ),
            *((
                [
                    Paragraph(f"<b>Report ID:</b> {report_meta['report_id']}", styles["body"]),
                    Paragraph(f"<b>Generated (UTC):</b> {report_meta['generated_at']}", styles["body"]),
                    Paragraph(
                        f"<b>Evidence Run:</b> {report_meta['analytics_run_id']} (date: {report_meta['analytics_run_date']})",
                        styles["body"],
                    ),
                ]
            ) if include_evidence else []),
            Spacer(1, 12),
            HRFlowable(width="100%", thickness=1, color=NAVY),
            Paragraph(
                "<b>EXECUTIVE SUMMARY</b>",
                ParagraphStyle(
                    name="exec",
                    fontSize=10,
                    textColor=NAVY,
                    fontName="Helvetica-Bold",
                    spaceAfter=6,
                ),
            ),
            Paragraph(
                "Overall hedge effectiveness: See conclusion below. "
                "Next scheduled test: " + report_meta["next_test_date"],
                styles["body"],
            ),
            HRFlowable(width="100%", thickness=1, color=NAVY),
            Spacer(1, 16),
        ]

    def _build_methodology_and_controls(self, report_meta: dict[str, Any]) -> list[Any]:
        styles = self._styles()
        content = (
            "<b>Methodology and Controls</b><br/>"
            "1) Prospective assessment evaluates economic relationship and hedge ratio alignment under IFRS 9 para 6.4.1(c).<br/>"
            "2) Retrospective dollar-offset is presented as management monitoring evidence (not as a standalone IFRS 9 qualification bright-line test).<br/>"
            f"3) Reporting currency: {report_meta['currency']}. Data lineage is tied to analytics run {report_meta['analytics_run_id']}."
        )
        return [
            Paragraph("<b>0. METHODOLOGY & CONTROL CONTEXT</b>", styles["navy_header"]),
            HRFlowable(width="100%", thickness=1, color=NAVY),
            Paragraph(content, styles["body"]),
            Spacer(1, 12),
        ]

    def _build_designation_summary(
        self, positions: list[Any]
    ) -> list[Any]:
        styles = self._styles()
        if not positions:
            return [
                Paragraph("<b>1. HEDGE DESIGNATION SUMMARY</b>", styles["navy_header"]),
                HRFlowable(width="100%", thickness=1, color=NAVY),
                Paragraph(
                    "No open hedge positions at reporting date.",
                    styles["body"],
                ),
                Spacer(1, 16),
            ]

        data = [
            [
                "Position ID",
                "Instrument",
                "Proxy",
                "Designation Date",
                "Notional (USD)",
                "Hedge Ratio",
                "Status",
            ]
        ]
        for p in positions:
            pos_id = str(p.id)[:8] if hasattr(p, "id") else "—"
            data.append(
                [
                    pos_id,
                    p.instrument_type.value if hasattr(p, "instrument_type") else "—",
                    p.proxy,
                    str(p.expiry_date) if hasattr(p, "expiry_date") else "—",
                    f"{float(p.notional_usd):,.2f}",
                    f"{float(p.hedge_ratio) * 100:.1f}%",
                    p.status.value if hasattr(p, "status") else "OPEN",
                ]
            )

        t = Table(data, colWidths=[50, 55, 55, 55, 70, 50, 50])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ]
            )
        )
        return [
            Paragraph("<b>1. HEDGE DESIGNATION SUMMARY</b>", styles["navy_header"]),
            HRFlowable(width="100%", thickness=1, color=NAVY),
            t,
            Spacer(1, 16),
        ]

    def _build_prospective_test(self, latest_run: Any) -> list[Any]:
        styles = self._styles()
        if latest_run is None or not latest_run.basis_metrics:
            return [
                Paragraph(
                    "<b>2. PROSPECTIVE EFFECTIVENESS TEST</b>",
                    styles["navy_header"],
                ),
                HRFlowable(width="100%", thickness=1, color=NAVY),
                Paragraph(
                    "Method: Regression Analysis (R²) — IFRS 9 para 6.4.1(c)(i)",
                    styles["body"],
                ),
                Paragraph(
                    "Requirement: R² ≥ 0.80 for hedge to qualify for IFRS 9 designation.",
                    styles["body"],
                ),
                Paragraph(
                    "Prospective test pending — run the analytics pipeline to generate "
                    "effectiveness data.",
                    styles["body"],
                ),
                Spacer(1, 16),
            ]

        basis = latest_run.basis_metrics or {}
        r2_ho_raw = basis.get("r2_heating_oil")
        r2_brent_raw = basis.get("r2_brent")
        r2_wti_raw = basis.get("r2_wti")
        r2_ho = float(r2_ho_raw) if r2_ho_raw is not None else None
        r2_brent = float(r2_brent_raw) if r2_brent_raw is not None else None
        r2_wti = float(r2_wti_raw) if r2_wti_raw is not None else None

        def status_cell(r2: float | None) -> str:
            if r2 is None:
                return "NO_DATA"
            if r2 >= IFRS9_R2_MIN_PROSPECTIVE:
                return "EFFECTIVE"
            if r2 >= 0.65:
                return "MONITOR"
            return "INEFFECTIVE"

        def display_r2(r2: float | None) -> str:
            return f"{r2:.4f}" if r2 is not None else "N/A"

        data = [
            ["Proxy", "Latest R²", "Evidence Date", "Minimum", "Status", "Comment"],
            [
                "Heating Oil Fut",
                display_r2(r2_ho),
                str(latest_run.run_date),
                "0.80",
                status_cell(r2_ho),
                "Primary designated proxy",
            ],
            [
                "Brent Crude Fut",
                display_r2(r2_brent),
                str(latest_run.run_date),
                "0.80",
                status_cell(r2_brent),
                "Secondary benchmark proxy",
            ],
            [
                "WTI Crude Fut",
                display_r2(r2_wti),
                str(latest_run.run_date),
                "0.80",
                status_cell(r2_wti),
                "Secondary benchmark proxy",
            ],
        ]

        t = Table(data, colWidths=[80, 55, 70, 45, 55, 95])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ]
            )
        )

        r2_values = [r for r in [r2_ho, r2_brent, r2_wti] if r is not None]
        n_effective = sum(1 for r in r2_values if r >= IFRS9_R2_MIN_PROSPECTIVE)
        passed = r2_ho is not None and r2_ho >= IFRS9_R2_MIN_PROSPECTIVE
        conclusion = (
            f"The prospective effectiveness test {'PASSED' if passed else 'FAILED'} "
            f"for the current reporting period. {n_effective} of {len(r2_values)} proxy instruments "
            f"with available evidence meet the IFRS 9 minimum R² threshold of 0.80. "
        )
        if passed:
            conclusion += (
                "Heating oil futures remain the primary designated hedging instrument "
                "for IFRS 9 purposes."
            )

        return [
            Paragraph("<b>2. PROSPECTIVE EFFECTIVENESS TEST</b>", styles["navy_header"]),
            HRFlowable(width="100%", thickness=1, color=NAVY),
            Paragraph(
                "Method: Regression Analysis (R²) — IFRS 9 para 6.4.1(c)(i)",
                styles["body"],
            ),
            Paragraph(
                "Requirement: R² ≥ 0.80 for hedge to qualify for IFRS 9 designation.",
                styles["body"],
            ),
            Spacer(1, 6),
            t,
            Spacer(1, 6),
            Paragraph(f"Conclusion: {conclusion}", styles["body"]),
            Spacer(1, 16),
        ]

    def _build_retrospective_test(
        self, positions: list[Any], current_price: float | None
    ) -> list[Any]:
        styles = self._styles()
        if current_price is None or len(positions) < 1:
            return [
                Paragraph(
                    "<b>3. RETROSPECTIVE EFFECTIVENESS TEST</b>",
                    styles["navy_header"],
                ),
                HRFlowable(width="100%", thickness=1, color=NAVY),
                Paragraph(
                    "Method: Dollar Offset Ratio — IFRS 9 para B6.4.14",
                    styles["body"],
                ),
                Paragraph(
                    "Monitoring band: 80%–125% shown for management evidence; IFRS 9 qualification remains principle-based.",
                    styles["body"],
                ),
                Paragraph(
                    "Insufficient price history for retrospective test. At least one "
                    "pricing period must elapse after hedge designation.",
                    styles["body"],
                ),
                Spacer(1, 16),
            ]

        data = [
            [
                "Position",
                "Instrument",
                "Entry",
                "Current",
                "Δ Hedge",
                "Δ Hedged Item",
                "Offset Ratio",
                "Status",
            ]
        ]

        for p in positions:
            entry = float(p.entry_price)
            notional_bbls = float(p.notional_usd) / entry if entry > 0 else 0
            price_diff = current_price - entry

            # Short hedge: gain when price falls. Delta hedge = (entry - current) * notional_bbls
            delta_hedge = (entry - current_price) * notional_bbls
            delta_hedged_item = price_diff * notional_bbls
            if abs(delta_hedged_item) > 1e-6:
                ratio = abs(delta_hedge) / abs(delta_hedged_item) * 100
            else:
                ratio = 100.0

            if IFRS9_RETRO_LOW <= ratio / 100 <= IFRS9_RETRO_HIGH:
                status = "EFFECTIVE"
            elif 0.65 <= ratio / 100 < IFRS9_RETRO_LOW or IFRS9_RETRO_HIGH < ratio / 100 <= 1.40:
                status = "MONITOR"
            else:
                status = "INEFFECTIVE"

            data.append(
                [
                    str(p.id)[:8] if hasattr(p, "id") else "—",
                    p.instrument_type.value if hasattr(p, "instrument_type") else "—",
                    f"{entry:.2f}",
                    f"{current_price:.2f}",
                    f"{delta_hedge:,.2f}",
                    f"{delta_hedged_item:,.2f}",
                    f"{ratio:.1f}%",
                    status,
                ]
            )

        t = Table(data, colWidths=[45, 50, 40, 40, 55, 55, 50, 55])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ]
            )
        )

        return [
            Paragraph(
                "<b>3. RETROSPECTIVE EFFECTIVENESS TEST</b>",
                styles["navy_header"],
            ),
            HRFlowable(width="100%", thickness=1, color=NAVY),
            Paragraph(
                "Method: Dollar Offset Ratio — IFRS 9 para B6.4.14",
                styles["body"],
            ),
            Paragraph(
                "Monitoring band: 80%–125% shown for management evidence; IFRS 9 qualification remains principle-based.",
                styles["body"],
            ),
            Spacer(1, 6),
            t,
            Spacer(1, 16),
        ]

    def _build_data_quality_section(
        self,
        latest_run: Any,
        positions: list[Any],
        current_price: float | None,
    ) -> list[Any]:
        styles = self._styles()
        basis = (latest_run.basis_metrics or {}) if latest_run is not None else {}
        issues: list[str] = []
        if latest_run is None:
            issues.append("No completed analytics run available for the reporting period.")
        if not positions:
            issues.append("No open hedge positions at reporting date.")
        if current_price is None:
            issues.append("Current jet fuel reference price unavailable.")
        for key in ("r2_heating_oil", "r2_brent", "r2_wti"):
            if basis.get(key) is None:
                issues.append(f"Missing basis metric: {key}.")

        status = "PASS" if not issues else "REVIEW"
        body = "No material data-quality exceptions detected." if not issues else "<br/>".join(f"- {i}" for i in issues)

        return [
            Paragraph("<b>4. DATA QUALITY & EVIDENCE CHECKS</b>", styles["navy_header"]),
            HRFlowable(width="100%", thickness=1, color=NAVY),
            Paragraph(f"<b>Status:</b> {status}", styles["body"]),
            Paragraph(body, styles["body"]),
            Spacer(1, 16),
        ]

    def _build_conclusion(self, positions: list[Any], latest_run: Any) -> list[Any]:
        styles = self._styles()
        today = date.today()
        next_test = today + timedelta(days=90)

        effective = True
        if latest_run and latest_run.basis_metrics:
            r2 = float(latest_run.basis_metrics.get("r2_heating_oil", 1) or 1)
            if r2 < IFRS9_R2_MIN_PROSPECTIVE:
                effective = False

        assessment = "EFFECTIVE" if effective else "REQUIRES REVIEW"
        qualifies = "qualifies" if effective else "does not qualify"

        conclusion = (
            "<b>5. HEDGE EFFECTIVENESS CONCLUSION</b><br/>"
            f"<b>Overall assessment:</b> {assessment}<br/>"
            f"The hedge portfolio {qualifies} for hedge accounting treatment under IFRS 9 "
            f"for the period ending {today.isoformat()}.<br/>"
            + (
                "Hedge accounting may continue. No de-designation required. "
                "Recommended action: Maintain current hedge positions and document routine monitoring."
                if effective
                else "One or more proxies are approaching or below the effectiveness threshold. "
                "Recommended action: Review proxy selection and consider rebalancing toward heating oil futures."
            )
            + f"<br/><b>Next scheduled effectiveness test:</b> {next_test.isoformat()}<br/><br/>"
            "<b>Disclaimer:</b> This report is generated for internal risk management and documentation only. "
            "It does not constitute professional accounting advice and should be reviewed by qualified finance "
            "and audit stakeholders before external reporting use."
        )
        return [
            Paragraph(conclusion, styles["body"]),
        ]

    def _build_signoff_section(self, report_meta: dict[str, Any]) -> list[Any]:
        styles = self._styles()
        signoff_table = Table(
            [
                ["Role", "Name", "Timestamp (UTC)", "Status"],
                ["Prepared by (Treasury Analyst)", "________________", report_meta["generated_at"], "Prepared"],
                ["Reviewed by (Risk Manager)", "________________", "________________", "Pending"],
                ["Approved by (Controller/CFO)", "________________", "________________", "Pending"],
            ],
            colWidths=[120, 120, 130, 80],
        )
        signoff_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                ]
            )
        )
        return [
            Paragraph("<b>6. GOVERNANCE SIGN-OFF</b>", styles["navy_header"]),
            HRFlowable(width="100%", thickness=1, color=NAVY),
            signoff_table,
            Spacer(1, 8),
        ]

    def _build_appendix_evidence(
        self,
        latest_run: Any,
        positions: list[Any],
        current_price: float | None,
        report_meta: dict[str, Any],
    ) -> list[Any]:
        styles = self._styles()
        basis = (latest_run.basis_metrics or {}) if latest_run is not None else {}
        optimizer = (latest_run.optimizer_result or {}) if latest_run is not None else {}
        var_results = (latest_run.var_results or {}) if latest_run is not None else {}

        evidence_table = Table(
            [
                ["Evidence Item", "Value"],
                ["Report ID", report_meta["report_id"]],
                ["Run ID", report_meta["analytics_run_id"]],
                ["Run Date", report_meta["analytics_run_date"]],
                ["Generated At (UTC)", report_meta["generated_at"]],
                ["Open Positions", str(len(positions))],
                ["Current Jet Fuel Price", f"{current_price:.4f}" if current_price is not None else "N/A"],
                ["Price Source", str(report_meta["price_source"])],
                ["r2_heating_oil", str(basis.get("r2_heating_oil", "N/A"))],
                ["r2_brent", str(basis.get("r2_brent", "N/A"))],
                ["r2_wti", str(basis.get("r2_wti", "N/A"))],
                ["optimal_hr", str(optimizer.get("optimal_hr", "N/A"))],
                ["var_hedged_usd", str(var_results.get("var_usd", "N/A"))],
                ["var_unhedged_usd", str(var_results.get("var_unhedged_usd", "N/A"))],
                ["IFRS9 prospective threshold", "R² >= 0.80"],
                ["Retrospective monitoring band", "80% - 125%"],
            ],
            colWidths=[170, 280],
        )
        evidence_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                ]
            )
        )

        calc_notes = (
            "<b>Calculation Notes</b><br/>"
            "- Prospective: evaluate economic relationship using regression R² and hedge ratio alignment.<br/>"
            "- Retrospective monitoring: dollar-offset ratio = |Δ hedging instrument| / |Δ hedged item|.<br/>"
            "- Data source precedence: live feed tick, then database latest tick, then N/A if unavailable."
        )
        return [
            Paragraph("<b>5A. APPENDIX — EVIDENCE & CALCULATION INPUTS</b>", styles["navy_header"]),
            HRFlowable(width="100%", thickness=1, color=NAVY),
            evidence_table,
            Spacer(1, 8),
            Paragraph(calc_notes, styles["body"]),
            Spacer(1, 12),
        ]
