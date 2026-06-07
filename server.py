#!/usr/bin/env python3
"""
MEOK Cold-Chain Pharmaceutical Compliance MCP
=============================================

By MEOK AI Labs · https://haulage.app · MIT
<!-- mcp-name: io.github.CSOAI-ORG/meok-cold-chain-pharma-mcp -->

WHAT THIS DOES
--------------
UK pharmaceutical wholesale distribution is a £550m market — AstraZeneca, GSK,
Pfizer UK, plus 500+ MHRA-licensed wholesale distributors. Every shipment of a
prescription-only medicine (POM) MUST comply with EU/UK Good Distribution
Practice 2013/C 343/01 (MHRA-enforced) and most biologics require unbroken
+2 °C to +8 °C cold-chain integrity from manufacturer to patient.

A single cold-chain breach (failed temperature mapping, freezer fail, courier
delay) means:
  - Batch quarantine + write-off (£10k-£10m per consignment)
  - MHRA WDA(H) Wholesale Distribution Authorisation inspection finding
  - Patient harm risk → potential corporate manslaughter
  - Brexit divergence — UK FMD (FMD-UK) is now distinct from EU FMD

This MCP gives MHRA Responsible Persons (RPs), 3PL pharma logistics ops, and
clinical-trial supply teams the callable GDP toolkit they have been managing
on paper or in Excel.

TOOLS (8)
---------
- check_gdp_compliance(operator_data)           → EU/UK GDP 2013/C 343/01
- check_qualified_person_responsible(qp_data)   → MHRA RP licence check
- check_temperature_excursion(shipment_data)    → 2-8 °C breach detection
- check_who_pq_compliance(consignment)          → WHO PQ for global health
- check_serialisation_falsified_medicines(pack) → EU FMD + UK FMD divergence
- prepare_mhra_audit_pack(operator_data)        → WDA(H) inspection prep
- check_dangerous_goods_pharma(consignment)     → DGSA: dry ice ADR Cl. 9 + CDs
- validate_temperature_mapping_qualification(f) → WHO TRS 961 + EU GDP §3

WHY YOU PAY
-----------
Single avoided cold-chain breach on a biologic consignment = £100k-£10m saved
in batch write-off + reputational damage + MHRA finding. RPs use it to AUTOMATE
the GDP paperwork they hate. 3PLs use it as the evidence layer for MHRA
WDA(H) renewal and customer audits (AZ + GSK + Pfizer all require it).

PRICING
-------
Free MIT self-host · £199/mo Starter · £499/mo Pro · £2,999/mo Fleet
(pharma = highest-margin compliance vertical).

REGULATORY BASIS
----------------
EU/UK Good Distribution Practice Guideline 2013/C 343/01
MHRA WDA(H) Wholesale Distribution Authorisation (Human)
WHO Technical Report Series 961 — Annex 9 (cold-chain)
WHO Prequalification Programme (PQ)
EU Falsified Medicines Directive 2011/62/EU (delegated 2016/161)
UK Falsified Medicines (Human Use) Regulations 2019 (post-Brexit)
Medicines for Human Use (Marketing Authorisations Etc.) Regulations 1994
USP 1079 — Good Storage and Distribution Practices for Drug Products
ADR 2025 — Dry ice as UN1845 / Class 9
Misuse of Drugs Regulations 2001 — Schedule 1-5 controlled drugs
"""

from __future__ import annotations
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone, date
from typing import Optional
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("meok-cold-chain-pharma")
_HMAC_SECRET = os.environ.get("MEOK_HMAC_SECRET", "")


# ──────────────────────────────────────────────────────────────────────
# Regulatory tables
# ──────────────────────────────────────────────────────────────────────

# EU/UK GDP 2013/C 343/01 — 9 chapters
GDP_CHAPTERS = {
    "1_quality_management": "Quality system + change control + CAPA",
    "2_personnel": "Designated Responsible Person + trained staff",
    "3_premises_equipment": "Temperature mapping + qualified storage",
    "4_documentation": "SOPs + batch records + retention 5y minimum",
    "5_operations": "Goods-in qualification + supplier/customer due diligence",
    "6_complaints_returns_recalls": "Falsified product procedure + recall test annually",
    "7_outsourced_activities": "Written contracts + GDP audit of subcontractors",
    "8_self_inspections": "Annual internal GDP audit",
    "9_transportation": "Validated routes + temperature monitoring + qualified drivers",
}

# Standard cold-chain temperature bands (EMA + WHO)
TEMPERATURE_BANDS = {
    "ultra_cold_minus80": (-86.0, -60.0, "mRNA biologic ultra-cold"),
    "frozen_minus20": (-25.0, -15.0, "Frozen biologic"),
    "refrigerated_2_8": (2.0, 8.0, "Standard cold chain (most biologics + vaccines)"),
    "cool_8_15": (8.0, 15.0, "Cool storage"),
    "ambient_15_25": (15.0, 25.0, "Ambient room temperature"),
    "do_not_freeze_protect_from_frost": (2.0, 30.0, "Protect from frost / DNF"),
}

# Falsified Medicines Directive — EU vs UK post-Brexit divergence
FMD_DIVERGENCE = {
    "eu_fmd_2016_161": {
        "scope": "All POM in EU + Norway/Iceland/Liechtenstein",
        "registry": "European Medicines Verification System (EMVS)",
        "unique_identifier": "GS1 DataMatrix — product code, S/N, batch, expiry",
        "tamper_evident": "Required on outer packaging",
        "decommission_point": "At dispense to patient",
    },
    "uk_fmd_2019": {
        "scope": "Northern Ireland (still EU); GB ceased EMVS Jan 2021",
        "registry": "GB — no national system mandated post-Brexit (consultation paused)",
        "unique_identifier": "GB voluntary; NI = EU EMVS still",
        "tamper_evident": "MHRA expects on outer packaging despite no FMD",
        "decommission_point": "NI dispense or export; GB risk-based",
    },
    "windsor_framework_2024": {
        "scope": "NI dual-market access — MEDPACK fast-track scheme available",
        "ni_protocol_marker": "UKMA(NI) — Unfettered Access for GB→NI movements",
    },
}

# MHRA WDA(H) audit categories
MHRA_AUDIT_CATEGORIES = {
    "category_1_qms": "Quality management system + Responsible Person",
    "category_2_premises": "Premises, equipment + temperature mapping evidence",
    "category_3_operations": "Goods-in, picking, dispatch, returns SOPs",
    "category_4_documentation": "Batch records, complaint log, recall procedure",
    "category_5_subcontracting": "Outsourced storage + transport contracts",
    "category_6_self_inspection": "Annual internal GDP audit report",
    "category_7_complaints_recall": "Mock recall + falsified product procedure",
}

# Schedule classification for controlled drugs (Misuse of Drugs Regs 2001)
CONTROLLED_DRUGS_SCHEDULE = {
    "schedule_1": "No therapeutic use — Home Office licence required (cannabis, LSD)",
    "schedule_2": "Therapeutic POM — CD Register + safe custody (morphine, fentanyl)",
    "schedule_3": "POM — safe custody for some (temazepam, buprenorphine)",
    "schedule_4_part_1": "POM — benzodiazepines (diazepam)",
    "schedule_4_part_2": "POM — anabolic steroids (testosterone)",
    "schedule_5": "POM — preparations with low CD content (codeine combos)",
}

# Dry ice (UN1845) as a pharma cold-chain DG
DRY_ICE_ADR = {
    "un_number": "UN1845",
    "proper_shipping_name": "Carbon dioxide, solid (dry ice)",
    "class": "9",
    "packing_group": "n/a",
    "limited_quantity_kg": 200,
    "special_provision_904": "Asphyxiation risk — adequate ventilation required",
    "marking_required": "UN1845 + net weight kg",
    "iata_dgr_a151": "Air freight — pressure relief vent + UN-spec packaging",
}

# WHO TRS 961 + EU GDP §3 — temperature mapping qualification protocol
TEMP_MAPPING_REQUIREMENTS = {
    "winter_summer_mapping": "Both extremes required, 7-day continuous each",
    "minimum_sensors_per_100m3": 9,
    "loaded_unloaded_validation": "Both conditions required",
    "door_opening_simulation": "Worst-case door-open scenarios required",
    "calibration_traceable_uk_nplas": "Sensors traceable to NPL / UKAS",
    "deviation_limits": "Mean ±0.5°C of setpoint, no point >3°C deviation",
    "revalidation_interval_years": 3,
    "trigger_revalidation_events": [
        "HVAC change", "Layout change", "Cooling unit replacement",
        "Significant temperature excursion event", "Capacity expansion",
    ],
}


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _sign(payload: dict) -> str:
    """HMAC-sign the response for tamper-evident audit."""
    if not _HMAC_SECRET:
        return "unsigned-no-key-configured"
    return hmac.new(
        _HMAC_SECRET.encode(),
        json.dumps(payload, sort_keys=True, default=str).encode(),
        hashlib.sha256,
    ).hexdigest()


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _attestation(payload: dict) -> dict:
    return {
        **payload,
        "ts": _ts(),
        "sig": _sign(payload),
        "issuer": "meok-cold-chain-pharma-mcp",
        "version": "1.0.0",
    }


# ──────────────────────────────────────────────────────────────────────
# Tools
# ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def check_gdp_compliance(
    operator_name: str,
    wda_licence_number: str = "",
    responsible_person_named: bool = False,
    quality_system_documented: bool = False,
    temperature_mapping_current: bool = False,
    sop_count: int = 0,
    annual_self_inspection_completed: bool = False,
    mock_recall_within_12_months: bool = False,
    supplier_due_diligence_log: bool = False,
    falsified_product_procedure: bool = False,
) -> dict:
    """Check operator readiness against EU/UK GDP Guideline 2013/C 343/01.

    Args:
      operator_name: legal name of wholesale distributor
      wda_licence_number: MHRA WDA(H) licence ID (e.g. WDA(H) 12345)
      responsible_person_named: a named RP listed on the licence
      quality_system_documented: documented QMS with change control
      temperature_mapping_current: storage temperature mapping ≤3 years old
      sop_count: number of GDP SOPs in force
      annual_self_inspection_completed: latest internal audit ≤12 months
      mock_recall_within_12_months: GDP §6 recall test executed
      supplier_due_diligence_log: §5 supplier qualification records
      falsified_product_procedure: §6 SOP for FMD-suspect product

    Returns:
      compliance_score (0-100), gaps, advisory
    """
    chapters_passed = []
    gaps = []

    if quality_system_documented:
        chapters_passed.append("1_quality_management")
    else:
        gaps.append("Ch.1 — Documented QMS missing (GDP §1)")

    if responsible_person_named:
        chapters_passed.append("2_personnel")
    else:
        gaps.append("Ch.2 — Named Responsible Person required (GDP §2.2)")

    if temperature_mapping_current:
        chapters_passed.append("3_premises_equipment")
    else:
        gaps.append("Ch.3 — Temperature mapping out of date (GDP §3.2.1)")

    if sop_count >= 10:
        chapters_passed.append("4_documentation")
    else:
        gaps.append(f"Ch.4 — Only {sop_count} SOPs; minimum 10 expected (GDP §4)")

    if supplier_due_diligence_log:
        chapters_passed.append("5_operations")
    else:
        gaps.append("Ch.5 — Supplier due-diligence log missing (GDP §5.2)")

    if mock_recall_within_12_months and falsified_product_procedure:
        chapters_passed.append("6_complaints_returns_recalls")
    else:
        gaps.append("Ch.6 — Mock recall + FMD SOP both required (GDP §6.4)")

    if annual_self_inspection_completed:
        chapters_passed.append("8_self_inspections")
    else:
        gaps.append("Ch.8 — Annual self-inspection overdue (GDP §8)")

    # transport (Ch.9) requires separate tool — not graded here
    score = round(100 * len(chapters_passed) / 7)

    payload = {
        "tool": "check_gdp_compliance",
        "operator_name": operator_name,
        "wda_licence_number": wda_licence_number,
        "chapters_passed": chapters_passed,
        "gaps": gaps,
        "compliance_score": score,
        "audit_ready": score >= 85 and not gaps,
        "advisory": (
            "MHRA WDA(H) audit-ready — schedule self-inspection refresh."
            if score >= 85
            else f"Score {score}/100 — close {len(gaps)} gap(s) before next MHRA inspection."
        ),
        "regulatory_basis": "EU/UK GDP Guideline 2013/C 343/01",
    }
    return _attestation(payload)


@mcp.tool()
def check_qualified_person_responsible(
    rp_name: str,
    qualifications: Optional[list] = None,
    years_pharma_experience: int = 0,
    on_named_licence: bool = False,
    listed_on_mhra_register: bool = False,
    cpd_hours_last_12_months: int = 0,
    has_deputy_named: bool = False,
) -> dict:
    """Verify MHRA Responsible Person (RP) eligibility for a WDA(H).

    Per Article 79 of Directive 2001/83/EC + MHRA Best Practice Guidance,
    the RP must have suitable qualifications, sufficient experience,
    and be physically able to attend the premises.

    Args:
      rp_name: full legal name of the RP
      qualifications: list of qualifications (e.g. ["MPharm", "GDP Diploma"])
      years_pharma_experience: years working in pharma + distribution
      on_named_licence: explicitly named on the operator's WDA(H)
      listed_on_mhra_register: appears in MHRA public RP list
      cpd_hours_last_12_months: continuing professional development
      has_deputy_named: deputy RP named for absence cover
    """
    qualifications = qualifications or []
    issues = []

    acceptable_quals = {
        "MPharm", "MPharmS", "BPharm", "MSc Pharmacy",
        "RPSGB", "GPhC", "RP Gold Standard", "GDP Diploma",
        "Pharmacy Technician + RP training",
    }
    qual_match = any(q in acceptable_quals for q in qualifications)
    if not qual_match:
        issues.append(
            "No recognised qualification (need MPharm / GPhC / GDP Diploma / equivalent)"
        )

    if years_pharma_experience < 2:
        issues.append(f"Insufficient experience ({years_pharma_experience}y) — minimum 2y typical")
    if not on_named_licence:
        issues.append("Not named on the WDA(H) licence — RP must be explicitly listed")
    if not listed_on_mhra_register:
        issues.append("Not in MHRA RP register — submit RPgi notification")
    if cpd_hours_last_12_months < 20:
        issues.append(f"CPD only {cpd_hours_last_12_months}h — RPSGB recommends ≥20h/yr")
    if not has_deputy_named:
        issues.append("No deputy RP named — single point of failure on absence")

    payload = {
        "tool": "check_qualified_person_responsible",
        "rp_name": rp_name,
        "qualifications": qualifications,
        "years_pharma_experience": years_pharma_experience,
        "qualification_acceptable": qual_match,
        "licence_critical_issues": [i for i in issues if "WDA" in i or "register" in i],
        "all_issues": issues,
        "rp_eligible": not issues,
        "advisory": (
            "RP eligible — keep CPD log current and confirm deputy availability."
            if not issues
            else f"{len(issues)} blocker(s) — WDA(H) at risk until resolved."
        ),
        "regulatory_basis": "Article 79 Dir 2001/83/EC + MHRA RP Best Practice Guidance",
    }
    return _attestation(payload)


@mcp.tool()
def check_temperature_excursion(
    product_name: str,
    band: str = "refrigerated_2_8",
    readings_celsius: Optional[list] = None,
    duration_minutes: int = 0,
    sensor_count: int = 1,
    stability_data_excursion_window_minutes: int = 0,
) -> dict:
    """Detect a cold-chain temperature excursion + recommend remediation.

    Args:
      product_name: product/batch identifier
      band: storage band — 'refrigerated_2_8', 'frozen_minus20', 'ultra_cold_minus80', etc.
      readings_celsius: list of temperature readings during the event
      duration_minutes: total duration of the excursion in minutes
      sensor_count: how many sensors recorded the event
      stability_data_excursion_window_minutes: time the product is stability-rated
                                                outside the band per the SmPC
    """
    readings_celsius = readings_celsius or []
    if band not in TEMPERATURE_BANDS:
        band = "refrigerated_2_8"
    lo, hi, band_label = TEMPERATURE_BANDS[band]

    excursion_readings = [r for r in readings_celsius if r < lo or r > hi]
    max_deviation_c = 0.0
    if excursion_readings:
        max_deviation_c = max(
            abs(r - lo) if r < lo else abs(r - hi) for r in excursion_readings
        )

    excursion_detected = bool(excursion_readings) or duration_minutes > 0

    # Decision tree
    if not excursion_detected:
        decision = "WITHIN_LIMITS"
        action = "No action — log routine monitoring data."
    elif duration_minutes <= stability_data_excursion_window_minutes and max_deviation_c <= 2.0:
        decision = "WITHIN_STABILITY_BUDGET"
        action = (
            "Within stability-data excursion window — RP sign-off, release stock, "
            "log to deviation register."
        )
    elif duration_minutes > stability_data_excursion_window_minutes or max_deviation_c > 5.0:
        decision = "QUARANTINE_BATCH"
        action = (
            "Beyond stability budget — quarantine immediately, notify MAH, "
            "consider QP recall + write-off."
        )
    else:
        decision = "RP_RISK_ASSESSMENT_REQUIRED"
        action = (
            "RP-led risk assessment required — obtain stability data from MAH, "
            "document deviation, decide release/quarantine."
        )

    payload = {
        "tool": "check_temperature_excursion",
        "product_name": product_name,
        "band": band,
        "band_label": band_label,
        "band_lo_c": lo,
        "band_hi_c": hi,
        "excursion_readings": excursion_readings,
        "max_deviation_c": round(max_deviation_c, 2),
        "duration_minutes": duration_minutes,
        "sensor_count": sensor_count,
        "stability_budget_minutes": stability_data_excursion_window_minutes,
        "decision": decision,
        "remediation_action": action,
        "notifications_required": (
            ["MAH within 24h", "MHRA if defect", "QP/RP register entry"]
            if decision == "QUARANTINE_BATCH"
            else ["Deviation register entry"]
        ),
        "regulatory_basis": "EU GDP §9.2 + WHO TRS 961 + MAH SmPC stability data",
    }
    return _attestation(payload)


@mcp.tool()
def check_who_pq_compliance(
    product_name: str,
    manufacturer: str,
    destination_country: str = "",
    has_who_pq_listing: bool = False,
    has_vvm_label: bool = False,
    consignment_temperature_band: str = "refrigerated_2_8",
    has_cold_chain_monitor: bool = False,
    has_freeze_indicator: bool = False,
    intended_use: str = "epi",
) -> dict:
    """Check a consignment against WHO Prequalification (PQ) for global health.

    WHO PQ is required for any product procured by UN agencies (UNICEF, GAVI,
    Global Fund) or by recipient-country MoH under WHO programmes.

    Args:
      product_name: vaccine/biologic/medicine name
      manufacturer: marketing authorisation holder
      destination_country: ISO country code or name
      has_who_pq_listing: product is on the WHO PQ list
      has_vvm_label: Vaccine Vial Monitor present (EPI vaccines)
      consignment_temperature_band: cold-chain band
      has_cold_chain_monitor: continuous CCM device included
      has_freeze_indicator: Freeze-Tag / 30DAY indicator present
      intended_use: 'epi' (vaccines), 'malaria', 'tb', 'hiv', 'mch', 'general'
    """
    issues = []
    warnings = []

    if not has_who_pq_listing:
        issues.append("Product not on WHO PQ list — UN procurement blocked")

    if intended_use == "epi":
        if not has_vvm_label:
            issues.append("EPI vaccine — VVM label required (WHO/IVB/07.04)")
        if not has_freeze_indicator and consignment_temperature_band == "refrigerated_2_8":
            issues.append("EPI cold-chain — freeze indicator required (Freeze-Tag/30DAY)")

    if consignment_temperature_band in ("refrigerated_2_8", "frozen_minus20", "ultra_cold_minus80"):
        if not has_cold_chain_monitor:
            issues.append("Cold-chain product — CCM device required for last-mile evidence")

    high_risk_destinations = {"AFG", "YEM", "SDN", "SSD", "SYR", "AFGHANISTAN", "YEMEN"}
    if destination_country.upper() in high_risk_destinations:
        warnings.append(
            f"Destination {destination_country} is high-risk — "
            "consider WHO Emergency Use Listing pathway"
        )

    payload = {
        "tool": "check_who_pq_compliance",
        "product_name": product_name,
        "manufacturer": manufacturer,
        "destination_country": destination_country,
        "intended_use": intended_use,
        "consignment_temperature_band": consignment_temperature_band,
        "has_who_pq_listing": has_who_pq_listing,
        "has_vvm_label": has_vvm_label,
        "has_cold_chain_monitor": has_cold_chain_monitor,
        "has_freeze_indicator": has_freeze_indicator,
        "blocking_issues": issues,
        "warnings": warnings,
        "ready_for_un_procurement": not issues,
        "advisory": (
            "Consignment WHO-PQ compliant — ready for UNICEF/GAVI/Global Fund shipment."
            if not issues
            else f"{len(issues)} blocker(s) — UN procurement / programme delivery blocked."
        ),
        "regulatory_basis": "WHO PQ Programme + WHO TRS 961 Annex 9",
    }
    return _attestation(payload)


@mcp.tool()
def check_serialisation_falsified_medicines(
    product_name: str,
    market: str = "GB",
    has_gs1_datamatrix: bool = False,
    has_tamper_evident_seal: bool = False,
    unique_identifier_components: Optional[list] = None,
    decommissioned_at_dispense: bool = False,
    emvs_registered: bool = False,
) -> dict:
    """Check FMD serialisation status — EU vs UK post-Brexit divergence.

    Args:
      product_name: product name/SKU
      market: 'EU' / 'NI' / 'GB' (post-Brexit GB is no longer in EMVS)
      has_gs1_datamatrix: 2D barcode on outer packaging
      has_tamper_evident_seal: anti-tamper device on outer packaging
      unique_identifier_components: GS1 elements present
                                    (e.g. ["product_code","serial","batch","expiry"])
      decommissioned_at_dispense: pharmacy scan at point of dispense
      emvs_registered: pack S/N uploaded to EMVS hub
    """
    unique_identifier_components = unique_identifier_components or []
    issues = []
    market_upper = market.upper()

    required_ui = {"product_code", "serial", "batch", "expiry"}
    missing_ui = required_ui - set(unique_identifier_components)

    if market_upper in ("EU", "NI"):
        # Full FMD applies
        if not has_gs1_datamatrix:
            issues.append(f"{market_upper} FMD — GS1 DataMatrix required on outer pack")
        if missing_ui:
            issues.append(f"Missing UI elements: {sorted(missing_ui)}")
        if not has_tamper_evident_seal:
            issues.append(f"{market_upper} FMD — tamper-evident seal required")
        if not emvs_registered:
            issues.append(f"{market_upper} FMD — pack not registered in EMVS hub")
        if not decommissioned_at_dispense:
            issues.append(f"{market_upper} FMD — decommission scan at dispense missing")
        compliance_regime = "EU FMD (Delegated Reg 2016/161)"
    elif market_upper == "GB":
        # GB exited EMVS — MHRA expects tamper-evident + risk-based UI
        if not has_tamper_evident_seal:
            issues.append("GB — MHRA expects tamper-evident seal despite no FMD")
        compliance_regime = "UK FMD 2019 (post-Brexit, no EMVS)"
    else:
        issues.append(f"Unknown market '{market}'")
        compliance_regime = "unknown"

    payload = {
        "tool": "check_serialisation_falsified_medicines",
        "product_name": product_name,
        "market": market_upper,
        "compliance_regime": compliance_regime,
        "has_gs1_datamatrix": has_gs1_datamatrix,
        "has_tamper_evident_seal": has_tamper_evident_seal,
        "unique_identifier_components_present": sorted(set(unique_identifier_components)),
        "missing_ui_elements": sorted(missing_ui) if market_upper in ("EU", "NI") else [],
        "issues": issues,
        "fmd_compliant": not issues,
        "advisory": (
            f"{compliance_regime} compliant — pack releasable."
            if not issues
            else f"{len(issues)} FMD blocker(s) — pack cannot be released until resolved."
        ),
        "divergence_note": (
            "Windsor Framework 2024 — NI dual-market access; "
            "GB→NI moves need UKMA(NI) marker."
        ),
        "regulatory_basis": "EU FMD Dir 2011/62/EU + Delegated Reg 2016/161 + UK FMD Regs 2019",
    }
    return _attestation(payload)


@mcp.tool()
def prepare_mhra_audit_pack(
    operator_name: str,
    wda_licence_number: str = "",
    rp_name: str = "",
    inspection_date_iso: str = "",
    qms_documented: bool = False,
    temperature_mapping_current: bool = False,
    sop_count: int = 0,
    mock_recall_completed: bool = False,
    self_inspection_completed: bool = False,
    subcontractor_audits_logged: bool = False,
    fmd_procedure_documented: bool = False,
) -> dict:
    """Prepare the MHRA WDA(H) inspection pack — 7 audit categories.

    Returns a structured pack itemising what is ready vs. what needs work
    before the named inspection date.

    Args:
      operator_name: legal name of the licensed wholesale distributor
      wda_licence_number: e.g. 'WDA(H) 12345'
      rp_name: named Responsible Person
      inspection_date_iso: scheduled inspection date YYYY-MM-DD
      qms_documented: documented quality management system
      temperature_mapping_current: mapping ≤3y old
      sop_count: number of GDP SOPs maintained
      mock_recall_completed: §6 recall test within 12 months
      self_inspection_completed: §8 annual self-inspection complete
      subcontractor_audits_logged: §7 GDP audits of outsourced parties
      fmd_procedure_documented: §6.4 falsified product handling SOP
    """
    pack = {}
    gaps = []

    # Cat 1 — QMS
    pack["category_1_qms"] = {
        "ready": qms_documented and bool(rp_name),
        "evidence_needed": [
            "Quality manual",
            "RP appointment letter + CV",
            "Change-control log",
            "CAPA tracker",
        ],
    }
    if not pack["category_1_qms"]["ready"]:
        gaps.append("Cat 1 — QMS or RP letter missing")

    # Cat 2 — Premises
    pack["category_2_premises"] = {
        "ready": temperature_mapping_current,
        "evidence_needed": [
            "Temperature mapping report (winter + summer)",
            "Sensor calibration certificates (UKAS-traceable)",
            "HVAC service log",
            "Floor plan with sensor positions",
        ],
    }
    if not pack["category_2_premises"]["ready"]:
        gaps.append("Cat 2 — temperature mapping out of date")

    # Cat 3 — Operations
    pack["category_3_operations"] = {
        "ready": sop_count >= 10,
        "evidence_needed": [
            "Goods-in SOP", "Picking SOP", "Dispatch SOP",
            "Returns SOP", "Damaged-stock SOP", "Cold-chain SOP",
        ],
    }
    if not pack["category_3_operations"]["ready"]:
        gaps.append(f"Cat 3 — only {sop_count} SOPs in force")

    # Cat 4 — Documentation
    pack["category_4_documentation"] = {
        "ready": sop_count >= 10,
        "evidence_needed": [
            "Batch records (sample)", "Complaint log", "Deviation log",
            "Retention policy (5y minimum)",
        ],
    }

    # Cat 5 — Subcontracting
    pack["category_5_subcontracting"] = {
        "ready": subcontractor_audits_logged,
        "evidence_needed": [
            "Quality Technical Agreements (QTA)",
            "Sub-tier GDP audit reports",
            "Approved supplier list",
        ],
    }
    if not pack["category_5_subcontracting"]["ready"]:
        gaps.append("Cat 5 — subcontractor GDP audit evidence missing")

    # Cat 6 — Self-inspection
    pack["category_6_self_inspection"] = {
        "ready": self_inspection_completed,
        "evidence_needed": [
            "Annual self-inspection report",
            "CAPA closure evidence",
        ],
    }
    if not pack["category_6_self_inspection"]["ready"]:
        gaps.append("Cat 6 — self-inspection overdue")

    # Cat 7 — Complaints + recall + FMD
    pack["category_7_complaints_recall"] = {
        "ready": mock_recall_completed and fmd_procedure_documented,
        "evidence_needed": [
            "Mock recall report (within 12m)",
            "FMD-suspect product SOP",
            "Recall contact tree (24/7)",
        ],
    }
    if not pack["category_7_complaints_recall"]["ready"]:
        gaps.append("Cat 7 — mock recall + FMD SOP both required")

    days_to_inspection = -1
    if inspection_date_iso:
        try:
            insp = date.fromisoformat(inspection_date_iso)
            days_to_inspection = (insp - date.today()).days
        except Exception:
            pass

    ready_count = sum(1 for c in pack.values() if c["ready"])

    payload = {
        "tool": "prepare_mhra_audit_pack",
        "operator_name": operator_name,
        "wda_licence_number": wda_licence_number,
        "rp_name": rp_name,
        "inspection_date_iso": inspection_date_iso,
        "days_to_inspection": days_to_inspection,
        "pack": pack,
        "categories_ready": ready_count,
        "categories_total": 7,
        "gaps": gaps,
        "audit_ready": ready_count == 7,
        "advisory": (
            "WDA(H) audit pack ready — schedule RP pre-inspection walk-through."
            if ready_count == 7
            else f"{len(gaps)} gap(s) — close before MHRA inspection."
        ),
        "regulatory_basis": "MHRA WDA(H) inspection framework + GDP 2013/C 343/01",
    }
    return _attestation(payload)


@mcp.tool()
def check_dangerous_goods_pharma(
    consignment_id: str,
    contains_dry_ice: bool = False,
    dry_ice_kg: float = 0.0,
    contains_controlled_drugs: bool = False,
    cd_schedule: str = "",
    transport_mode: str = "road",
    contains_lithium_temperature_logger: bool = False,
) -> dict:
    """Check DG overlap on a pharma consignment.

    Pharma cold-chain creates two DG hot spots:
      1) Dry ice (UN1845, ADR Class 9) for frozen + ultra-cold biologics
      2) Schedule 1-5 controlled drugs (Misuse of Drugs Regs 2001)
         which need locked custody, CD register, Home Office cover.
    A third hot spot is the lithium temperature logger packed with the
    consignment — usually UN3091/3481 exempted small-cell but still
    requires lithium-battery handling label.

    Args:
      consignment_id: shipment ID / waybill
      contains_dry_ice: dry ice present as refrigerant
      dry_ice_kg: net mass of dry ice
      contains_controlled_drugs: any Schedule 1-5 CD present
      cd_schedule: 'schedule_1' / 'schedule_2' / 'schedule_3' / 'schedule_4_part_1'/2 / 'schedule_5'
      transport_mode: 'road' / 'air' / 'sea'
      contains_lithium_temperature_logger: e.g. Sensitech LIBERO / Berlinger Q-tag
    """
    flags = []
    paperwork_required = []

    if contains_dry_ice:
        flags.append("UN1845 — Carbon dioxide solid (dry ice), ADR Class 9")
        if dry_ice_kg > DRY_ICE_ADR["limited_quantity_kg"]:
            paperwork_required.append(
                f"Dry ice {dry_ice_kg}kg > {DRY_ICE_ADR['limited_quantity_kg']}kg "
                "LQ — full ADR transport document required"
            )
        else:
            paperwork_required.append(
                f"Dry ice {dry_ice_kg}kg ≤ LQ — limited-quantity marking + UN1845 + net weight"
            )
        paperwork_required.append("Asphyxiation risk — vehicle ventilation per SP904")
        if transport_mode == "air":
            paperwork_required.append("IATA DGR — pressure relief vent + UN-spec outer")

    if contains_controlled_drugs:
        cd_info = CONTROLLED_DRUGS_SCHEDULE.get(cd_schedule, "Unknown schedule — escalate to RP")
        flags.append(f"Controlled drug {cd_schedule}: {cd_info}")
        if cd_schedule in ("schedule_1", "schedule_2", "schedule_3"):
            paperwork_required.append("CD Register entry + safe-custody compliant transit")
            paperwork_required.append("Home Office Domestic Licence cover required")
            paperwork_required.append("DGSA pre-load attestation (high-value pharma)")

    if contains_lithium_temperature_logger:
        flags.append("Lithium-battery temperature logger — UN3091/3481 SP188 typically exempted")
        paperwork_required.append("Lithium-battery handling label (Class 9 mini) on outer pack")

    if not flags:
        return _attestation({
            "tool": "check_dangerous_goods_pharma",
            "consignment_id": consignment_id,
            "dg_flags": [],
            "paperwork_required": [],
            "advisory": "No DG triggers — standard GDP transport SOP applies.",
            "regulatory_basis": "ADR 2025 + Misuse of Drugs Regs 2001",
        })

    payload = {
        "tool": "check_dangerous_goods_pharma",
        "consignment_id": consignment_id,
        "transport_mode": transport_mode,
        "dg_flags": flags,
        "paperwork_required": paperwork_required,
        "dgsa_signoff_required": (
            contains_controlled_drugs or
            (contains_dry_ice and dry_ice_kg > DRY_ICE_ADR["limited_quantity_kg"])
        ),
        "advisory": (
            f"{len(flags)} DG trigger(s) on this consignment — "
            "DGSA + RP joint sign-off recommended before dispatch."
        ),
        "regulatory_basis": "ADR 2025 (UN1845/UN3091) + Misuse of Drugs Regs 2001 + IATA DGR",
    }
    return _attestation(payload)


@mcp.tool()
def validate_temperature_mapping_qualification(
    facility_name: str,
    storage_volume_m3: float = 0.0,
    band: str = "refrigerated_2_8",
    last_mapping_date_iso: str = "",
    sensor_count: int = 0,
    winter_summer_both: bool = False,
    loaded_unloaded_both: bool = False,
    door_opening_simulated: bool = False,
    sensors_ukas_traceable: bool = False,
    max_deviation_during_mapping_c: float = 0.0,
) -> dict:
    """Validate a temperature-mapping qualification per WHO TRS 961 + EU GDP §3.

    Args:
      facility_name: storage facility / cold-room ID
      storage_volume_m3: gross internal volume of the mapped area
      band: temperature band — e.g. 'refrigerated_2_8'
      last_mapping_date_iso: date of most recent qualification, YYYY-MM-DD
      sensor_count: number of mapping sensors used
      winter_summer_both: both seasons mapped
      loaded_unloaded_both: both load conditions mapped
      door_opening_simulated: worst-case door-open scenarios simulated
      sensors_ukas_traceable: sensors traceable to NPL / UKAS calibration
      max_deviation_during_mapping_c: largest point excursion observed (°C)
    """
    issues = []

    # Sensor density (per 100 m³)
    required_sensors = max(
        9,
        int((storage_volume_m3 / 100.0) * TEMP_MAPPING_REQUIREMENTS["minimum_sensors_per_100m3"]),
    ) if storage_volume_m3 > 0 else 9
    if sensor_count < required_sensors:
        issues.append(
            f"Only {sensor_count} sensors; {required_sensors} required for "
            f"{storage_volume_m3} m³ (≥9 per 100 m³)"
        )

    if not winter_summer_both:
        issues.append("Winter + summer mapping both required (WHO TRS 961 Annex 9)")
    if not loaded_unloaded_both:
        issues.append("Loaded + unloaded mapping both required")
    if not door_opening_simulated:
        issues.append("Door-opening worst-case simulation missing")
    if not sensors_ukas_traceable:
        issues.append("Sensor calibration must be UKAS/NPL traceable")
    if max_deviation_during_mapping_c > 3.0:
        issues.append(
            f"Max deviation {max_deviation_during_mapping_c}°C exceeds 3°C limit"
        )

    days_since_mapping = -1
    revalidation_due = False
    if last_mapping_date_iso:
        try:
            m = date.fromisoformat(last_mapping_date_iso)
            days_since_mapping = (date.today() - m).days
            if days_since_mapping > 365 * TEMP_MAPPING_REQUIREMENTS["revalidation_interval_years"]:
                revalidation_due = True
                issues.append(
                    f"Mapping {days_since_mapping}d old — "
                    f"revalidation due (≥{TEMP_MAPPING_REQUIREMENTS['revalidation_interval_years']}y)"
                )
        except Exception:
            issues.append(f"Invalid mapping date '{last_mapping_date_iso}'")

    payload = {
        "tool": "validate_temperature_mapping_qualification",
        "facility_name": facility_name,
        "band": band,
        "storage_volume_m3": storage_volume_m3,
        "sensor_count": sensor_count,
        "required_sensors": required_sensors,
        "last_mapping_date_iso": last_mapping_date_iso,
        "days_since_mapping": days_since_mapping,
        "revalidation_due": revalidation_due,
        "issues": issues,
        "qualification_valid": not issues,
        "trigger_revalidation_events": TEMP_MAPPING_REQUIREMENTS["trigger_revalidation_events"],
        "advisory": (
            "Temperature mapping qualification valid — "
            "log next revalidation date in CMMS."
            if not issues
            else f"{len(issues)} qualification gap(s) — facility cannot hold GDP-grade stock until resolved."
        ),
        "regulatory_basis": "WHO TRS 961 Annex 9 + EU GDP §3.2.1 + USP 1079",
    }
    return _attestation(payload)


# ──────────────────────────────────────────────────────────────────────
# Server entry
# ──────────────────────────────────────────────────────────────────────

def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()


# ── MEOK monetization layer (Stripe upgrade · PAYG · pricing) ──────────
# Free tier is zero-config. Upgrade to Pro (unlimited) or pay-as-you-go per call.
import os as _meok_os
MEOK_STRIPE_UPGRADE = "https://buy.stripe.com/5kQ6oJ0xS3ce8sl7ew8k91j"  # Pro (unlimited)
MEOK_PAYG_KEY = _meok_os.environ.get("MEOK_PAYG_KEY", "")  # set to enable PAYG (x402 / ~GBP0.05 per call)
MEOK_PRICING = "https://meok.ai/pricing"


def meok_upsell(tier: str = "free") -> dict:
    """Monetization options for free-tier callers: Pro upgrade, PAYG, or pricing page."""
    if tier != "free":
        return {}
    return {"upgrade_url": MEOK_STRIPE_UPGRADE,
            "payg_enabled": bool(MEOK_PAYG_KEY),
            "pricing": MEOK_PRICING}
