import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase


BACKFILL_QUERY = """
MATCH ()-[r:CONTAINS]->()
WHERE r.position IS NULL
SET r.position = 0,
    r.last_updated = coalesce(r.last_updated, date()),
    r.source = coalesce(r.source, 'genre_grouping')
RETURN count(r) AS updated
"""


CHECK_QUERY = """
MATCH ()-[r:CONTAINS]->()
WHERE size(keys(r)) < 3
RETURN count(r) AS c
"""


COUNT_QUERY = "MATCH ()-[r:CONTAINS]->() RETURN count(r) AS c"


def main():
    load_dotenv()

    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USERNAME")
    pwd = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    missing = [key for key, value in {"NEO4J_URI": uri, "NEO4J_USERNAME": user, "NEO4J_PASSWORD": pwd}.items() if not value]
    if missing:
        raise ValueError(f"Missing environment variables: {', '.join(missing)}")

    root = Path(__file__).resolve().parents[1]
    report_path = root / "validation_post_load_report.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    driver = GraphDatabase.driver(uri, auth=(user, pwd))
    with driver.session(database=database) as session:
        updated = session.run(BACKFILL_QUERY).single()["updated"]
        total_contains = session.run(COUNT_QUERY).single()["c"]
        remaining = session.run(CHECK_QUERY).single()["c"]

    driver.close()

    print(f"Updated CONTAINS relationships: {updated}")
    print(f"Total CONTAINS relationships: {total_contains}")
    print(f"CONTAINS with less than 3 props: {remaining}")
    print(f"Backfill completed at: {timestamp}")

    if report_path.exists():
        text = report_path.read_text(encoding="utf-8")
        if "- CONTAINS (< 3 props):" in text:
            text = text.replace(
                next(line for line in text.splitlines() if line.startswith("- CONTAINS (< 3 props):")),
                f"- CONTAINS (< 3 props): {remaining}",
            )
            report_path.write_text(text + ("" if text.endswith("\n") else "\n"), encoding="utf-8")
            print(f"Updated report: {report_path}")

    if remaining > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
