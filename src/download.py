"""Download the Fjelstul World Cup Database CSVs used here into data/raw/.
Source: https://github.com/jfjelstul/worldcup (© 2023 Joshua C. Fjelstul, Ph.D., CC-BY-SA 4.0)."""
import os, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://raw.githubusercontent.com/jfjelstul/worldcup/master/data-csv/"
for f in ["tournaments", "matches", "goals", "team_appearances", "tournament_standings", "teams", "host_countries", "penalty_kicks"]:
    urllib.request.urlretrieve(BASE + f + ".csv", os.path.join(ROOT, "data", "raw", f + ".csv")); print("downloaded", f)
