"""
policy.py — APEX 2.0
Deterministic investment policy engine.
Enforces hard rules. Returns structured violations. Never overridden by LLM.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Optional


class PolicyVerdict(str, Enum):
    PASS    = "PASS"
    BLOCK   = "BLOCK"
    WARN    = "WARN"
    UNKNOWN = "UNKNOWN"   # required input missing — cannot evaluate


@dataclass
class PolicyCheck:
    rule_id: str
    description: str
    verdict: PolicyVerdict
    reason: str


@dataclass
class PolicyResult:
    checks: list[PolicyCheck]
    overall: PolicyVerdict   # BLOCK if any check is BLOCK; WARN if any WARN; else PASS

    @property
    def blocked(self) -> bool:
        return self.overall == PolicyVerdict.BLOCK

    @property
    def block_reasons(self) -> list[str]:
        return [c.reason for c in self.checks if c.verdict == PolicyVerdict.BLOCK]

    @property
    def warnings(self) -> list[str]:
        return [c.reason for c in self.checks if c.verdict == PolicyVerdict.WARN]


def _d(v) -> Decimal:
    return Decimal(str(v))


def evaluate_investment_proposal(
    *,
    proposed_asset_class: str,          # "equity", "bond", "cash", "crypto", "other"
    proposed_amount_eur: Decimal,
    total_savings: Decimal,
    emergency_balance: Decimal,
    emergency_target: Decimal,
    home_purchase_balance: Decimal,
    home_purchase_target: Optional[Decimal],   # None = unconfirmed
    home_purchase_horizon_years: int,
    long_term_balance: Decimal,
    permitted_instruments: list[str],          # empty = unconfirmed
    risk_tolerance: Optional[str],             # None = unconfirmed
    expenses_verified: bool,
    surplus_verified: bool,
) -> PolicyResult:
    checks: list[PolicyCheck] = []

    # R1 — Emergency reserve must be fully funded
    if emergency_balance < emergency_target:
        shortfall = emergency_target - emergency_balance
        checks.append(PolicyCheck(
            rule_id="R1",
            description="Emergency reserve fully funded",
            verdict=PolicyVerdict.BLOCK,
            reason=f"Emergency reserve underfunded by €{shortfall:.2f}. "
                   "Fund this before investing anything.",
        ))
    else:
        checks.append(PolicyCheck(
            rule_id="R1",
            description="Emergency reserve fully funded",
            verdict=PolicyVerdict.PASS,
            reason="Emergency reserve meets minimum target.",
        ))

    # R2 — Home-purchase fund protected (horizon ≤ 4 years → no equity)
    if home_purchase_target is None:
        checks.append(PolicyCheck(
            rule_id="R2",
            description="Home-purchase fund target confirmed",
            verdict=PolicyVerdict.BLOCK,
            reason="Property purchase target price and location are unconfirmed. "
                   "Cannot expose any savings to equity risk.",
        ))
    elif home_purchase_horizon_years <= 4 and proposed_asset_class in ("equity", "crypto"):
        checks.append(PolicyCheck(
            rule_id="R2",
            description="Home-purchase fund not exposed to volatile assets",
            verdict=PolicyVerdict.BLOCK,
            reason=f"Property goal is within {home_purchase_horizon_years} years. "
                   "Equity and crypto exposure for this money is prohibited.",
        ))
    else:
        checks.append(PolicyCheck(
            rule_id="R2",
            description="Home-purchase fund not exposed to volatile assets",
            verdict=PolicyVerdict.PASS,
            reason="Home-purchase fund constraint met.",
        ))

    # R3 — Investment amount must not exceed long-term bucket
    if proposed_amount_eur > long_term_balance:
        checks.append(PolicyCheck(
            rule_id="R3",
            description="Investment amount within long-term bucket",
            verdict=PolicyVerdict.BLOCK,
            reason=f"Proposed €{proposed_amount_eur:.2f} exceeds "
                   f"available long-term capital €{long_term_balance:.2f}.",
        ))
    else:
        checks.append(PolicyCheck(
            rule_id="R3",
            description="Investment amount within long-term bucket",
            verdict=PolicyVerdict.PASS,
            reason=f"Proposed amount €{proposed_amount_eur:.2f} is within long-term bucket.",
        ))

    # R4 — Permitted instruments confirmed
    if not permitted_instruments:
        checks.append(PolicyCheck(
            rule_id="R4",
            description="Permitted instruments confirmed",
            verdict=PolicyVerdict.BLOCK,
            reason="Permitted investment instruments not yet confirmed by user. "
                   "No investment recommendation can be made.",
        ))
    elif proposed_asset_class not in permitted_instruments:
        checks.append(PolicyCheck(
            rule_id="R4",
            description="Proposed asset class in permitted list",
            verdict=PolicyVerdict.BLOCK,
            reason=f"'{proposed_asset_class}' is not in the confirmed permitted list: "
                   f"{permitted_instruments}.",
        ))
    else:
        checks.append(PolicyCheck(
            rule_id="R4",
            description="Proposed asset class in permitted list",
            verdict=PolicyVerdict.PASS,
            reason=f"'{proposed_asset_class}' is permitted.",
        ))

    # R5 — Risk tolerance must be confirmed
    if risk_tolerance is None:
        checks.append(PolicyCheck(
            rule_id="R5",
            description="Risk tolerance confirmed",
            verdict=PolicyVerdict.BLOCK,
            reason="Risk tolerance not confirmed. Cannot size position or assess suitability.",
        ))
    else:
        checks.append(PolicyCheck(
            rule_id="R5",
            description="Risk tolerance confirmed",
            verdict=PolicyVerdict.PASS,
            reason=f"Risk tolerance: {risk_tolerance}.",
        ))

    # R6 — Expenses and surplus verified
    if not expenses_verified or not surplus_verified:
        checks.append(PolicyCheck(
            rule_id="R6",
            description="Monthly expenses and surplus verified",
            verdict=PolicyVerdict.WARN,
            reason="Expenses not verified from bank statements. "
                   "Actual monthly surplus may be lower than estimated.",
        ))
    else:
        checks.append(PolicyCheck(
            rule_id="R6",
            description="Monthly expenses and surplus verified",
            verdict=PolicyVerdict.PASS,
            reason="Expenses verified.",
        ))

    # R7 — Single position cap: max 25% of long-term bucket
    if long_term_balance > _d("0"):
        pct = (proposed_amount_eur / long_term_balance * 100).quantize(Decimal("0.1"))
        if pct > _d("25"):
            checks.append(PolicyCheck(
                rule_id="R7",
                description="Single position ≤ 25% of long-term bucket",
                verdict=PolicyVerdict.WARN,
                reason=f"Proposed position is {pct}% of long-term bucket. "
                       "Consider spreading across multiple instruments.",
            ))
        else:
            checks.append(PolicyCheck(
                rule_id="R7",
                description="Single position ≤ 25% of long-term bucket",
                verdict=PolicyVerdict.PASS,
                reason=f"Position concentration: {pct}% — within limit.",
            ))

    # Determine overall verdict
    verdicts = {c.verdict for c in checks}
    if PolicyVerdict.BLOCK in verdicts:
        overall = PolicyVerdict.BLOCK
    elif PolicyVerdict.UNKNOWN in verdicts:
        overall = PolicyVerdict.UNKNOWN
    elif PolicyVerdict.WARN in verdicts:
        overall = PolicyVerdict.WARN
    else:
        overall = PolicyVerdict.PASS

    return PolicyResult(checks=checks, overall=overall)
