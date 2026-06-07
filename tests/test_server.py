"""Smoke tests for meok-cold-chain-pharma-mcp."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import (
    check_gdp_compliance,
    check_qualified_person_responsible,
    check_temperature_excursion,
    check_who_pq_compliance,
    check_serialisation_falsified_medicines,
    prepare_mhra_audit_pack,
    check_dangerous_goods_pharma,
    validate_temperature_mapping_qualification,
    GDP_CHAPTERS,
    TEMPERATURE_BANDS,
    FMD_DIVERGENCE,
    MHRA_AUDIT_CATEGORIES,
    CONTROLLED_DRUGS_SCHEDULE,
    DRY_ICE_ADR,
    TEMP_MAPPING_REQUIREMENTS,
)


def _call(tool, **kwargs):
    """FastMCP wraps tools as Tool objects — extract the callable."""
    fn = tool.fn if hasattr(tool, "fn") else tool
    return fn(**kwargs)


# ─── check_gdp_compliance ──────────────────────────────────────────────

def test_gdp_full_house_passes():
    r = _call(check_gdp_compliance,
              operator_name="BigPharma Distribution UK Ltd",
              wda_licence_number="WDA(H) 12345",
              responsible_person_named=True,
              quality_system_documented=True,
              temperature_mapping_current=True,
              sop_count=15,
              annual_self_inspection_completed=True,
              mock_recall_within_12_months=True,
              supplier_due_diligence_log=True,
              falsified_product_procedure=True)
    assert r["compliance_score"] == 100
    assert r["audit_ready"] is True
    assert r["gaps"] == []


def test_gdp_missing_rp_drops_score():
    r = _call(check_gdp_compliance,
              operator_name="StartupRx Ltd",
              responsible_person_named=False,
              quality_system_documented=True,
              temperature_mapping_current=False,
              sop_count=2)
    assert r["compliance_score"] < 100
    assert r["audit_ready"] is False
    assert any("Responsible Person" in g for g in r["gaps"])
    assert any("Temperature mapping" in g for g in r["gaps"])


# ─── check_qualified_person_responsible ───────────────────────────────

def test_rp_with_full_creds_eligible():
    r = _call(check_qualified_person_responsible,
              rp_name="Dr Alice Pharmacist",
              qualifications=["MPharm", "GDP Diploma"],
              years_pharma_experience=8,
              on_named_licence=True,
              listed_on_mhra_register=True,
              cpd_hours_last_12_months=25,
              has_deputy_named=True)
    assert r["rp_eligible"] is True
    assert r["qualification_acceptable"] is True
    assert r["all_issues"] == []


def test_rp_missing_licence_flag_blocks():
    r = _call(check_qualified_person_responsible,
              rp_name="Bob Trainee",
              qualifications=["BSc Chemistry"],
              years_pharma_experience=1,
              on_named_licence=False,
              listed_on_mhra_register=False,
              cpd_hours_last_12_months=0,
              has_deputy_named=False)
    assert r["rp_eligible"] is False
    assert len(r["licence_critical_issues"]) >= 2
    assert any("WDA" in i for i in r["all_issues"])
    assert any("MHRA RP register" in i for i in r["all_issues"])


# ─── check_temperature_excursion ──────────────────────────────────────

def test_excursion_within_limits():
    r = _call(check_temperature_excursion,
              product_name="Insulin Lispro 100u/ml",
              band="refrigerated_2_8",
              readings_celsius=[3.1, 4.5, 5.2, 6.0, 7.8],
              duration_minutes=0)
    assert r["decision"] == "WITHIN_LIMITS"
    assert r["excursion_readings"] == []


def test_excursion_quarantine_triggers():
    r = _call(check_temperature_excursion,
              product_name="mRNA Vaccine",
              band="ultra_cold_minus80",
              readings_celsius=[-20.0, -15.0, -10.0, -5.0],
              duration_minutes=180,
              sensor_count=3,
              stability_data_excursion_window_minutes=30)
    assert r["decision"] == "QUARANTINE_BATCH"
    assert r["max_deviation_c"] > 5.0
    assert any("MAH" in n for n in r["notifications_required"])


def test_excursion_within_stability_budget():
    r = _call(check_temperature_excursion,
              product_name="Adalimumab biosimilar",
              band="refrigerated_2_8",
              readings_celsius=[1.2, 9.5, 8.3],
              duration_minutes=15,
              sensor_count=1,
              stability_data_excursion_window_minutes=120)
    assert r["decision"] == "WITHIN_STABILITY_BUDGET"
    assert r["excursion_readings"]  # non-empty


# ─── check_who_pq_compliance ──────────────────────────────────────────

def test_who_pq_epi_vaccine_fully_compliant():
    r = _call(check_who_pq_compliance,
              product_name="Measles vaccine",
              manufacturer="Serum Institute of India",
              destination_country="NGA",
              has_who_pq_listing=True,
              has_vvm_label=True,
              consignment_temperature_band="refrigerated_2_8",
              has_cold_chain_monitor=True,
              has_freeze_indicator=True,
              intended_use="epi")
    assert r["ready_for_un_procurement"] is True
    assert r["blocking_issues"] == []


def test_who_pq_missing_vvm_blocks():
    r = _call(check_who_pq_compliance,
              product_name="Polio vaccine",
              manufacturer="Bio Farma",
              destination_country="YEM",
              has_who_pq_listing=True,
              has_vvm_label=False,
              consignment_temperature_band="refrigerated_2_8",
              has_cold_chain_monitor=False,
              has_freeze_indicator=False,
              intended_use="epi")
    assert r["ready_for_un_procurement"] is False
    assert any("VVM" in i for i in r["blocking_issues"])
    assert len(r["warnings"]) >= 1  # YEM is high-risk


# ─── check_serialisation_falsified_medicines ──────────────────────────

def test_fmd_eu_full_compliant():
    r = _call(check_serialisation_falsified_medicines,
              product_name="Atorvastatin 40mg",
              market="EU",
              has_gs1_datamatrix=True,
              has_tamper_evident_seal=True,
              unique_identifier_components=["product_code", "serial", "batch", "expiry"],
              decommissioned_at_dispense=True,
              emvs_registered=True)
    assert r["fmd_compliant"] is True
    assert r["compliance_regime"].startswith("EU FMD")


def test_fmd_gb_post_brexit_relaxed():
    r = _call(check_serialisation_falsified_medicines,
              product_name="Paracetamol 500mg POM",
              market="GB",
              has_gs1_datamatrix=False,
              has_tamper_evident_seal=True,
              unique_identifier_components=[])
    # GB post-Brexit doesn't require full FMD — only tamper-evident matters
    assert r["fmd_compliant"] is True
    assert "UK FMD" in r["compliance_regime"]


def test_fmd_ni_treated_as_eu():
    r = _call(check_serialisation_falsified_medicines,
              product_name="Insulin glargine",
              market="NI",
              has_gs1_datamatrix=False,
              has_tamper_evident_seal=False)
    assert r["fmd_compliant"] is False
    assert any("DataMatrix" in i for i in r["issues"])


# ─── prepare_mhra_audit_pack ──────────────────────────────────────────

def test_mhra_audit_pack_ready():
    r = _call(prepare_mhra_audit_pack,
              operator_name="National Pharma 3PL",
              wda_licence_number="WDA(H) 98765",
              rp_name="Dr Carol RP",
              inspection_date_iso="2027-01-15",
              qms_documented=True,
              temperature_mapping_current=True,
              sop_count=20,
              mock_recall_completed=True,
              self_inspection_completed=True,
              subcontractor_audits_logged=True,
              fmd_procedure_documented=True)
    assert r["audit_ready"] is True
    assert r["categories_ready"] == 7
    assert r["gaps"] == []


def test_mhra_audit_pack_gaps_listed():
    r = _call(prepare_mhra_audit_pack,
              operator_name="Newco Distribution",
              wda_licence_number="WDA(H) PENDING",
              qms_documented=False,
              temperature_mapping_current=False,
              sop_count=3,
              mock_recall_completed=False,
              self_inspection_completed=False)
    assert r["audit_ready"] is False
    assert r["categories_ready"] < 7
    assert len(r["gaps"]) >= 4


# ─── check_dangerous_goods_pharma ─────────────────────────────────────

def test_dg_pharma_no_triggers():
    r = _call(check_dangerous_goods_pharma,
              consignment_id="CON-001",
              contains_dry_ice=False,
              contains_controlled_drugs=False)
    assert r["dg_flags"] == []
    assert "No DG triggers" in r["advisory"]


def test_dg_pharma_dry_ice_over_lq_triggers_full_adr():
    r = _call(check_dangerous_goods_pharma,
              consignment_id="CON-COLDPACK-002",
              contains_dry_ice=True,
              dry_ice_kg=500.0,
              transport_mode="road")
    assert any("UN1845" in f for f in r["dg_flags"])
    assert any("full ADR" in p for p in r["paperwork_required"])
    assert r["dgsa_signoff_required"] is True


def test_dg_pharma_controlled_drug_sched2_triggers_cdr():
    r = _call(check_dangerous_goods_pharma,
              consignment_id="CON-CD-003",
              contains_controlled_drugs=True,
              cd_schedule="schedule_2",
              transport_mode="road")
    assert any("safe-custody" in p for p in r["paperwork_required"])
    assert any("Home Office" in p for p in r["paperwork_required"])
    assert r["dgsa_signoff_required"] is True


# ─── validate_temperature_mapping_qualification ───────────────────────

def test_temp_mapping_valid_small_facility():
    r = _call(validate_temperature_mapping_qualification,
              facility_name="ColdRoom-A",
              storage_volume_m3=80.0,
              band="refrigerated_2_8",
              last_mapping_date_iso="2026-01-01",
              sensor_count=12,
              winter_summer_both=True,
              loaded_unloaded_both=True,
              door_opening_simulated=True,
              sensors_ukas_traceable=True,
              max_deviation_during_mapping_c=1.5)
    assert r["qualification_valid"] is True
    assert r["issues"] == []


def test_temp_mapping_insufficient_sensors_flagged():
    r = _call(validate_temperature_mapping_qualification,
              facility_name="ColdRoom-B",
              storage_volume_m3=300.0,
              band="refrigerated_2_8",
              last_mapping_date_iso="2026-01-01",
              sensor_count=5,
              winter_summer_both=True,
              loaded_unloaded_both=True,
              door_opening_simulated=True,
              sensors_ukas_traceable=True,
              max_deviation_during_mapping_c=2.0)
    assert r["qualification_valid"] is False
    assert any("sensors" in i for i in r["issues"])


def test_temp_mapping_revalidation_overdue():
    r = _call(validate_temperature_mapping_qualification,
              facility_name="ColdRoom-Legacy",
              storage_volume_m3=50.0,
              last_mapping_date_iso="2020-01-01",
              sensor_count=10,
              winter_summer_both=True,
              loaded_unloaded_both=True,
              door_opening_simulated=True,
              sensors_ukas_traceable=True,
              max_deviation_during_mapping_c=2.0)
    assert r["revalidation_due"] is True
    assert r["qualification_valid"] is False


# ─── attestation + HMAC ───────────────────────────────────────────────

def test_attestation_unsigned_when_no_key():
    # No MEOK_HMAC_SECRET set in test env → sig field is the placeholder
    os.environ.pop("MEOK_HMAC_SECRET", None)
    import importlib, server as server_mod
    importlib.reload(server_mod)
    r = _call(server_mod.check_gdp_compliance, operator_name="X")
    assert "sig" in r
    assert "ts" in r
    assert r["issuer"] == "meok-cold-chain-pharma-mcp"
    assert r["sig"] == "unsigned-no-key-configured"


def test_attestation_signed_when_key_set():
    os.environ["MEOK_HMAC_SECRET"] = "test-secret-key-only"
    import importlib, server as server_mod
    importlib.reload(server_mod)
    r1 = _call(server_mod.check_gdp_compliance, operator_name="Operator A")
    # Same inputs → different ts → different sig is fine,
    # but the sig field MUST be a hex digest, not the placeholder
    assert r1["sig"] != "unsigned-no-key-configured"
    assert len(r1["sig"]) == 64  # SHA-256 hex
    assert all(c in "0123456789abcdef" for c in r1["sig"])
    # Cleanup
    os.environ.pop("MEOK_HMAC_SECRET", None)
    importlib.reload(server_mod)


# ─── Reference table integrity ────────────────────────────────────────

def test_gdp_chapters_has_nine_chapters():
    assert len(GDP_CHAPTERS) == 9


def test_temperature_bands_includes_ultra_cold():
    assert "ultra_cold_minus80" in TEMPERATURE_BANDS
    lo, hi, _ = TEMPERATURE_BANDS["ultra_cold_minus80"]
    assert lo == -86.0 and hi == -60.0


def test_fmd_divergence_has_eu_uk_windsor():
    assert "eu_fmd_2016_161" in FMD_DIVERGENCE
    assert "uk_fmd_2019" in FMD_DIVERGENCE
    assert "windsor_framework_2024" in FMD_DIVERGENCE


def test_mhra_audit_has_seven_categories():
    assert len(MHRA_AUDIT_CATEGORIES) == 7


def test_controlled_drugs_has_all_schedules():
    expected = {"schedule_1", "schedule_2", "schedule_3",
                "schedule_4_part_1", "schedule_4_part_2", "schedule_5"}
    assert set(CONTROLLED_DRUGS_SCHEDULE.keys()) == expected


def test_dry_ice_un1845_class_9():
    assert DRY_ICE_ADR["un_number"] == "UN1845"
    assert DRY_ICE_ADR["class"] == "9"


def test_temp_mapping_requirements_revalidation_3y():
    assert TEMP_MAPPING_REQUIREMENTS["revalidation_interval_years"] == 3
    assert TEMP_MAPPING_REQUIREMENTS["minimum_sensors_per_100m3"] == 9


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
