# World Cup, by the minute: Power BI

Every men's (1930-2022) and women's (1991-2019) World Cup goal, timed and counted, as a Power BI report.

This folder is a Power BI project (`World_Cup.pbip`): a TMDL semantic model and a PBIR report. It is generated from one Python spec, checked against Microsoft's JSON schemas, and its numbers are recomputed independently in pandas.

## Open it

1. Open **`World_Cup.pbip`** in Power BI Desktop. In versions before mid-2025, first turn on the preview features for Power BI Project (.pbip), the TMDL model format and the PBIR report format.
2. Click **Refresh**. The model reads this repo's cleaned CSVs from GitHub through the **BaseUrl** parameter. If asked, choose **Anonymous** access for `raw.githubusercontent.com`.
3. Check the visuals against [`docs/expected_values.md`](docs/expected_values.md).

## Pages

- **Goal clock:** men's/women's slicer; share of normal-time goals in each quarter-hour against an even spread; late-goal and early-goal shares.
- **Tournaments:** goals per match at every tournament; hosts who won and reached the last four; every host's finish.
- **Nations:** pick a team: tournaments, titles, wins, goal difference and its record at every edition; the record matches.

## Model

- **Tables:** Tournaments, Goal Minutes, Teams, Records.
- **Relationships:** Goal Minutes[tournament_id] to Tournaments[tournament_id]; Teams[tournament_id] to Tournaments[tournament_id].
- **16 DAX measures** in display folders: Goals (Total Goals, Normal-Time Goals, Share of Normal-Time Goals, Even Spread, Last 15 Minutes Share, First 15 Minutes Share); Tournaments (Tournaments Count, Matches Played, Goals per Match); Hosts (Hosts Who Won, Hosts in Last Four, Average Teams); Nations (Appearances, Titles, Wins, Goal Difference). The full DAX is in [`docs/measures.md`](docs/measures.md).

## Notes

- Quarter-hour bands are added in Power Query; stoppage-time goals count in the band of the half they end, and extra time is kept out of the normal-time shares.
- `tools/expected.py` checks the README's findings (22% late, 13% early, hosts 7 and 14, 5.38 and 2.21 goals a game, women's 3.23): all agree.

## Rebuild and check

```bash
pip install jsonschema referencing pandas numpy
python tools/spec.py        # the spec: writes the .pbip and its folders
python tools/validate.py    # Microsoft schemas, field and DAX references, name clashes
python tools/expected.py    # what the report should show, checked against the project's own results
```

`tools/pbikit.py` is a small shared library for writing Power BI projects as code. It is used across the portfolio and encodes lessons from real Power BI Desktop runs: names are case-insensitive; a format string must not start with a quote; empty CSV cells must become null before a type change; in DAX, `BLANK() = FALSE()` is true.
