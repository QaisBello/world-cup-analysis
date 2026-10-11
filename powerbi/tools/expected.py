"""What the Power BI report should show, recomputed in pandas and checked against the README's findings.
Run from powerbi/:  python tools/expected.py   (writes docs/expected_values.md; exit code 1 on any disagreement)"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pbikit  # noqa: E402
import spec  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN = os.path.join(os.path.dirname(ROOT), "data", "cleaned")
t = pd.read_csv(os.path.join(CLEAN, "tournaments.csv"))
g = pd.read_csv(os.path.join(CLEAN, "goal_minutes.csv"))
tm = pd.read_csv(os.path.join(CLEAN, "team_tournaments.csv"))
problems = pbikit.check_sorts(spec.SPEC, CLEAN)


def check(label, got, want):
    if got != want:
        problems.append(f"{label}: {got} vs README {want}")


nt = g[g.period.isin(["first half", "second half"])].copy()
nt["band"] = (nt.minute_regulation / 15).apply(lambda v: int(-(-v // 1)))
share = nt.groupby("band").goals.sum() / nt.goals.sum()
check("Last 15 minutes share", round(100 * share[6]), 22)
check("First 15 minutes share", round(100 * share[1]), 13)
check("Hosts who won", int(t.host_won.sum()), 7)
check("Hosts in last four", int(t.host_result.isin(["champions", "runners-up", "third place", "fourth place"]).sum()), 14)
men = t[t.sex == "Men"].set_index("year")
check("Men's peak goals per match (1954)", round(men.goals[1954] / men.matches[1954], 2), 5.38)
check("Men's low (1990)", round(men.goals[1990] / men.matches[1990], 2), 2.21)
w = t[t.sex == "Women"]
check("Women's goals per match", round(w.goals.sum() / w.matches.sum(), 2), 3.23)
labels = {1: "1-15'", 2: "16-30'", 3: "31-45+'", 4: "46-60'", 5: "61-75'", 6: "76-90+'"}
lines = ["# Expected values", "", "From `tools/expected.py`, checked against the README's findings: "
         f"**{'all agree' if not problems else 'DISAGREEMENTS: ' + '; '.join(problems)}**.", "",
         "## Goal clock (both competitions)", "", "| Card | Expected |", "|---|---:|",
         f"| Goals from the 76th minute | {share[6]:.0%} |", f"| Goals in the first 15 minutes | {share[1]:.0%} |",
         f"| Goals | {g.goals.sum():,} |", f"| Goals per match | {t.goals.sum() / t.matches.sum():.2f} |", "",
         "| Quarter-hour | Share |", "|---|---:|"] + [f"| {labels[b]} | {share[b]:.1%} |" for b in range(1, 7)] + [
         "", "## Tournaments", "", "| Card | Expected |", "|---|---:|", f"| Hosts who won | {t.host_won.sum()} |",
         f"| Hosts in the last four | {t.host_result.isin(['champions', 'runners-up', 'third place', 'fourth place']).sum()} |",
         f"| Teams per tournament | {t.count_teams.mean():.0f} |",
         "", "## Nations (select Brazil, men's)", ""]
b = tm[(tm.team_name == "Brazil") & (tm.sex == "Men")]
lines += [f"Tournaments {len(b)}, titles {int(b.champion.sum())}, wins {b.won.sum()}, goal difference {b.goals_for.sum() - b.goals_against.sum():+d}."]
os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
open(os.path.join(ROOT, "docs", "expected_values.md"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
sys.exit(1 if problems else 0)
