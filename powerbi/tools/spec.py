"""Power BI version of "World Cup, by the minute". Run from powerbi/:

    python tools/spec.py        # writes World_Cup.pbip and its folders
    python tools/validate.py    # schema and reference checks
    python tools/expected.py    # what the visuals should show, checked against the README's findings
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pbikit import C, M, build, card, color, lit, series_colors, slicer, text_box, visual  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = "World_Cup"
GREEN, GOLD, INK, GREY = "#1F7A4D", "#C9A227", "#13201B", "#9AA3A0"

TABLES = {
    "Tournaments": dict(
        file="tournaments.csv",
        description="One row per tournament: 22 men's (1930-2022) and 8 women's (1991-2019), from the Fjelstul World Cup Database.",
        columns=[("tournament_id", "string", {"isKey": True, "isHidden": True}), ("year", "int64", {"formatString": "0"}),
                 ("sex", "string", {}), ("host_country", "string", {}), ("winner", "string", {}), ("count_teams", "int64", {}),
                 ("host_won", "int64", {"isHidden": True}), ("matches", "int64", {"isHidden": True}), ("et", "int64", {"isHidden": True}),
                 ("shootouts", "int64", {"isHidden": True}), ("draws", "int64", {"isHidden": True}), ("goals", "int64", {"isHidden": True}),
                 ("stoppage_goals", "int64", {"isHidden": True}), ("penalty_goals", "int64", {"isHidden": True}),
                 ("own_goals", "int64", {"isHidden": True}), ("et_goals", "int64", {"isHidden": True}),
                 ("goals_per_match", "double", {"isHidden": True}), ("host_result", "string", {})],
        added=[("Tournament", "string", {"sortByColumn": "year"})],
        m_extra='''
            #"Tournament" = Table.AddColumn(#"Filtered Rows", "Tournament", each Text.From([year]) & " " & [sex] & "'s", type text)
        ''', m_last="Tournament"),
    "Goal Minutes": dict(
        file="goal_minutes.csv",
        description="Goals by regulation minute, stoppage flag and period for every tournament. Quarter-hour bands added in Power Query "
                    "(stoppage goals fall in the band of the half they end).",
        columns=[("tournament_id", "string", {"isHidden": True}), ("sex", "string", {"isHidden": True}), ("minute_regulation", "int64", {}),
                 ("stoppage", "boolean", {}), ("period", "string", {}), ("goals", "int64", {"isHidden": True}), ("year", "int64", {"isHidden": True})],
        added=[("Quarter-hour", "string", {"sortByColumn": "Band Order"}), ("Band Order", "int64", {"isHidden": True}),
               ("Normal Time", "boolean", {"isHidden": True})],
        m_extra='''
            #"Band Order" = Table.AddColumn(#"Filtered Rows", "Band Order", each
                if [minute_regulation] > 90 then 7 else Number.RoundUp([minute_regulation] / 15), Int64.Type),
            #"Quarter-hour" = Table.AddColumn(#"Band Order", "Quarter-hour", each
                {"", "1-15'", "16-30'", "31-45+'", "46-60'", "61-75'", "76-90+'", "Extra time"}{[Band Order]}, type text),
            #"Normal Time" = Table.AddColumn(#"Quarter-hour", "Normal Time", each
                [period] = "first half" or [period] = "second half", type logical)
        ''', m_last="Normal Time"),
    "Teams": dict(
        file="team_tournaments.csv", description="Every team at every tournament: record, goals and how far it went.",
        columns=[("tournament_id", "string", {"isHidden": True}), ("sex", "string", {"isHidden": True}), ("team_name", "string", {}),
                 ("team_code", "string", {"isHidden": True}), ("played", "int64", {}), ("won", "int64", {}), ("drawn", "int64", {}),
                 ("lost", "int64", {}), ("goals_for", "int64", {}), ("goals_against", "int64", {}), ("stage_rank", "int64", {"isHidden": True}),
                 ("year", "int64", {"formatString": "0"}), ("champion", "boolean", {}), ("finish", "string", {"sortByColumn": "Finish Order"})],
        added=[("Finish Order", "int64", {"isHidden": True})],
        m_extra='''
            #"Finish Order" = Table.AddColumn(#"Filtered Rows", "Finish Order", each List.PositionOf(
                {"Group stage", "Second round", "Round of 16", "Quarter-finals", "Semi-finals", "Runners-up", "Champions"}, [finish]), Int64.Type)
        ''', m_last="Finish Order"),
    "Records": dict(
        file="top_matches.csv", description="Highest-scoring matches and biggest margins.",
        columns=[("list", "string", {}), ("sex", "string", {}), ("tournament_name", "string", {}), ("match_date", "dateTime", {"formatString": "dd mmm yyyy"}),
                 ("stage_name", "string", {}), ("home_team_name", "string", {}), ("home_team_score", "int64", {}), ("away_team_score", "int64", {}),
                 ("away_team_name", "string", {}), ("total", "int64", {}), ("margin", "int64", {}), ("extra_time", "int64", {"isHidden": True})]),
}
RELATIONSHIPS = [
    (("Goal Minutes", "tournament_id"), ("Tournaments", "tournament_id"), {}),
    (("Teams", "tournament_id"), ("Tournaments", "tournament_id"), {}),
]

G, T, TM = "Goal Minutes", "Tournaments", "Teams"
MEASURES = [
    ("Total Goals", G, "Goals", "#,0", "SUM ( 'Goal Minutes'[goals] )", "Goals scored, all periods."),
    ("Normal-Time Goals", G, "Goals", "#,0", "CALCULATE ( [Total Goals], 'Goal Minutes'[Normal Time] == TRUE () )", "Goals in the 90 minutes plus stoppage time."),
    ("Share of Normal-Time Goals", G, "Goals", "0%", """DIVIDE (
    [Normal-Time Goals],
    CALCULATE ( [Normal-Time Goals], REMOVEFILTERS ( 'Goal Minutes'[Quarter-hour], 'Goal Minutes'[Band Order] ) )
)""", "Share of normal-time goals in each quarter-hour (an even spread would be 17% each)."),
    ("Even Spread", G, "Goals", "0%", "1 / 6", "Reference line: one sixth of goals per quarter-hour."),
    ("Last 15 Minutes Share", G, "Goals", "0%", """DIVIDE (
    CALCULATE ( [Normal-Time Goals], 'Goal Minutes'[Band Order] = 6 ),
    [Normal-Time Goals]
)""", "Share of normal-time goals from the 76th minute on, including stoppage time."),
    ("First 15 Minutes Share", G, "Goals", "0%", "DIVIDE ( CALCULATE ( [Normal-Time Goals], 'Goal Minutes'[Band Order] = 1 ), [Normal-Time Goals] )",
     "Share of normal-time goals in the opening 15 minutes."),
    ("Tournaments Count", T, "Tournaments", "#,0", "COUNTROWS ( Tournaments )", "Tournaments in context."),
    ("Matches Played", T, "Tournaments", "#,0", "SUM ( Tournaments[matches] )", "Matches played."),
    ("Goals per Match", T, "Tournaments", "0.00", "DIVIDE ( SUM ( Tournaments[goals] ), [Matches Played] )", "Goals per match."),
    ("Hosts Who Won", T, "Hosts", "#,0", "SUM ( Tournaments[host_won] )", "Tournaments won by the host."),
    ("Hosts in Last Four", T, "Hosts", "#,0",
     'CALCULATE ( COUNTROWS ( Tournaments ), Tournaments[host_result] IN { "champions", "runners-up", "third place", "fourth place" } )',
     "Hosts that reached the semi-finals."),
    ("Average Teams", T, "Hosts", "0", "AVERAGE ( Tournaments[count_teams] )", "Teams per tournament (a random team's chance of winning is about 1 in this)."),
    ("Appearances", TM, "Nations", "#,0", "COUNTROWS ( Teams )", "Tournaments played."),
    ("Titles", TM, "Nations", "#,0", "CALCULATE ( COUNTROWS ( Teams ), Teams[champion] == TRUE () ) + 0", "World Cups won."),
    ("Wins", TM, "Nations", "#,0", "SUM ( Teams[won] )", "Matches won."),
    ("Goal Difference", TM, "Nations", "+#,0;-#,0;0", "SUM ( Teams[goals_for] ) - SUM ( Teams[goals_against] )", "Goals for minus against."),
]

p1, p2, p3 = "clock", "tournaments", "nations"
share, even = M(G, "Share of Normal-Time Goals", "Share of goals"), M(G, "Even Spread", "Even spread")
PAGES = [
    (p1, "Goal clock", [
        text_box(p1, "title", 24, 12, 860, 52, "World Cup, by the minute: when goals come", 18),
        slicer(p1, "sex", 900, 8, 356, 64, C(T, "sex", "Men's or women's"), None),
        card(p1, "last", 24, 76, 300, 96, M(G, "Last 15 Minutes Share", "Goals from the 76th minute")),
        card(p1, "first", 336, 76, 300, 96, M(G, "First 15 Minutes Share", "Goals in the first 15 minutes")),
        card(p1, "goals", 648, 76, 300, 96, M(G, "Total Goals", "Goals")),
        card(p1, "gpm", 960, 76, 296, 96, M(T, "Goals per Match", "Goals per match")),
        visual(p1, "bands", "lineClusteredColumnComboChart", 24, 184, 1232, 524,
               {"Category": [C(G, "Quarter-hour")], "Y": [share], "Y2": [even]},
               "Share of normal-time goals by quarter-hour (line: an even spread)",
               objects={"dataPoint": series_colors([share, even], [GREEN, GOLD]), "labels": [{"properties": {"show": lit(True)}}]},
               sort=(C(G, "Quarter-hour"), "Ascending"), z=10),
    ]),
    (p2, "Tournaments", [
        text_box(p2, "title", 24, 12, 1232, 52, "Scoring collapsed, then levelled off; and hosts do better than chance", 18),
        card(p2, "won", 24, 76, 400, 96, M(T, "Hosts Who Won", "Hosts who won")),
        card(p2, "four", 436, 76, 400, 96, M(T, "Hosts in Last Four", "Hosts in the last four")),
        card(p2, "teams", 848, 76, 408, 96, M(T, "Average Teams", "Teams per tournament")),
        visual(p2, "gpm", "lineChart", 24, 184, 760, 524, {"Category": [C(T, "year", "Year")], "Y": [M(T, "Goals per Match")], "Series": [C(T, "sex", "Competition")]},
               "Goals per match, every tournament", sort=(C(T, "year"), "Ascending"), z=10),
        visual(p2, "hosts", "tableEx", 800, 184, 456, 524,
               {"Values": [C(T, "Tournament"), C(T, "host_country", "Host"), C(T, "host_result", "Host finished"), C(T, "winner", "Winner")]},
               "Every host and how far it went", sort=(C(T, "Tournament"), "Ascending"), z=11),
    ]),
    (p3, "Nations", [
        text_box(p3, "title", 24, 12, 700, 52, "Nation explorer", 18),
        slicer(p3, "team", 736, 8, 260, 64, C(TM, "team_name", "Team"), None, single=True),
        slicer(p3, "sex", 1008, 8, 248, 64, C(T, "sex", "Men's or women's"), None),
        card(p3, "apps", 24, 76, 300, 96, M(TM, "Appearances", "Tournaments")),
        card(p3, "titles", 336, 76, 300, 96, M(TM, "Titles", "World Cups won")),
        card(p3, "wins", 648, 76, 300, 96, M(TM, "Wins", "Matches won")),
        card(p3, "gd", 960, 76, 296, 96, M(TM, "Goal Difference", "Goal difference")),
        visual(p3, "record", "tableEx", 24, 184, 760, 524,
               {"Values": [C(TM, "year", "Year"), C(TM, "finish", "Finish"), C(TM, "played", "P"), C(TM, "won", "W"), C(TM, "drawn", "D"),
                           C(TM, "lost", "L"), C(TM, "goals_for", "GF"), C(TM, "goals_against", "GA")]},
               "Every tournament for the selected team", sort=(C(TM, "year"), "Descending"), z=10),
        visual(p3, "records", "tableEx", 800, 184, 456, 524,
               {"Values": [C("Records", "list", "Record"), C("Records", "tournament_name", "Tournament"), C("Records", "home_team_name", "Home"),
                           C("Records", "home_team_score", "Home goals"), C("Records", "away_team_score", "Away goals"), C("Records", "away_team_name", "Away")]},
               "Records: most goals and biggest margins", sort=(C("Records", "home_team_score"), "Descending"), z=11),
    ]),
]

SPEC = dict(name=NAME, root=ROOT, tables=TABLES, measures=MEASURES, relationships=RELATIONSHIPS, pages=PAGES,
            base_url="https://raw.githubusercontent.com/QaisBello/world-cup-analysis/main/data/cleaned/",
            base_desc="Folder of cleaned CSVs from this repo (data/cleaned). Point it at a local folder or another branch to test.")

if __name__ == "__main__":
    build(SPEC)
