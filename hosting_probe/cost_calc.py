"""Per-run inference cost scenarios for docs/HOSTING_PROBE.md §4 (arithmetic only; no API calls).

Price: $0.30 / $0.90 per 1M input / output tokens (Nebius Token Factory listing, checked live
2026-10-14). Token figures are proposed planning values, not measurements.
Run: uv run --locked python hosting_probe/cost_calc.py
"""

IN, OUT = 0.30, 0.90


def cost(tokens_in: float, tokens_out: float) -> float:
    return (tokens_in * IN + tokens_out * OUT) / 1e6


NORMAL = {
    "claim": (2000, 1500),
    "diagnosis": (8000, 3000),
    "revision (1.5 on average)": (10000 * 1.5, 4000 * 1.5),
    "report": (6000, 2000),
}
CEILING = {
    "claim": (3000, 3000),
    "diagnosis": (12000, 6000),
    "revision 1": (12000, 8000),
    "revision 2": (12000, 8000),
    "report": (8000, 4000),
    "spare (largest stage)": (12000, 8000),
}

if __name__ == "__main__":
    totals = {}
    for name, stages in (("normal", NORMAL), ("ceiling", CEILING)):
        tin = sum(i for i, _ in stages.values())
        tout = sum(o for _, o in stages.values())
        totals[name] = cost(tin, tout)
        print(f"{name}: in {tin:,.0f} out {tout:,.0f} -> ${totals[name]:.4f}")
        for stage, (i, o) in stages.items():
            print(f"  {stage}: ${cost(i, o):.5f}")
    print(
        f"ceiling if retries were extra calls (12 requests): ${2 * totals['ceiling']:.4f}"
    )
    print(
        f"smoke observed: ${cost(32, 47):.7f}, ${cost(47, 52):.7f}; smoke bound ${cost(512, 1024):.6f}"
    )
    for budget in (50, 30):
        print(
            f"${budget}: {budget / totals['normal']:.0f} normal runs, {budget / totals['ceiling']:.0f} ceiling runs"
        )
