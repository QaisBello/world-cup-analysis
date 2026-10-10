"""
Clean the Fjelstul World Cup Database and build the tables behind the dashboard.

Input : data/raw/*.csv (run src/download.py first)
Output: data/cleaned/tournaments.csv     one row per tournament: goals, matches, goals per match, timing mix, host result
        data/cleaned/goal_minutes.csv    goals by tournament and minute (regulation minute, stoppage flag, period)
        data/cleaned/team_tournaments.csv one row per team per tournament: W/D/L, goals, furthest stage
        data/cleaned/top_matches.csv     the highest-scoring and most one-sided matches
        data/cleaned/data_quality_log.csv
Run   : python src/build.py
"""
import os
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW, OUT = os.path.join(ROOT, "data", "raw"), os.path.join(ROOT, "data", "cleaned")
os.makedirs(OUT, exist_ok=True)
read = lambda f: pd.read_csv(os.path.join(RAW, f + ".csv"))
log = []
def note(check, rows, finding, action): log.append(dict(check=check, rows_affected=int(rows), finding=finding, action=action))

T, M, G, A, H = read("tournaments"), read("matches"), read("goals"), read("team_appearances"), read("host_countries")
note("Load", len(M), f"{len(T)} tournaments ({T.year.min()}–{T.year.max()}), {len(M):,} matches, {len(G):,} goals, {len(A):,} team-match rows.", "Read the Fjelstul World Cup Database CSVs.")
for d in (T, M, G, A, H):
    d["sex"] = d.tournament_name.str.contains("Women").map({True: "Women", False: "Men"})

# ---- stage labels are spelled several ways
STAGE = {"quarter-final": "quarter-finals", "quater-finals": "quarter-finals", "semi-final": "semi-finals"}
n = int(M.stage_name.isin(STAGE).sum() + A.stage_name.isin(STAGE).sum() + H.performance.isin(STAGE).sum())
for d, c in ((M, "stage_name"), (A, "stage_name"), (H, "performance")):
    d[c] = d[c].replace(STAGE)
note("Stage names", n, "The same stage is written as 'quarter-final', 'quarter-finals' and 'quater-finals' (typo), and 'semi-final' vs 'semi-finals'.", "Mapped to one spelling each.")

# ---- replays: 4 drawn matches were replayed in early tournaments
rep = int(M.replayed.sum())
note("Replayed matches", rep, "Four drawn matches (1934–1938) were replayed. Both the original and the replay are real matches.", "Kept both; counted as separate matches.")

# ---- stoppage time is only recorded consistently from 1998
G["stoppage"] = G.minute_stoppage.fillna(0) > 0
yrs = G[G.stoppage].tournament_id.str[3:].astype(int)
first = yrs.min(); early = ", ".join(f"{y}: {n}" for y, n in yrs[yrs < 1998].value_counts().sort_index().items())
note("Stoppage-time minutes", int(G.stoppage.sum()),
     f"Stoppage minutes first appear in {first} and only sporadically before 1998 ({early}); earlier added-time goals are logged as 45' or 90'.",
     "Stoppage-time figures use 1998 onwards, where recording is consistent.")

# ---- own goals are credited to the benefiting team
note("Own goals", int(G.own_goal.sum()), "Own goals are already credited to the team that benefited.", "Counted for that team; flagged in minute data.")

# ---- tournaments table
mt = M.groupby("tournament_id").agg(matches=("match_id", "size"), et=("extra_time", "sum"), shootouts=("penalty_shootout", "sum"), draws=("draw", "sum"))
gt = G.groupby("tournament_id").agg(goals=("goal_id", "size"), stoppage_goals=("stoppage", "sum"), penalty_goals=("penalty", "sum"), own_goals=("own_goal", "sum"),
                                    et_goals=("match_period", lambda s: s.str.startswith("extra time").sum()))
STAGE_RANK = {"group stage": 1, "first round": 1, "second group stage": 2, "round of 16": 3, "quarter-finals": 4, "final round": 5, "semi-finals": 5, "third-place match": 5, "final": 6}
TOUR = T.set_index("tournament_id")[["year", "sex", "host_country", "winner", "count_teams", "host_won"]].join(mt).join(gt)
TOUR["goals_per_match"] = (TOUR.goals / TOUR.matches).round(3)
TOUR["host_result"] = H.groupby("tournament_id").performance.first()
TOUR.reset_index().sort_values(["sex", "year"]).to_csv(os.path.join(OUT, "tournaments.csv"), index=False)

# ---- goal minutes
G["period"] = G.match_period.str.replace(", stoppage time", "", regex=False)
gm = G.groupby(["tournament_id", "sex", "minute_regulation", "stoppage", "period"]).size().rename("goals").reset_index()
gm["year"] = gm.tournament_id.str[3:].astype(int)
gm.to_csv(os.path.join(OUT, "goal_minutes.csv"), index=False)

# ---- team x tournament
A["stage_rank"] = A.stage_name.map(STAGE_RANK)
miss = A.stage_rank.isna().sum()
assert miss == 0, A[A.stage_rank.isna()].stage_name.unique()
tt = A.groupby(["tournament_id", "sex", "team_name", "team_code"]).agg(
    played=("match_id", "size"), won=("win", "sum"), drawn=("draw", "sum"), lost=("lose", "sum"),
    goals_for=("goals_for", "sum"), goals_against=("goals_against", "sum"), stage_rank=("stage_rank", "max")).reset_index()
tt["year"] = tt.tournament_id.str[3:].astype(int)
win = T.set_index("tournament_id").winner
tt["champion"] = tt.apply(lambda r: r.team_name == win[r.tournament_id], axis=1)
tt["finish"] = tt.stage_rank.map({1: "Group stage", 2: "Second round", 3: "Round of 16", 4: "Quarter-finals", 5: "Semi-finals", 6: "Final"})
tt.loc[tt.champion, "finish"] = "Champions"
tt.loc[(tt.stage_rank == 6) & ~tt.champion, "finish"] = "Runners-up"
tt.to_csv(os.path.join(OUT, "team_tournaments.csv"), index=False)
note("Team names", int(tt.team_name.nunique()), "Teams are kept as the database names them, so West Germany and Germany are separate, as are the Soviet Union and Russia.", "No merging; the dashboard notes it.")

# ---- top matches
M["total"] = M.home_team_score + M.away_team_score
M["margin"] = (M.home_team_score - M.away_team_score).abs()
top = pd.concat([M.nlargest(15, ["total", "margin"]).assign(list="Most goals"), M.nlargest(15, ["margin", "total"]).assign(list="Biggest margin")])
top[["list", "sex", "tournament_name", "match_date", "stage_name", "home_team_name", "home_team_score", "away_team_score", "away_team_name", "total", "margin", "extra_time"]].to_csv(os.path.join(OUT, "top_matches.csv"), index=False)

pd.DataFrame(log).to_csv(os.path.join(OUT, "data_quality_log.csv"), index=False)
print(pd.DataFrame(log)[["check", "rows_affected"]].to_string(index=False))
print(TOUR[["year", "sex", "goals_per_match", "stoppage_goals", "host_result"]].sort_values("year").tail(8))
