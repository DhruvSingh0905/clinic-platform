"""Compound database — reference data for cycle log.

v1 scope per wiki/domain/compound-database: AAS injectables, AAS orals,
AIs, SERMs, CV ancillaries, recovery, peptides, background meds.

Sources: Llewellyn's Anabolics, PubMed, DrugBank (public), FDA labels.
Half-lives are ester-dependent for injectables.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Compound:
    id: str                          # unique key, e.g. "test_cyp"
    canonical_name: str
    aliases: list[str] = field(default_factory=list)
    compound_class: str = ""         # AAS, AI, SERM, 5ARI, PDE5, ARB, peptide, statin, etc.
    ester: str | None = None
    parent: str | None = None        # parent compound for ester variants
    half_life_hours: float | None = None
    half_life_source: str = ""
    route: str = ""                  # IM, subQ, oral, transdermal
    is_17aa: bool = False            # hepatotoxic oral flag
    dose_range_trt: str = ""         # e.g. "100-200mg/wk"
    dose_range_supra: str = ""       # e.g. "300-700mg/wk"
    monitoring_markers: list[str] = field(default_factory=list)  # LOINC codes to watch
    mechanism_summary: str = ""
    notes: str = ""


# === V1 COMPOUND DATABASE ===
# Seeded from Llewellyn's Anabolics + PubMed half-life data

COMPOUNDS: dict[str, Compound] = {}


def _add(c: Compound) -> None:
    COMPOUNDS[c.id] = c


# --- AAS INJECTABLES ---

_add(Compound(
    id="test_cyp", canonical_name="Testosterone Cypionate",
    aliases=["Test C", "Test Cyp", "Cyp"],
    compound_class="AAS", ester="cypionate", parent="testosterone",
    half_life_hours=192,  # ~8 days, Llewellyn
    half_life_source="Llewellyn's Anabolics",
    route="IM",
    dose_range_trt="100-200mg/wk", dose_range_supra="300-700mg/wk",
    monitoring_markers=["2986-8", "2243-4", "4544-3", "1742-6"],  # total T, E2, HCT, ALT
    mechanism_summary="Exogenous testosterone, cypionate ester for sustained release.",
))

_add(Compound(
    id="test_e", canonical_name="Testosterone Enanthate",
    aliases=["Test E", "Test Enan"],
    compound_class="AAS", ester="enanthate", parent="testosterone",
    half_life_hours=168,  # ~7 days
    half_life_source="Llewellyn's Anabolics",
    route="IM",
    dose_range_trt="100-200mg/wk", dose_range_supra="300-700mg/wk",
    monitoring_markers=["2986-8", "2243-4", "4544-3", "1742-6"],
))

_add(Compound(
    id="test_prop", canonical_name="Testosterone Propionate",
    aliases=["Test P", "Test Prop"],
    compound_class="AAS", ester="propionate", parent="testosterone",
    half_life_hours=48,  # ~2 days
    half_life_source="Llewellyn's Anabolics",
    route="IM",
    dose_range_supra="50-100mg EOD",
    monitoring_markers=["2986-8", "2243-4", "4544-3"],
))

_add(Compound(
    id="test_u", canonical_name="Testosterone Undecanoate",
    aliases=["Test U", "Nebido", "Aveed"],
    compound_class="AAS", ester="undecanoate", parent="testosterone",
    half_life_hours=504,  # ~21 days
    half_life_source="FDA label (Aveed)",
    route="IM",
    dose_range_trt="750mg q10wk",
    monitoring_markers=["2986-8", "2243-4", "4544-3"],
))

_add(Compound(
    id="nand_deca", canonical_name="Nandrolone Decanoate",
    aliases=["Deca", "Deca Durabolin", "Nand Deca"],
    compound_class="AAS", ester="decanoate", parent="nandrolone",
    half_life_hours=360,  # ~15 days
    half_life_source="Llewellyn's Anabolics",
    route="IM",
    dose_range_supra="200-600mg/wk",
    monitoring_markers=["2986-8", "4544-3", "2842-3"],  # prolactin relevant
))

_add(Compound(
    id="nand_npp", canonical_name="Nandrolone Phenylpropionate",
    aliases=["NPP", "Nand PP"],
    compound_class="AAS", ester="phenylpropionate", parent="nandrolone",
    half_life_hours=72,  # ~3 days
    half_life_source="Llewellyn's Anabolics",
    route="IM",
    dose_range_supra="100-150mg EOD",
    monitoring_markers=["2986-8", "4544-3", "2842-3"],
))

_add(Compound(
    id="eq", canonical_name="Boldenone Undecylenate",
    aliases=["EQ", "Equipoise", "Bold"],
    compound_class="AAS", ester="undecylenate", parent="boldenone",
    half_life_hours=336,  # ~14 days
    half_life_source="Llewellyn's Anabolics",
    route="IM",
    dose_range_supra="300-800mg/wk",
    monitoring_markers=["2986-8", "2243-4", "4544-3", "789-8"],  # E2 crash risk, RBC
    notes="Metabolite acts as AI; E2 crash risk at high test:EQ ratios.",
))

_add(Compound(
    id="tren_a", canonical_name="Trenbolone Acetate",
    aliases=["Tren A", "Tren Ace"],
    compound_class="AAS", ester="acetate", parent="trenbolone",
    half_life_hours=48,
    half_life_source="Llewellyn's Anabolics",
    route="IM",
    dose_range_supra="150-400mg/wk",
    monitoring_markers=["2986-8", "4544-3", "2842-3", "2085-9", "2089-1"],  # prolactin, lipids
    notes="Highly suppressive. CV risk elevated. Insomnia, sweating common.",
))

_add(Compound(
    id="tren_e", canonical_name="Trenbolone Enanthate",
    aliases=["Tren E"],
    compound_class="AAS", ester="enanthate", parent="trenbolone",
    half_life_hours=168,
    half_life_source="Estimated from ester",
    route="IM",
    dose_range_supra="200-400mg/wk",
    monitoring_markers=["2986-8", "4544-3", "2842-3", "2085-9", "2089-1"],
))

_add(Compound(
    id="masteron_p", canonical_name="Drostanolone Propionate",
    aliases=["Masteron", "Mast P", "Drostanolone"],
    compound_class="AAS", ester="propionate", parent="drostanolone",
    half_life_hours=60,
    half_life_source="Llewellyn's Anabolics",
    route="IM",
    dose_range_supra="300-500mg/wk",
    monitoring_markers=["2986-8", "2243-4", "2085-9"],
    notes="Mild AI properties via DHT derivative.",
))

_add(Compound(
    id="primo_e", canonical_name="Methenolone Enanthate",
    aliases=["Primobolan", "Primo", "Primo E"],
    compound_class="AAS", ester="enanthate", parent="methenolone",
    half_life_hours=240,  # ~10 days
    half_life_source="Llewellyn's Anabolics",
    route="IM",
    dose_range_supra="400-800mg/wk",
    monitoring_markers=["2986-8", "2085-9"],
    notes="Mild, low side-effect profile. Popular in longer cycles.",
))

# --- AAS ORALS ---

_add(Compound(
    id="anavar", canonical_name="Oxandrolone",
    aliases=["Anavar", "Var"],
    compound_class="AAS", route="oral", is_17aa=True,
    half_life_hours=9,
    half_life_source="FDA label",
    dose_range_supra="20-80mg/day",
    monitoring_markers=["1742-6", "1920-8", "2085-9", "2089-1"],  # ALT, AST, lipids
    notes="Mild oral. Still impacts lipids and SHBG significantly.",
))

_add(Compound(
    id="winstrol", canonical_name="Stanozolol",
    aliases=["Winstrol", "Winny"],
    compound_class="AAS", route="oral", is_17aa=True,
    half_life_hours=9,
    half_life_source="Llewellyn's Anabolics",
    dose_range_supra="25-75mg/day",
    monitoring_markers=["1742-6", "1920-8", "2085-9", "2089-1", "13967-5"],  # SHBG
    notes="Harsh on lipids and joints. Crushes SHBG.",
))

_add(Compound(
    id="dbol", canonical_name="Methandrostenolone",
    aliases=["Dianabol", "Dbol"],
    compound_class="AAS", route="oral", is_17aa=True,
    half_life_hours=6,
    half_life_source="Llewellyn's Anabolics",
    dose_range_supra="20-50mg/day",
    monitoring_markers=["1742-6", "1920-8", "2243-4", "2085-9"],  # aromatizes heavily
    notes="Strong aromatizer. Water retention. E2 management critical.",
))

_add(Compound(
    id="anadrol", canonical_name="Oxymetholone",
    aliases=["Anadrol", "Adrol", "A-bombs"],
    compound_class="AAS", route="oral", is_17aa=True,
    half_life_hours=16,
    half_life_source="FDA label",
    dose_range_supra="25-100mg/day",
    monitoring_markers=["1742-6", "1920-8", "4544-3", "2085-9"],
    notes="Very hepatotoxic at high doses. Raises hematocrit significantly.",
))

_add(Compound(
    id="tbol", canonical_name="4-Chlorodehydromethyltestosterone",
    aliases=["Turinabol", "Tbol"],
    compound_class="AAS", route="oral", is_17aa=True,
    half_life_hours=16,
    half_life_source="Estimated",
    dose_range_supra="30-60mg/day",
    monitoring_markers=["1742-6", "1920-8", "2085-9"],
))

# --- AROMATASE INHIBITORS ---

_add(Compound(
    id="anastrozole", canonical_name="Anastrozole",
    aliases=["Arimidex", "Adex"],
    compound_class="AI", route="oral",
    half_life_hours=48,
    half_life_source="FDA label",
    dose_range_trt="0.25-0.5mg 2x/wk",
    monitoring_markers=["2243-4", "13967-5"],  # E2, SHBG
    notes="Non-steroidal. Reversible. E2 crash risk with overuse.",
))

_add(Compound(
    id="exemestane", canonical_name="Exemestane",
    aliases=["Aromasin"],
    compound_class="AI", route="oral",
    half_life_hours=24,
    half_life_source="FDA label",
    dose_range_trt="12.5mg 2x/wk",
    monitoring_markers=["2243-4", "13967-5"],
    notes="Steroidal (suicidal) AI. Less E2 rebound. Mildly androgenic.",
))

_add(Compound(
    id="letrozole", canonical_name="Letrozole",
    aliases=["Femara", "Letro"],
    compound_class="AI", route="oral",
    half_life_hours=48,
    half_life_source="FDA label",
    dose_range_trt="0.25mg 2x/wk (gyno emergency: up to 2.5mg/day)",
    monitoring_markers=["2243-4"],
    notes="Most potent AI. High E2 crash risk. Reserve for gyno flares.",
))

# --- SERMs ---

_add(Compound(
    id="tamoxifen", canonical_name="Tamoxifen",
    aliases=["Nolvadex", "Nolva"],
    compound_class="SERM", route="oral",
    half_life_hours=168,  # ~7 days (active metabolite endoxifen longer)
    half_life_source="FDA label",
    monitoring_markers=["10501-5", "15067-2", "2986-8"],  # LH, FSH, total T
    notes="PCT staple. Blocks E2 at breast tissue. IGF-1 suppression.",
))

_add(Compound(
    id="clomiphene", canonical_name="Clomiphene",
    aliases=["Clomid"],
    compound_class="SERM", route="oral",
    half_life_hours=120,
    half_life_source="FDA label",
    monitoring_markers=["10501-5", "15067-2", "2986-8"],
    notes="PCT. Raises LH/FSH. Side effects: visual disturbances, mood.",
))

_add(Compound(
    id="enclomiphene", canonical_name="Enclomiphene",
    aliases=["Enclomid"],
    compound_class="SERM", route="oral",
    half_life_hours=10,
    half_life_source="Phase III data",
    monitoring_markers=["10501-5", "15067-2", "2986-8"],
    notes="Trans-isomer of clomiphene. Fewer side effects. Less studied.",
))

_add(Compound(
    id="raloxifene", canonical_name="Raloxifene",
    aliases=["Evista"],
    compound_class="SERM", route="oral",
    half_life_hours=32,
    half_life_source="FDA label",
    monitoring_markers=["2243-4"],
    notes="Breast-tissue selective. Used for existing gyno reduction.",
))

# --- CV ANCILLARIES ---

_add(Compound(
    id="telmisartan", canonical_name="Telmisartan",
    aliases=["Micardis"],
    compound_class="ARB", route="oral",
    half_life_hours=24,
    half_life_source="FDA label",
    monitoring_markers=["2951-2", "2823-3"],  # Na, K (renal monitoring)
    mechanism_summary="ARB + PPARγ agonist. BP control + insulin sensitivity.",
))

_add(Compound(
    id="lisinopril", canonical_name="Lisinopril",
    aliases=["Zestril", "Prinivil"],
    compound_class="ACEi", route="oral",
    half_life_hours=12,
    half_life_source="FDA label",
    monitoring_markers=["2951-2", "2823-3", "38483-4"],  # Na, K, creatinine
))

_add(Compound(
    id="tadalafil", canonical_name="Tadalafil",
    aliases=["Cialis"],
    compound_class="PDE5", route="oral",
    half_life_hours=17.5,
    half_life_source="FDA label",
    mechanism_summary="PDE5 inhibitor. BP-lowering effect. Vasodilation.",
))

_add(Compound(
    id="atorvastatin", canonical_name="Atorvastatin",
    aliases=["Lipitor"],
    compound_class="statin", route="oral",
    half_life_hours=14,
    half_life_source="FDA label",
    monitoring_markers=["2089-1", "2085-9", "1742-6"],  # LDL, HDL, ALT
))

_add(Compound(
    id="rosuvastatin", canonical_name="Rosuvastatin",
    aliases=["Crestor"],
    compound_class="statin", route="oral",
    half_life_hours=19,
    half_life_source="FDA label",
    monitoring_markers=["2089-1", "2085-9", "1742-6"],
))

_add(Compound(
    id="ezetimibe", canonical_name="Ezetimibe",
    aliases=["Zetia"],
    compound_class="cholesterol_absorption_inhibitor", route="oral",
    half_life_hours=22,
    half_life_source="FDA label",
    monitoring_markers=["2089-1"],
))

_add(Compound(
    id="ivabradine", canonical_name="Ivabradine",
    aliases=["Corlanor"],
    compound_class="HCN_blocker", route="oral",
    half_life_hours=6,
    half_life_source="FDA label",
    mechanism_summary="HCN channel blocker. Lowers resting HR without BP effect.",
    notes="Used off-label for tren/stimulant-induced tachycardia.",
))

_add(Compound(
    id="bisoprolol", canonical_name="Bisoprolol",
    aliases=["Zebeta"],
    compound_class="beta_blocker", route="oral",
    half_life_hours=11,
    half_life_source="FDA label",
))

# --- RECOVERY ---

_add(Compound(
    id="hcg", canonical_name="Human Chorionic Gonadotropin",
    aliases=["HCG", "Pregnyl", "Novarel"],
    compound_class="gonadotropin", route="subQ",
    half_life_hours=33,
    half_life_source="PubMed",
    monitoring_markers=["2986-8", "2243-4", "10501-5"],
    notes="LH analog. Maintains testicular function on cycle. Aromatizes.",
))

_add(Compound(
    id="hmg", canonical_name="Human Menopausal Gonadotropin",
    aliases=["hMG", "Menopur"],
    compound_class="gonadotropin", route="subQ",
    half_life_hours=24,
    half_life_source="Estimated",
    monitoring_markers=["15067-2", "2986-8"],
    notes="Contains FSH + LH activity. Fertility recovery.",
))

# --- PEPTIDES ---

_add(Compound(
    id="hgh", canonical_name="Human Growth Hormone",
    aliases=["HGH", "GH", "Somatropin"],
    compound_class="peptide_GH", route="subQ",
    half_life_hours=3,
    half_life_source="FDA label",
    monitoring_markers=["1990-1", "2345-7", "14749-6"],  # IGF-1, glucose, insulin
    notes="Raises IGF-1. Insulin resistance at higher doses. Fasting glucose monitor.",
))

_add(Compound(
    id="bpc157", canonical_name="BPC-157",
    aliases=["BPC 157", "Body Protection Compound"],
    compound_class="peptide_other", route="subQ",
    half_life_hours=4,
    half_life_source="Estimated (limited human data)",
    notes="Low evidence tier. Animal data only for most claims. Flag accordingly.",
))

_add(Compound(
    id="tb500", canonical_name="Thymosin Beta-4",
    aliases=["TB-500", "TB500"],
    compound_class="peptide_other", route="subQ",
    half_life_hours=6,
    half_life_source="Estimated (limited human data)",
    notes="Low evidence tier.",
))

# --- BACKGROUND MEDS ---

_add(Compound(
    id="finasteride", canonical_name="Finasteride",
    aliases=["Propecia", "Proscar"],
    compound_class="5ARI", route="oral",
    half_life_hours=8,
    half_life_source="FDA label",
    monitoring_markers=["2857-1"],  # PSA
    notes="5-alpha reductase inhibitor. Reduces DHT. PSA halved on therapy.",
))

_add(Compound(
    id="dutasteride", canonical_name="Dutasteride",
    aliases=["Avodart"],
    compound_class="5ARI", route="oral",
    half_life_hours=720,  # ~30 days (extremely long)
    half_life_source="FDA label",
    monitoring_markers=["2857-1"],
))

_add(Compound(
    id="metformin", canonical_name="Metformin",
    aliases=["Glucophage"],
    compound_class="biguanide", route="oral",
    half_life_hours=6.2,
    half_life_source="FDA label",
    monitoring_markers=["2345-7", "4548-4", "2132-9"],  # glucose, A1c, B12 (depletion)
))

_add(Compound(
    id="minoxidil", canonical_name="Minoxidil",
    aliases=["Rogaine"],
    compound_class="vasodilator", route="transdermal",
    half_life_hours=4.2,  # oral; topical has longer local effect
    half_life_source="FDA label",
    notes="Topical for hair. Oral at low dose (2.5-5mg) used off-label for BP.",
))

# --- MISSING ANCILLARIES FROM WIKI V1 ---

_add(Compound(
    id="losartan", canonical_name="Losartan",
    aliases=["Cozaar"],
    compound_class="ARB", route="oral",
    half_life_hours=6,  # active metabolite EXP3174: t½=6-9h
    half_life_source="FDA label",
    monitoring_markers=["2951-2", "2823-3", "38483-4"],
    notes="ARB. Less PPARγ activity than telmisartan.",
))

_add(Compound(
    id="bempedoic_acid", canonical_name="Bempedoic Acid",
    aliases=["Nexletol"],
    compound_class="ACL_inhibitor", route="oral",
    half_life_hours=21,
    half_life_source="FDA label (2020)",
    monitoring_markers=["2089-1", "1742-6"],
    notes="ATP citrate lyase inhibitor. Upstream of statins. Prodrug activated in liver, not muscle — no myalgia.",
))

_add(Compound(
    id="citrus_bergamot", canonical_name="Citrus Bergamot",
    aliases=["Bergamot", "Bergamot Extract"],
    compound_class="supplement", route="oral",
    half_life_hours=8,  # estimated, limited PK data
    half_life_source="Estimated (limited PK data)",
    monitoring_markers=["2089-1", "2085-9"],
    notes="Weaker evidence tier. Some RCTs show lipid benefit. Not FDA-regulated.",
))

# --- GLP-1 ---

_add(Compound(
    id="semaglutide", canonical_name="Semaglutide",
    aliases=["Ozempic", "Wegovy", "Rybelsus"],
    compound_class="GLP1_RA", route="subQ",
    half_life_hours=168,  # ~7 days
    half_life_source="FDA label",
    monitoring_markers=["2345-7", "4548-4", "14749-6"],  # glucose, A1c, insulin
    notes="GLP-1 receptor agonist. Weekly injection. Weight loss + glycemic control.",
))

_add(Compound(
    id="tirzepatide", canonical_name="Tirzepatide",
    aliases=["Mounjaro", "Zepbound"],
    compound_class="GLP1_GIP_RA", route="subQ",
    half_life_hours=120,  # ~5 days
    half_life_source="FDA label",
    monitoring_markers=["2345-7", "4548-4", "14749-6"],
    notes="Dual GIP/GLP-1 agonist. Weekly injection.",
))

# --- RECOVERY (missing) ---

_add(Compound(
    id="kisspeptin", canonical_name="Kisspeptin-10",
    aliases=["Kisspeptin", "KP-10"],
    compound_class="neuropeptide", route="subQ",
    half_life_hours=0.07,  # ~4 min; KP-54 is ~28 min
    half_life_source="PubMed: PMID 21976724 (KP-10 terminal t½ ~4 min; KP-54 is longer)",
    monitoring_markers=["10501-5", "15067-2", "2986-8"],
    notes="Low evidence tier for PED recovery. Stimulates GnRH pulsatility. Research-grade.",
))

# --- PEPTIDES (missing) ---

_add(Compound(
    id="sermorelin", canonical_name="Sermorelin",
    aliases=["GRF(1-29)", "Geref"],
    compound_class="peptide_GH", route="subQ",
    half_life_hours=0.2,  # ~12 min
    half_life_source="PeptideDossier (10-15 min); FDA label",
    monitoring_markers=["1990-1"],
    notes="GHRH analog. Very short-acting, requires daily injection. FDA-approved (discontinued).",
))

_add(Compound(
    id="tesamorelin", canonical_name="Tesamorelin",
    aliases=["Egrifta"],
    compound_class="peptide_GH", route="subQ",
    half_life_hours=0.15,  # ~8-11 min per FDA label
    half_life_source="FDA label (Egrifta): mean elimination t½ 8-11 min",
    monitoring_markers=["1990-1", "2345-7"],
    notes="GHRH analog. FDA-approved for HIV lipodystrophy. Longer-acting than sermorelin.",
))

_add(Compound(
    id="ghrp2", canonical_name="GHRP-2",
    aliases=["GHRP-2", "Pralmorelin"],
    compound_class="peptide_GH", route="subQ",
    half_life_hours=0.5,  # ~25-30 min
    half_life_source="PubMed clinical dosing data; used as diagnostic agent in Japan",
    monitoring_markers=["1990-1"],
    notes="GHRP. Potent GH release. Increases cortisol and prolactin more than ipamorelin.",
))

_add(Compound(
    id="ghrp6", canonical_name="GHRP-6",
    aliases=["GHRP-6"],
    compound_class="peptide_GH", route="subQ",
    half_life_hours=2.5,  # elimination t½; distribution t½ is ~7.6 min
    half_life_source="PubMed: PMID 23099431 (elimination t½ 2.5±1.1h in 9 healthy males)",
    monitoring_markers=["1990-1"],
    notes="GHRP. Strong hunger stimulation (ghrelin mimetic). Bi-exponential clearance.",
))

_add(Compound(
    id="hexarelin", canonical_name="Hexarelin",
    aliases=["Examorelin"],
    compound_class="peptide_GH", route="subQ",
    half_life_hours=0.92,  # ~55 min in humans
    half_life_source="Creative Peptides / clinical data",
    monitoring_markers=["1990-1"],
    notes="GHRP. Most potent GH secretagogue. Rapid desensitization — efficacy drops within 2 weeks of continuous use.",
))

_add(Compound(
    id="cjc1295_dac", canonical_name="CJC-1295 DAC",
    aliases=["CJC-1295", "CJC with DAC", "Modified GRF(1-29)"],
    compound_class="peptide_GH", route="subQ",
    half_life_hours=192,  # ~8 days with DAC
    half_life_source="PubMed: PMID 16352683",
    monitoring_markers=["1990-1"],  # IGF-1
    notes="GHRH analog. Long-acting with Drug Affinity Complex.",
))

_add(Compound(
    id="ipamorelin", canonical_name="Ipamorelin",
    aliases=["Ipam"],
    compound_class="peptide_GH", route="subQ",
    half_life_hours=2,
    half_life_source="PubMed: PMID 9849822",
    monitoring_markers=["1990-1"],
    notes="GHRP. Selective GH secretagogue, minimal cortisol/prolactin release.",
))

_add(Compound(
    id="mk677", canonical_name="Ibutamoren",
    aliases=["MK-677", "MK677", "Nutrobal"],
    compound_class="peptide_GH", route="oral",
    half_life_hours=24,  # supports once-daily dosing
    half_life_source="PubMed: PMID 9467534 (drug elimination, not GH pulse)",
    monitoring_markers=["1990-1", "2345-7", "14749-6"],  # IGF-1, glucose, insulin
    notes="GH secretagogue (oral). Raises fasting glucose and insulin. Monitor closely.",
))

# ==========================================================================
# COMPREHENSIVE ANCILLARY DATABASE
# Everything an enhanced athlete might take alongside AAS that moves data.
# If the system doesn't know about it, the LLM will misattribute changes.
# ==========================================================================

# --- BP MEDS (additional) ---

_add(Compound(
    id="amlodipine", canonical_name="Amlodipine",
    aliases=["Norvasc"],
    compound_class="CCB", route="oral",
    half_life_hours=40,
    half_life_source="FDA label",
    monitoring_markers=["2951-2", "2823-3"],
    mechanism_summary="Calcium channel blocker. Long-acting BP med. Peripheral edema common.",
    notes="Very commonly prescribed alongside AAS use. Ankle swelling can confuse weight tracking.",
))

_add(Compound(
    id="nebivolol", canonical_name="Nebivolol",
    aliases=["Bystolic"],
    compound_class="beta_blocker", route="oral",
    half_life_hours=12,
    half_life_source="FDA label",
    mechanism_summary="Beta-1 selective blocker with nitric oxide potentiation. Lowers HR + BP.",
    notes="Preferred beta blocker in enhanced athletes — less exercise intolerance than non-selective.",
))

_add(Compound(
    id="carvedilol", canonical_name="Carvedilol",
    aliases=["Coreg"],
    compound_class="beta_blocker", route="oral",
    half_life_hours=7,
    half_life_source="FDA label",
    notes="Non-selective beta+alpha blocker. More potent BP reduction but more exercise intolerance.",
))

_add(Compound(
    id="hctz", canonical_name="Hydrochlorothiazide",
    aliases=["HCTZ", "Microzide"],
    compound_class="thiazide_diuretic", route="oral",
    half_life_hours=10,
    half_life_source="FDA label",
    monitoring_markers=["2951-2", "2823-3", "2345-7", "14933-6"],  # Na, K, glucose, uric acid
    notes="Thiazide diuretic. Raises uric acid, can deplete potassium. Common in ARB combos.",
))

# --- LIPID MEDS (additional) ---

_add(Compound(
    id="pravastatin", canonical_name="Pravastatin",
    aliases=["Pravachol"],
    compound_class="statin", route="oral",
    half_life_hours=2,
    half_life_source="FDA label",
    monitoring_markers=["2089-1", "2085-9", "1742-6"],
    notes="Hydrophilic statin. Fewer drug interactions. Less potent than atorva/rosuva.",
))

_add(Compound(
    id="fenofibrate", canonical_name="Fenofibrate",
    aliases=["Tricor", "Fenoglide"],
    compound_class="fibrate", route="oral",
    half_life_hours=20,
    half_life_source="FDA label",
    monitoring_markers=["2571-8", "2085-9", "1742-6"],  # trigs, HDL, ALT
    notes="PPARα agonist. Primarily lowers triglycerides, raises HDL. Monitor liver.",
))

_add(Compound(
    id="icosapent_ethyl", canonical_name="Icosapent Ethyl",
    aliases=["Vascepa", "Prescription Omega-3", "EPA"],
    compound_class="omega3_rx", route="oral",
    half_life_hours=89,
    half_life_source="FDA label (Vascepa)",
    monitoring_markers=["2571-8", "2089-1"],
    notes="Purified EPA. FDA-approved for trigs. Measurable effect on lipid panel.",
))

# --- ANTI-PROLACTIN (critical for tren/nand users) ---

_add(Compound(
    id="cabergoline", canonical_name="Cabergoline",
    aliases=["Caber", "Dostinex"],
    compound_class="dopamine_agonist", route="oral",
    half_life_hours=65,
    half_life_source="FDA label",
    monitoring_markers=["2842-3"],  # prolactin
    notes="Dopamine D2 agonist. Crushes prolactin. Used with tren/nandrolone. Very potent — low dose.",
))

_add(Compound(
    id="pramipexole", canonical_name="Pramipexole",
    aliases=["Prami", "Mirapex"],
    compound_class="dopamine_agonist", route="oral",
    half_life_hours=8,
    half_life_source="FDA label",
    monitoring_markers=["2842-3"],
    notes="D3-preferring dopamine agonist. Lowers prolactin. More side effects than caber (nausea, fatigue).",
))

# --- THYROID (common alongside GH) ---

_add(Compound(
    id="liothyronine", canonical_name="Liothyronine",
    aliases=["T3", "Cytomel"],
    compound_class="thyroid_hormone", route="oral",
    half_life_hours=24,
    half_life_source="FDA label",
    monitoring_markers=["3016-3", "3053-6", "3026-2"],  # TSH, FT3, FT4
    notes="Exogenous T3. Suppresses TSH. Commonly run with GH. Catabolic at high doses.",
))

_add(Compound(
    id="levothyroxine", canonical_name="Levothyroxine",
    aliases=["T4", "Synthroid", "Levoxyl"],
    compound_class="thyroid_hormone", route="oral",
    half_life_hours=168,  # ~7 days
    half_life_source="FDA label",
    monitoring_markers=["3016-3", "3026-2"],
    notes="Exogenous T4. Standard thyroid replacement. Slow to reach steady state.",
))

# --- LIVER SUPPORT (critical for oral AAS users) ---

_add(Compound(
    id="tudca", canonical_name="TUDCA",
    aliases=["Tauroursodeoxycholic Acid", "TUDCA"],
    compound_class="hepatoprotectant", route="oral",
    half_life_hours=4,
    half_life_source="Estimated from bile acid PK",
    monitoring_markers=["1742-6", "1920-8", "1975-2"],  # ALT, AST, bilirubin
    notes="Bile acid. Standard liver support with 17aa orals. Evidence supports hepatoprotective effect.",
))

_add(Compound(
    id="nac", canonical_name="N-Acetyl Cysteine",
    aliases=["NAC"],
    compound_class="hepatoprotectant", route="oral",
    half_life_hours=6.25,
    half_life_source="PubMed: clinical PK data",
    monitoring_markers=["1742-6", "1920-8"],
    notes="Glutathione precursor. Antioxidant. Used for liver support with orals.",
))

_add(Compound(
    id="milk_thistle", canonical_name="Silymarin",
    aliases=["Milk Thistle", "Silymarin"],
    compound_class="hepatoprotectant", route="oral",
    half_life_hours=6,
    half_life_source="PubMed: PMID 20564545",
    monitoring_markers=["1742-6", "1920-8"],
    notes="Weaker evidence than TUDCA/NAC. Very commonly used regardless.",
))

# --- DIURETICS ---

_add(Compound(
    id="furosemide", canonical_name="Furosemide",
    aliases=["Lasix"],
    compound_class="loop_diuretic", route="oral",
    half_life_hours=2,
    half_life_source="FDA label",
    monitoring_markers=["2951-2", "2823-3", "38483-4"],  # Na, K, creatinine
    notes="Loop diuretic. Water/sodium loss. Electrolyte monitoring critical. Used for edema.",
))

_add(Compound(
    id="spironolactone", canonical_name="Spironolactone",
    aliases=["Aldactone", "Spiro"],
    compound_class="K_sparing_diuretic", route="oral",
    half_life_hours=1.4,  # parent; active metabolite canrenone t½=16h
    half_life_source="FDA label (active metabolite canrenone: 16h)",
    monitoring_markers=["2823-3", "2986-8"],  # potassium, testosterone (anti-androgen)
    notes="Anti-androgen properties. Raises potassium. Used for acne/water. Can confuse hormone panels.",
))

# --- INSULIN (used with GH by advanced users) ---

_add(Compound(
    id="insulin_rapid", canonical_name="Insulin (Rapid-Acting)",
    aliases=["Humalog", "Novolog", "Lispro", "Aspart", "Insulin"],
    compound_class="insulin", route="subQ",
    half_life_hours=1,
    half_life_source="FDA label",
    monitoring_markers=["2345-7", "4548-4", "14749-6"],  # glucose, A1c, fasting insulin
    notes="Exogenous insulin. Hypoglycemia risk. Dramatically affects glucose and body composition data.",
))

_add(Compound(
    id="insulin_long", canonical_name="Insulin (Long-Acting)",
    aliases=["Lantus", "Glargine", "Levemir", "Detemir", "Tresiba", "Degludec"],
    compound_class="insulin", route="subQ",
    half_life_hours=24,  # glargine; degludec ~25h
    half_life_source="FDA label (glargine)",
    monitoring_markers=["2345-7", "4548-4", "14749-6"],
    notes="Basal insulin. Steady glucose lowering. Affects fasting glucose readings.",
))

# --- SLEEP / TREN SUPPORT ---

_add(Compound(
    id="trazodone", canonical_name="Trazodone",
    aliases=["Desyrel"],
    compound_class="SARI", route="oral",
    half_life_hours=7,
    half_life_source="FDA label",
    notes="Serotonin antagonist. Used off-label for tren insomnia. Affects sleep architecture data.",
))

# --- HAIR (topical anti-androgens) ---

_add(Compound(
    id="ru58841", canonical_name="RU-58841",
    aliases=["RU58841", "RU"],
    compound_class="topical_antiandrogen", route="transdermal",
    half_life_hours=1,  # topical, local effect
    half_life_source="Estimated (research compound, no FDA data)",
    notes="Research-grade topical anti-androgen. No FDA approval. Very common in enhanced community for hair.",
))

_add(Compound(
    id="ketoconazole", canonical_name="Ketoconazole",
    aliases=["Nizoral"],
    compound_class="antifungal", route="transdermal",
    half_life_hours=8,  # oral PK; topical is local
    half_life_source="FDA label (oral); topical is local effect",
    notes="Topical (shampoo) for hair. Mild anti-androgen at scalp. Minimal systemic impact.",
))

# --- GI (common with oral AAS) ---

_add(Compound(
    id="omeprazole", canonical_name="Omeprazole",
    aliases=["Prilosec"],
    compound_class="PPI", route="oral",
    half_life_hours=1,  # short, but irreversible proton pump inhibition lasts 24h
    half_life_source="FDA label",
    monitoring_markers=["2132-9", "19123-9"],  # B12 (long-term depletion), magnesium
    notes="Proton pump inhibitor. Long-term use depletes B12 and magnesium. Affects those lab values.",
))

# --- PROSTATE ---

_add(Compound(
    id="saw_palmetto", canonical_name="Saw Palmetto",
    aliases=["Serenoa repens"],
    compound_class="supplement", route="oral",
    half_life_hours=8,  # estimated
    half_life_source="Estimated (limited PK data)",
    monitoring_markers=["2857-1"],  # PSA
    notes="Mild 5AR inhibition. May lower PSA slightly. Weaker than finasteride.",
))

# --- SUPPLEMENTS THAT MOVE LABS ---

_add(Compound(
    id="red_yeast_rice", canonical_name="Red Yeast Rice",
    aliases=["RYR", "Monacolin K"],
    compound_class="supplement", route="oral",
    half_life_hours=3,  # contains lovastatin (monacolin K); lovastatin t½ ~3h
    half_life_source="FDA label for lovastatin (~3h); active component is identical",
    monitoring_markers=["2089-1", "2085-9", "1742-6"],  # LDL, HDL, ALT
    notes="Contains monacolin K (identical to lovastatin). Measurably lowers LDL. Statin side effects possible.",
))

_add(Compound(
    id="berberine", canonical_name="Berberine",
    aliases=["Berberine HCL"],
    compound_class="supplement", route="oral",
    half_life_hours=5,  # estimated
    half_life_source="PubMed: PMID 27436163 (PK review)",
    monitoring_markers=["2345-7", "4548-4", "2089-1", "2571-8"],  # glucose, A1c, LDL, trigs
    notes="AMPK activator. Lowers glucose and lipids. Often called 'natural metformin'. Drug interactions with CYP substrates.",
))

_add(Compound(
    id="coq10", canonical_name="Coenzyme Q10",
    aliases=["CoQ10", "Ubiquinone", "Ubiquinol"],
    compound_class="supplement", route="oral",
    half_life_hours=33,
    half_life_source="PubMed: PMID 24389208",
    notes="Antioxidant. Depleted by statins. Often co-prescribed. Minimal direct lab impact but statin users should track.",
))

_add(Compound(
    id="fish_oil", canonical_name="Fish Oil",
    aliases=["Omega-3", "EPA/DHA", "Fish Oil"],
    compound_class="supplement", route="oral",
    half_life_hours=48,  # EPA/DHA incorporation
    half_life_source="Estimated (fatty acid incorporation PK)",
    monitoring_markers=["2571-8"],  # triglycerides
    notes="Lowers triglycerides at high doses (3-4g EPA+DHA/day). OTC, not prescription Vascepa.",
))

_add(Compound(
    id="niacin", canonical_name="Niacin",
    aliases=["Vitamin B3", "Nicotinic Acid", "Niaspan"],
    compound_class="supplement", route="oral",
    half_life_hours=0.75,  # ~45 min
    half_life_source="FDA label (Niaspan)",
    monitoring_markers=["2085-9", "2571-8", "2345-7", "14933-6"],  # HDL, trigs, glucose, uric acid
    notes="Raises HDL, lowers trigs. Raises glucose and uric acid. Flushing common. Significant lab impact.",
))

_add(Compound(
    id="ashwagandha", canonical_name="Ashwagandha",
    aliases=["KSM-66", "Sensoril", "Withania somnifera"],
    compound_class="supplement", route="oral",
    half_life_hours=6,  # estimated
    half_life_source="Estimated (limited PK data)",
    monitoring_markers=["3016-3", "3026-2"],  # TSH, FT4 — can affect thyroid
    notes="Adaptogen. Can raise thyroid hormones (lower TSH, raise T4). Confounds thyroid panels if not tracked.",
))

_add(Compound(
    id="vitamin_d3", canonical_name="Vitamin D3",
    aliases=["Cholecalciferol", "Vitamin D", "D3"],
    compound_class="supplement", route="oral",
    half_life_hours=360,  # ~15 days for 25-OH-D
    half_life_source="PubMed: PMID 18689389",
    monitoring_markers=["1989-3"],  # 25-OH vitamin D
    notes="Very long half-life. Takes weeks to reach steady state. Directly affects 25-OH-D lab values.",
))

_add(Compound(
    id="zinc", canonical_name="Zinc",
    aliases=["Zinc Picolinate", "Zinc Glycinate", "ZMA"],
    compound_class="supplement", route="oral",
    half_life_hours=6,  # plasma elimination; tissue turnover is longer
    half_life_source="PubMed PK data (plasma t½ ~5-6h; tissue redistribution longer)",
    monitoring_markers=["2986-8", "2243-4"],  # can affect T and E2 metabolism
    notes="Aromatase inhibition at high doses. Can affect testosterone and estrogen metabolism. Confounds hormone panels.",
))

_add(Compound(
    id="proviron", canonical_name="Mesterolone",
    aliases=["Proviron"],
    compound_class="AAS", route="oral",
    half_life_hours=12,
    half_life_source="Llewellyn's Anabolics",
    is_17aa=False,  # 1-methylated, NOT 17aa — less hepatotoxic
    monitoring_markers=["2986-8", "2243-4", "13967-5"],  # T, E2, SHBG
    notes="DHT derivative. Used as ancillary for anti-estrogenic effect and SHBG binding. Not 17aa — mild on liver. Technically AAS but used as ancillary.",
))


def lookup_compound(query: str) -> Compound | None:
    """Look up a compound by ID or alias (case-insensitive)."""
    query_lower = query.strip().lower()

    # Direct ID match
    if query_lower in COMPOUNDS:
        return COMPOUNDS[query_lower]

    # Alias search
    for c in COMPOUNDS.values():
        if query_lower == c.canonical_name.lower():
            return c
        if any(query_lower == a.lower() for a in c.aliases):
            return c

    return None


def list_compounds(compound_class: str | None = None) -> list[Compound]:
    """List all compounds, optionally filtered by class."""
    compounds = list(COMPOUNDS.values())
    if compound_class:
        compounds = [c for c in compounds if c.compound_class == compound_class]
    return sorted(compounds, key=lambda c: c.canonical_name)
