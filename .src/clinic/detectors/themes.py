"""Thematic trend detectors.

Each theme aggregates multiple related signals across bloodwork, wearables,
and the drug timeline. The theme identifies patterns and produces findings
that the LLM uses to reason about what's happening and why.

Themes (in order of clinical importance for enhanced athletes):
1. Cardiovascular Stress — the #1 killer. Hematocrit, BP, HR, HRV, lipids.
2. Hepatic Load — liver strain from 17aa orals. ALT, AST, GGT, bilirubin.
3. Hormonal Balance — E2 management, prolactin, SHBG, HPTA status.
4. Metabolic Health — glucose, insulin, A1c, weight. GH/peptide effects.
5. Renal Function — creatinine (confounded by muscle), BUN, eGFR, cystatin C.
6. Hematological — full CBC picture beyond hematocrit.
7. Inflammation & Vascular Risk — hs-CRP, homocysteine, ApoB, Lp(a).
8. Recovery & HPTA — post-cycle LH/FSH/T recovery tracking.
"""

from __future__ import annotations

import sqlite3
from datetime import date

from clinic.detectors.framework import (
    DrugContext,
    Finding,
    Severity,
    Signal,
    compute_trend,
    get_active_compounds,
    get_metric_series,
    get_wearable_series,
    store_finding,
)


def run_all_detectors(
    conn: sqlite3.Connection,
    user_id: str = "default",
    as_of: str | None = None,
) -> list[Finding]:
    """Run all theme detectors and return findings."""
    if as_of is None:
        as_of = date.today().isoformat()

    findings: list[Finding] = []

    detectors = [
        detect_cardiovascular_stress,
        detect_hepatic_load,
        detect_hormonal_balance,
        detect_metabolic_health,
        detect_renal_function,
        detect_hematological,
        detect_inflammation_vascular,
        detect_recovery_hpta,
    ]

    for detector in detectors:
        result = detector(conn, user_id, as_of)
        if result:
            findings.append(result)
            store_finding(conn, result, user_id)

    return findings


# =============================================================================
# THEME 1: CARDIOVASCULAR STRESS
# The most important theme. AAS-related cardiovascular events are the #1 acute
# risk. Aggregates: hematocrit, hemoglobin, BP, resting HR, HRV, lipids.
# =============================================================================

def detect_cardiovascular_stress(
    conn: sqlite3.Connection,
    user_id: str,
    as_of: str,
) -> Finding | None:
    """Detect cardiovascular stress signals."""
    signals: list[Signal] = []
    drug_ctx = get_active_compounds(conn, as_of, user_id)

    # --- Hematocrit ---
    hct_series = get_metric_series(conn, "4544-3", user_id)  # Hematocrit
    if hct_series:
        direction, change = compute_trend(hct_series)
        latest = hct_series[-1][1]
        baseline = hct_series[0][1] if len(hct_series) > 1 else None

        if latest >= 54:
            signals.append(Signal(
                metric="Hematocrit", trend_direction=direction,
                value_current=latest, value_baseline=baseline,
                value_change=change,
                description=f"Hematocrit at {latest}% — above 54% threshold associated with thrombotic risk",
                confidence=0.95,
            ))
        elif latest >= 51 and direction == "rising":
            signals.append(Signal(
                metric="Hematocrit", trend_direction=direction,
                value_current=latest, value_baseline=baseline,
                value_change=change,
                description=f"Hematocrit at {latest}% and rising — approaching concerning range",
                confidence=0.9,
            ))
        elif direction == "rising" and change and change >= 3:
            signals.append(Signal(
                metric="Hematocrit", trend_direction=direction,
                value_current=latest, value_baseline=baseline,
                value_change=change,
                description=f"Hematocrit rose {change:.1f} points ({baseline}% → {latest}%)",
                confidence=0.85,
            ))

    # --- Hemoglobin ---
    hgb_series = get_metric_series(conn, "718-7", user_id)  # Hemoglobin
    if hgb_series:
        direction, change = compute_trend(hgb_series)
        latest = hgb_series[-1][1]
        if latest > 17.7 or (direction == "rising" and change and change >= 1.0):
            signals.append(Signal(
                metric="Hemoglobin", trend_direction=direction,
                value_current=latest, value_change=change,
                description=f"Hemoglobin at {latest} g/dL — {'elevated' if latest > 17.7 else 'rising'} (correlates with hematocrit)",
            ))

    # --- Blood Pressure (from wearables) ---
    sys_series = get_wearable_series(conn, "bp_systolic", user_id)
    dia_series = get_wearable_series(conn, "bp_diastolic", user_id)
    if sys_series:
        direction, change = compute_trend(sys_series)
        latest_sys = sys_series[-1][1]
        if latest_sys >= 140 or direction == "rising":
            baseline_sys = sys_series[0][1] if len(sys_series) > 1 else None
            signals.append(Signal(
                metric="Blood Pressure (Systolic)", trend_direction=direction,
                value_current=latest_sys, value_baseline=baseline_sys,
                value_change=change,
                description=f"Systolic BP at {latest_sys:.0f} mmHg — {'stage 2 hypertension range' if latest_sys >= 140 else 'trending up'}",
            ))

    # --- Resting Heart Rate ---
    rhr_series = get_wearable_series(conn, "resting_hr", user_id)
    if rhr_series:
        direction, change = compute_trend(rhr_series)
        latest = rhr_series[-1][1]
        baseline = rhr_series[0][1] if len(rhr_series) > 1 else None
        if direction == "rising" and change and change >= 3:
            signals.append(Signal(
                metric="Resting Heart Rate", trend_direction=direction,
                value_current=latest, value_baseline=baseline,
                value_change=change,
                description=f"Resting HR rose from {baseline:.0f} to {latest:.0f} bpm over observation window",
            ))

    # --- HRV ---
    hrv_series = get_wearable_series(conn, "hrv_sdnn", user_id)
    if hrv_series:
        direction, change = compute_trend(hrv_series)
        latest = hrv_series[-1][1]
        baseline = hrv_series[0][1] if len(hrv_series) > 1 else None
        if direction == "falling" and change and abs(change) >= 5:
            signals.append(Signal(
                metric="HRV (SDNN)", trend_direction=direction,
                value_current=latest, value_baseline=baseline,
                value_change=change,
                description=f"HRV declined from {baseline:.0f}ms to {latest:.0f}ms — reduced autonomic recovery",
            ))

    # --- Lipids ---
    hdl_series = get_metric_series(conn, "2085-9", user_id)  # HDL
    ldl_series = get_metric_series(conn, "2089-1", user_id)  # LDL
    trig_series = get_metric_series(conn, "2571-8", user_id)  # Triglycerides

    if hdl_series:
        direction, change = compute_trend(hdl_series)
        latest = hdl_series[-1][1]
        if latest < 30 or (direction == "falling" and change and abs(change) >= 10):
            signals.append(Signal(
                metric="HDL Cholesterol", trend_direction=direction,
                value_current=latest, value_change=change,
                description=f"HDL at {latest:.0f} mg/dL — {'critically suppressed' if latest < 30 else 'declining significantly'}",
            ))

    if ldl_series:
        direction, change = compute_trend(ldl_series)
        latest = ldl_series[-1][1]
        if latest > 160 or (direction == "rising" and change and change >= 30):
            signals.append(Signal(
                metric="LDL Cholesterol", trend_direction=direction,
                value_current=latest, value_change=change,
                description=f"LDL at {latest:.0f} mg/dL — {'elevated' if latest > 160 else 'rising significantly'}",
            ))

    if not signals:
        return None

    # Determine severity based on number and type of signals
    severity = Severity.INFO
    if any(s.metric == "Hematocrit" and s.value_current and s.value_current >= 54 for s in signals):
        severity = Severity.CONCERNING
    elif len(signals) >= 3:
        severity = Severity.CONCERNING
    elif len(signals) >= 2:
        severity = Severity.NOTABLE

    # Tag AAS compounds specifically
    aas_context = [d for d in drug_ctx if d.compound_class in ("AAS", "AI")]

    headline = f"{len(signals)} cardiovascular signal(s) detected"
    if severity == Severity.CONCERNING:
        headline += " — multiple markers warrant review"

    return Finding(
        theme="cardiovascular",
        detector_id="cv_stress",
        severity=severity,
        headline=headline,
        signals=signals,
        drug_context=drug_ctx,
        confidence=0.85,
        recommendations=["Discuss with clinician if hematocrit >54% or BP consistently >140/90"],
    )


# =============================================================================
# THEME 2: HEPATIC LOAD
# Liver strain, primarily from 17α-alkylated orals. Time-locked to oral starts.
# =============================================================================

def detect_hepatic_load(
    conn: sqlite3.Connection,
    user_id: str,
    as_of: str,
) -> Finding | None:
    signals: list[Signal] = []
    drug_ctx = get_active_compounds(conn, as_of, user_id)

    # Identify active 17aa orals
    oral_17aa = [d for d in drug_ctx if d.compound_class == "AAS"
                 and _is_17aa(conn, d.compound_id)]
    hepatoprotectants = [d for d in drug_ctx if d.compound_class == "hepatoprotectant"]

    alt_series = get_metric_series(conn, "1742-6", user_id)  # ALT
    ast_series = get_metric_series(conn, "1920-8", user_id)  # AST
    ggt_series = get_metric_series(conn, "2324-2", user_id)  # GGT
    bili_series = get_metric_series(conn, "1975-2", user_id)  # Total Bilirubin
    alp_series = get_metric_series(conn, "6768-6", user_id)  # Alk Phos

    # ALT/AST pattern
    for name, loinc, series, upper_ref in [("ALT", "1742-6", alt_series, 44), ("AST", "1920-8", ast_series, 40)]:
        if series:
            direction, change = compute_trend(series)
            latest = series[-1][1]
            if latest > upper_ref * 3:
                signals.append(Signal(
                    metric=name, trend_direction=direction,
                    value_current=latest, value_change=change,
                    description=f"{name} at {latest:.0f} U/L — >3x upper limit ({upper_ref})",
                    confidence=0.95,
                ))
            elif latest > upper_ref:
                signals.append(Signal(
                    metric=name, trend_direction=direction,
                    value_current=latest, value_change=change,
                    description=f"{name} at {latest:.0f} U/L — above reference ({upper_ref}){', rising' if direction == 'rising' else ''}",
                    confidence=0.9,
                ))
            elif direction == "rising" and change and change > 10:
                signals.append(Signal(
                    metric=name, trend_direction=direction,
                    value_current=latest, value_change=change,
                    description=f"{name} rising ({change:.0f} U/L increase) though still in range",
                ))

    # Cholestatic pattern: GGT + Alk Phos + Bilirubin all elevated
    cholestatic_signals = 0
    if ggt_series and ggt_series[-1][1] > 65:
        cholestatic_signals += 1
    if alp_series and alp_series[-1][1] > 121:
        cholestatic_signals += 1
    if bili_series and bili_series[-1][1] > 1.2:
        cholestatic_signals += 1

    if cholestatic_signals >= 2:
        signals.append(Signal(
            metric="Cholestatic Pattern",
            description=f"Multiple cholestatic markers elevated (GGT/ALP/bilirubin) — {cholestatic_signals}/3 above reference",
            confidence=0.85,
        ))

    if not signals:
        return None

    severity = Severity.INFO
    if any("3x" in s.description for s in signals) or cholestatic_signals >= 2:
        severity = Severity.CONCERNING
    elif len(signals) >= 2:
        severity = Severity.NOTABLE

    headline = f"Hepatic stress — {len(signals)} liver marker(s) flagged"
    if oral_17aa:
        names = ", ".join(d.compound_name for d in oral_17aa)
        headline += f" (active 17aa oral: {names})"

    return Finding(
        theme="hepatic",
        detector_id="hepatic_load",
        severity=severity,
        headline=headline,
        signals=signals,
        drug_context=drug_ctx,
        recommendations=["ALT/AST >3x ULN on oral AAS: consider discontinuation and recheck in 2-4 weeks"],
    )


# =============================================================================
# THEME 3: HORMONAL BALANCE
# E2 management, prolactin, SHBG, T:E2 ratio. AI and SERM effects.
# =============================================================================

def detect_hormonal_balance(
    conn: sqlite3.Connection,
    user_id: str,
    as_of: str,
) -> Finding | None:
    signals: list[Signal] = []
    drug_ctx = get_active_compounds(conn, as_of, user_id)

    # E2
    e2_series = get_metric_series(conn, "2243-4", user_id)  # Estradiol sensitive
    if not e2_series:
        e2_series = get_metric_series(conn, "13969-1", user_id)  # Estradiol standard

    test_series = get_metric_series(conn, "2986-8", user_id)  # Total T

    # E2 absolute — crash or spike
    if e2_series:
        latest_e2 = e2_series[-1][1]
        direction, change = compute_trend(e2_series)
        if latest_e2 < 10:
            signals.append(Signal(
                metric="Estradiol", trend_direction=direction,
                value_current=latest_e2, value_change=change,
                description=f"E2 at {latest_e2:.0f} pg/mL — critically low. Joint pain, low libido, cognitive blunting expected.",
                confidence=0.95,
            ))
        elif latest_e2 < 15 and direction == "falling":
            signals.append(Signal(
                metric="Estradiol", trend_direction=direction,
                value_current=latest_e2, value_change=change,
                description=f"E2 at {latest_e2:.0f} pg/mL and falling — approaching crash territory",
            ))
        elif latest_e2 > 80:
            signals.append(Signal(
                metric="Estradiol", trend_direction=direction,
                value_current=latest_e2, value_change=change,
                description=f"E2 at {latest_e2:.0f} pg/mL — elevated. Water retention, mood, gyno risk.",
            ))

    # T:E2 ratio
    if test_series and e2_series:
        latest_t = test_series[-1][1]
        latest_e2 = e2_series[-1][1]
        if latest_e2 > 0:
            ratio = latest_t / latest_e2
            if ratio > 40:
                signals.append(Signal(
                    metric="T:E2 Ratio", value_current=ratio,
                    description=f"T:E2 ratio at {ratio:.0f}:1 — high ratio suggests E2 may be over-suppressed",
                ))
            elif ratio < 10:
                signals.append(Signal(
                    metric="T:E2 Ratio", value_current=ratio,
                    description=f"T:E2 ratio at {ratio:.0f}:1 — low ratio suggests relative E2 excess",
                ))

    # Prolactin (relevant on tren/nand)
    prl_series = get_metric_series(conn, "2842-3", user_id)
    if prl_series:
        latest = prl_series[-1][1]
        direction, _ = compute_trend(prl_series)
        if latest > 25:
            nors = [d for d in drug_ctx if d.compound_id in
                    ("tren_a", "tren_e", "nand_deca", "nand_npp")]
            desc = f"Prolactin at {latest:.1f} ng/mL — elevated"
            if nors:
                desc += f" (active 19-nor: {', '.join(d.compound_name for d in nors)})"
            signals.append(Signal(
                metric="Prolactin", trend_direction=direction,
                value_current=latest,
                description=desc,
            ))

    # SHBG — orals crush it
    shbg_series = get_metric_series(conn, "13967-5", user_id)
    if shbg_series:
        latest = shbg_series[-1][1]
        direction, change = compute_trend(shbg_series)
        if latest < 10:
            signals.append(Signal(
                metric="SHBG", trend_direction=direction,
                value_current=latest, value_change=change,
                description=f"SHBG at {latest:.1f} nmol/L — very suppressed",
            ))

    if not signals:
        return None

    severity = Severity.INFO
    if any("critically low" in s.description for s in signals):
        severity = Severity.CONCERNING
    elif len(signals) >= 2:
        severity = Severity.NOTABLE

    return Finding(
        theme="hormonal",
        detector_id="hormonal_balance",
        severity=severity,
        headline=f"Hormonal balance — {len(signals)} signal(s)",
        signals=signals,
        drug_context=drug_ctx,
    )


# =============================================================================
# THEME 4: METABOLIC HEALTH
# Glucose, insulin, A1c, weight trajectory. GH/peptide/GLP-1 effects.
# =============================================================================

def detect_metabolic_health(
    conn: sqlite3.Connection,
    user_id: str,
    as_of: str,
) -> Finding | None:
    signals: list[Signal] = []
    drug_ctx = get_active_compounds(conn, as_of, user_id)

    # Fasting glucose
    glu_series = get_metric_series(conn, "2345-7", user_id)
    if glu_series:
        latest = glu_series[-1][1]
        direction, change = compute_trend(glu_series)
        if latest > 125:
            signals.append(Signal(
                metric="Fasting Glucose", value_current=latest,
                trend_direction=direction, value_change=change,
                description=f"Fasting glucose at {latest:.0f} mg/dL — diabetic range",
                confidence=0.95,
            ))
        elif latest > 99:
            signals.append(Signal(
                metric="Fasting Glucose", value_current=latest,
                trend_direction=direction, value_change=change,
                description=f"Fasting glucose at {latest:.0f} mg/dL — pre-diabetic range",
            ))

    # HbA1c
    a1c_series = get_metric_series(conn, "4548-4", user_id)
    if a1c_series:
        latest = a1c_series[-1][1]
        direction, change = compute_trend(a1c_series)
        if latest > 6.4:
            signals.append(Signal(
                metric="HbA1c", value_current=latest,
                description=f"HbA1c at {latest:.1f}% — diabetic range",
                confidence=0.95,
            ))
        elif latest > 5.6:
            signals.append(Signal(
                metric="HbA1c", value_current=latest,
                description=f"HbA1c at {latest:.1f}% — pre-diabetic range",
            ))

    # Fasting insulin
    ins_series = get_metric_series(conn, "14749-6", user_id)
    if ins_series:
        latest = ins_series[-1][1]
        if latest > 15:
            signals.append(Signal(
                metric="Fasting Insulin", value_current=latest,
                description=f"Fasting insulin at {latest:.1f} uIU/mL — insulin resistance signal",
            ))

    # Weight trajectory (from wearables)
    weight_series = get_wearable_series(conn, "weight", user_id)
    if weight_series and len(weight_series) >= 7:
        direction, change = compute_trend(weight_series)
        latest = weight_series[-1][1]
        baseline = weight_series[0][1]
        total_change = latest - baseline
        if abs(total_change) > 3:  # >3kg change
            signals.append(Signal(
                metric="Weight", trend_direction=direction,
                value_current=latest, value_baseline=baseline,
                value_change=total_change,
                description=f"Weight {'gained' if total_change > 0 else 'lost'} {abs(total_change):.1f}kg ({baseline:.1f} → {latest:.1f}kg)",
            ))

    if not signals:
        return None

    # Flag GH/peptide/insulin context
    gh_compounds = [d for d in drug_ctx if d.compound_class in
                    ("peptide_GH", "insulin", "GLP1_RA", "GLP1_GIP_RA", "biguanide")]

    severity = Severity.INFO
    if any("diabetic range" in s.description and "pre" not in s.description for s in signals):
        severity = Severity.CONCERNING
    elif len(signals) >= 2:
        severity = Severity.NOTABLE

    return Finding(
        theme="metabolic",
        detector_id="metabolic_health",
        severity=severity,
        headline=f"Metabolic health — {len(signals)} signal(s)",
        signals=signals,
        drug_context=drug_ctx,
    )


# =============================================================================
# THEME 5: RENAL FUNCTION
# Creatinine is confounded by muscle mass. Cystatin C is the gold standard.
# =============================================================================

def detect_renal_function(
    conn: sqlite3.Connection,
    user_id: str,
    as_of: str,
) -> Finding | None:
    signals: list[Signal] = []
    drug_ctx = get_active_compounds(conn, as_of, user_id)

    creat_series = get_metric_series(conn, "38483-4", user_id)  # Creatinine
    egfr_series = get_metric_series(conn, "33914-3", user_id)  # eGFR
    bun_series = get_metric_series(conn, "3094-0", user_id)  # BUN
    cystc_series = get_metric_series(conn, "76485-2", user_id)  # Cystatin C

    if creat_series:
        latest = creat_series[-1][1]
        direction, change = compute_trend(creat_series)
        # Note: elevated creatinine in muscular users is expected
        if latest > 1.5:
            signals.append(Signal(
                metric="Creatinine", value_current=latest,
                trend_direction=direction, value_change=change,
                description=f"Creatinine at {latest:.2f} mg/dL — elevated (note: muscle mass confounds this marker)",
            ))
        elif direction == "rising" and change and change > 0.2:
            signals.append(Signal(
                metric="Creatinine", value_current=latest,
                trend_direction=direction, value_change=change,
                description=f"Creatinine rising (+{change:.2f}) — monitor; consider cystatin C for muscle-independent assessment",
            ))

    if egfr_series:
        latest = egfr_series[-1][1]
        if latest < 60:
            signals.append(Signal(
                metric="eGFR", value_current=latest,
                description=f"eGFR at {latest:.0f} — below 60 suggests impaired kidney function",
                confidence=0.9,
            ))

    if cystc_series:
        latest = cystc_series[-1][1]
        direction, change = compute_trend(cystc_series)
        if latest > 1.0:
            signals.append(Signal(
                metric="Cystatin C", value_current=latest,
                trend_direction=direction,
                description=f"Cystatin C at {latest:.2f} mg/L — elevated (muscle-mass independent renal marker)",
                confidence=0.95,
            ))

    if not signals:
        return None

    severity = Severity.INFO
    if any(s.metric == "eGFR" for s in signals) or any(s.metric == "Cystatin C" for s in signals):
        severity = Severity.NOTABLE

    return Finding(
        theme="renal",
        detector_id="renal_function",
        severity=severity,
        headline=f"Renal function — {len(signals)} signal(s)",
        signals=signals,
        drug_context=drug_ctx,
        recommendations=["If creatinine elevated: request cystatin C for muscle-independent kidney assessment"],
    )


# =============================================================================
# THEME 6: HEMATOLOGICAL
# Full CBC picture. RBC, WBC, platelets, differential.
# =============================================================================

def detect_hematological(
    conn: sqlite3.Connection,
    user_id: str,
    as_of: str,
) -> Finding | None:
    signals: list[Signal] = []
    drug_ctx = get_active_compounds(conn, as_of, user_id)

    rbc_series = get_metric_series(conn, "789-8", user_id)  # RBC
    wbc_series = get_metric_series(conn, "6690-2", user_id)  # WBC
    plt_series = get_metric_series(conn, "777-3", user_id)  # Platelets

    if rbc_series:
        latest = rbc_series[-1][1]
        direction, _ = compute_trend(rbc_series)
        if latest > 6.0:
            signals.append(Signal(
                metric="RBC", value_current=latest, trend_direction=direction,
                description=f"RBC at {latest:.2f} — polycythemia range (correlates with androgen-driven erythropoiesis)",
            ))

    if wbc_series:
        latest = wbc_series[-1][1]
        if latest < 3.0:
            signals.append(Signal(
                metric="WBC", value_current=latest,
                description=f"WBC at {latest:.1f} — low white count",
            ))
        elif latest > 12:
            signals.append(Signal(
                metric="WBC", value_current=latest,
                description=f"WBC at {latest:.1f} — elevated (infection, stress, or steroid effect)",
            ))

    if plt_series:
        latest = plt_series[-1][1]
        if latest < 100:
            signals.append(Signal(
                metric="Platelets", value_current=latest,
                description=f"Platelets at {latest:.0f} — thrombocytopenia",
            ))

    if not signals:
        return None

    return Finding(
        theme="hematological",
        detector_id="hematological",
        severity=Severity.NOTABLE if len(signals) >= 2 else Severity.INFO,
        headline=f"Hematological — {len(signals)} signal(s)",
        signals=signals,
        drug_context=drug_ctx,
    )


# =============================================================================
# THEME 7: INFLAMMATION & VASCULAR RISK
# Long-term risk markers: hs-CRP, homocysteine, ApoB, Lp(a).
# =============================================================================

def detect_inflammation_vascular(
    conn: sqlite3.Connection,
    user_id: str,
    as_of: str,
) -> Finding | None:
    signals: list[Signal] = []
    drug_ctx = get_active_compounds(conn, as_of, user_id)

    crp_series = get_metric_series(conn, "30522-7", user_id)  # hs-CRP
    hcy_series = get_metric_series(conn, "30392-5", user_id)  # Homocysteine
    apob_series = get_metric_series(conn, "49132-4", user_id)  # ApoB
    lpa_series = get_metric_series(conn, "43394-6", user_id)  # Lp(a)

    if crp_series:
        latest = crp_series[-1][1]
        direction, _ = compute_trend(crp_series)
        if latest > 3.0:
            signals.append(Signal(
                metric="hs-CRP", value_current=latest, trend_direction=direction,
                description=f"hs-CRP at {latest:.1f} mg/L — elevated systemic inflammation",
            ))

    if hcy_series:
        latest = hcy_series[-1][1]
        if latest > 15:
            signals.append(Signal(
                metric="Homocysteine", value_current=latest,
                description=f"Homocysteine at {latest:.1f} umol/L — elevated cardiovascular risk marker",
            ))

    if apob_series:
        latest = apob_series[-1][1]
        direction, _ = compute_trend(apob_series)
        if latest > 130:
            signals.append(Signal(
                metric="ApoB", value_current=latest, trend_direction=direction,
                description=f"ApoB at {latest:.0f} mg/dL — elevated atherogenic particle count",
            ))

    if lpa_series:
        latest = lpa_series[-1][1]
        if latest > 125:  # nmol/L
            signals.append(Signal(
                metric="Lp(a)", value_current=latest,
                description=f"Lp(a) at {latest:.0f} nmol/L — elevated genetic risk marker (not modifiable by lifestyle)",
            ))

    if not signals:
        return None

    return Finding(
        theme="inflammation_vascular",
        detector_id="inflammation_vascular",
        severity=Severity.NOTABLE if len(signals) >= 2 else Severity.INFO,
        headline=f"Inflammation & vascular risk — {len(signals)} marker(s) flagged",
        signals=signals,
        drug_context=drug_ctx,
    )


# =============================================================================
# THEME 8: RECOVERY & HPTA
# Post-cycle: LH, FSH, total T trajectory. PCT effectiveness.
# =============================================================================

def detect_recovery_hpta(
    conn: sqlite3.Connection,
    user_id: str,
    as_of: str,
) -> Finding | None:
    signals: list[Signal] = []
    drug_ctx = get_active_compounds(conn, as_of, user_id)

    lh_series = get_metric_series(conn, "10501-5", user_id)  # LH
    fsh_series = get_metric_series(conn, "15067-2", user_id)  # FSH
    test_series = get_metric_series(conn, "2986-8", user_id)  # Total T

    # Only relevant if NOT actively on exogenous androgens (or recently stopped)
    active_aas = [d for d in drug_ctx if d.compound_class == "AAS"]

    if lh_series:
        latest = lh_series[-1][1]
        direction, _ = compute_trend(lh_series)
        if latest < 1.0 and not active_aas:
            signals.append(Signal(
                metric="LH", value_current=latest, trend_direction=direction,
                description=f"LH at {latest:.1f} mIU/mL — suppressed. HPTA not recovered.",
            ))
        elif latest < 1.0 and active_aas:
            signals.append(Signal(
                metric="LH", value_current=latest, trend_direction=direction,
                description=f"LH at {latest:.1f} mIU/mL — suppressed (expected on exogenous androgens)",
                confidence=0.5,  # low priority when on cycle
            ))

    if fsh_series:
        latest = fsh_series[-1][1]
        if latest < 1.0 and not active_aas:
            signals.append(Signal(
                metric="FSH", value_current=latest,
                description=f"FSH at {latest:.1f} mIU/mL — suppressed. Spermatogenesis impaired.",
            ))

    # If total T is low AND off cycle — recovery problem
    if test_series and not active_aas:
        latest = test_series[-1][1]
        if latest < 264:
            signals.append(Signal(
                metric="Total Testosterone", value_current=latest,
                description=f"Total T at {latest:.0f} ng/dL — below reference. HPTA recovery incomplete.",
            ))

    if not signals:
        return None

    # Check for PCT compounds
    pct_compounds = [d for d in drug_ctx if d.compound_class in ("SERM", "gonadotropin")]

    severity = Severity.INFO
    if any("not recovered" in s.description for s in signals):
        severity = Severity.NOTABLE

    return Finding(
        theme="recovery",
        detector_id="recovery_hpta",
        severity=severity,
        headline=f"HPTA recovery — {len(signals)} signal(s)",
        signals=signals,
        drug_context=drug_ctx,
    )


# =============================================================================
# HELPERS
# =============================================================================

def _is_17aa(conn: sqlite3.Connection, compound_id: str) -> bool:
    """Check if a compound is 17-alpha-alkylated (hepatotoxic oral)."""
    row = conn.execute(
        "SELECT is_17aa FROM compound_definition WHERE id = ?",
        (compound_id,),
    ).fetchone()
    return bool(row and row["is_17aa"])
