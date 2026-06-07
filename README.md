<!-- mcp-name: io.github.CSOAI-ORG/meok-cold-chain-pharma-mcp -->
[![MCP Scorecard: 84/100](https://img.shields.io/badge/proofof.ai-84%2F100-5b21b6)](https://proofof.ai/scorecard/meok-cold-chain-pharma-mcp.html)

# meok-cold-chain-pharma-mcp

[![PyPI](https://img.shields.io/badge/PyPI-1.0.0-blue)](https://pypi.org/project/meok-cold-chain-pharma-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP](https://img.shields.io/badge/MCP-1.3.0+-green)](https://modelcontextprotocol.io)

> Pharmaceutical Good Distribution Practice + cold-chain transport compliance toolkit for MHRA Responsible Persons, pharma 3PL, and clinical-trial supply teams. By **MEOK AI Labs**.

## Why this exists

UK pharmaceutical wholesale distribution is a **£550m market**. Every shipment of a prescription-only medicine (POM) must comply with **EU/UK GDP Guideline 2013/C 343/01** (MHRA-enforced under WDA(H) — Wholesale Distribution Authorisation). Most biologics + vaccines require **unbroken +2 °C to +8 °C cold-chain** from manufacturer to patient.

A single cold-chain breach means:

- **Batch quarantine + write-off** — £10k to £10m per consignment
- **MHRA WDA(H) inspection finding** — licence risk
- **Patient harm risk** — potential corporate manslaughter exposure
- **Brexit divergence pain** — UK FMD now distinct from EU FMD; NI under Windsor

This MCP gives the **Responsible Person (RP)**, the 3PL pharma logistics op, and the clinical-trial QP the callable GDP toolkit they have been managing on paper or in Excel.

## Install

```bash
pip install meok-cold-chain-pharma-mcp
```

## Claude Desktop config

```json
{
  "mcpServers": {
    "cold-chain-pharma": {
      "command": "meok-cold-chain-pharma-mcp"
    }
  }
}
```

## Tools (8)

| Tool | Use case |
|------|----------|
| `check_gdp_compliance` | EU/UK GDP 2013/C 343/01 readiness across 9 chapters. |
| `check_qualified_person_responsible` | MHRA WDA(H) Responsible Person eligibility — licence-critical. |
| `check_temperature_excursion` | 2-8 °C cold-chain breach detection + quarantine / RP review decision. |
| `check_who_pq_compliance` | WHO Prequalification readiness for UN/GAVI/Global Fund procurement. |
| `check_serialisation_falsified_medicines` | EU FMD + UK FMD post-Brexit divergence (GB / NI / EU). |
| `prepare_mhra_audit_pack` | WDA(H) inspection prep — 7 audit categories. |
| `check_dangerous_goods_pharma` | DGSA pharma overlap — dry ice ADR Class 9 + controlled drugs. |
| `validate_temperature_mapping_qualification` | WHO TRS 961 + EU GDP §3.2.1 mapping qualification check. |

## Pricing

- **Free** — MIT self-host
- **Starter** — £199/mo (signed attestations + email support)
- **Pro** — £499/mo (multi-site RP dashboard + temperature excursion alerts)
- **Fleet** — £2,999/mo (50+ sites, custom integrations, MHRA-grade audit export, SLA)

Pharma is the highest-margin compliance vertical we serve — a single avoided cold-chain breach on a biologic consignment pays for the platform many times over.

[Subscribe Pro → £499/mo](https://www.csoai.org/checkout) · [Talk to Nick](mailto:nicholas@meok.ai)

## Regulatory basis

- **EU/UK Good Distribution Practice** Guideline 2013/C 343/01
- **MHRA WDA(H)** — Wholesale Distribution Authorisation (Human)
- **WHO TRS 961 Annex 9** — cold-chain mapping protocol
- **WHO Prequalification Programme** — UN procurement standard
- **EU Falsified Medicines Directive** 2011/62/EU + Delegated Reg 2016/161
- **UK Falsified Medicines (Human Use) Regulations 2019** (post-Brexit, GB)
- **Windsor Framework 2024** — NI dual-market access
- **Medicines for Human Use (Marketing Authorisations Etc.) Regulations 1994**
- **USP 1079** — Good Storage and Distribution Practices for Drug Products
- **ADR 2025 UN1845** — dry ice as Class 9 dangerous good
- **Misuse of Drugs Regulations 2001** — Schedule 1–5 controlled drugs

## Sign your responses (production)

```bash
export MEOK_HMAC_SECRET="your-secret"
meok-cold-chain-pharma-mcp
```

Every tool response returns an HMAC-SHA256 signature for tamper-evident audit-trail evidence — useful for MHRA inspection bundles + customer (AZ / GSK / Pfizer) audit packs.

## Companion MCPs

Part of the **MEOK Haulage Compliance** stack on haulage.app:

- `meok-car-transport-uk-mcp` — DVSA + tacho + C&U
- `meok-ev-recall-transport-mcp` — ADR Class 9 EV recall
- `meok-cold-chain-pharma-mcp` — this one

## License

MIT © 2026 Nicholas Templeman / MEOK AI Labs · [haulage.app](https://haulage.app)
