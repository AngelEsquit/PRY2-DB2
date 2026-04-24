import argparse
import csv
import os
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
from neo4j import GraphDatabase


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def batched(items: List[Dict[str, str]], size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def to_bool(value: str) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def normalize_movies(rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    out = []
    for r in rows:
        out.append(
            {
                "movie_id": r["movie_id"],
                "title": r["title"],
                "original_title": r.get("original_title") or "",
                "original_language": r.get("original_language") or "",
                "status": r.get("status") or "",
                "overview": r.get("overview") or "",
                "release_date": r.get("release_date") or None,
                "runtime": float(r.get("runtime") or 0),
                "budget": int(float(r.get("budget") or 0)),
                "revenue": int(float(r.get("revenue") or 0)),
                "vote_average": float(r.get("vote_average") or 0),
                "vote_count": int(float(r.get("vote_count") or 0)),
                "popularity": float(r.get("popularity") or 0),
            }
        )
    return out


def normalize_users(rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    out = []
    for r in rows:
        langs = [x for x in (r.get("favorite_languages") or "").split("|") if x]
        pref_genres = [x for x in (r.get("preferred_genres") or "").split("|") if x]
        out.append(
            {
                "user_id": r["user_id"],
                "name": r["name"],
                "age": int(float(r.get("age") or 0)),
                "country": r.get("country") or "",
                "register_date": r.get("register_date") or None,
                "premium": to_bool(r.get("premium") or "false"),
                "favorite_languages": langs,
                "preferred_genres": pref_genres,
            }
        )
    return out


def normalize_movie_genres(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    return [{"movie_id": r["movie_id"], "genre": r["genre"]} for r in rows]


def normalize_directors(movies: List[Dict[str, str]]) -> List[Dict[str, str]]:
    unique = {}
    for m in movies:
        d = (m.get("director") or "").strip()
        if d:
            director_id = "D_" + d.lower().replace(" ", "_")
            unique[director_id] = {"director_id": director_id, "name": d}
    return list(unique.values())


def normalize_directed_by(movies: List[Dict[str, str]]) -> List[Dict[str, str]]:
    rels = []
    for m in movies:
        d = (m.get("director") or "").strip()
        movie_id = m.get("movie_id")
        if d and movie_id:
            director_id = "D_" + d.lower().replace(" ", "_")
            rels.append({"director_id": director_id, "movie_id": movie_id})
    return rels


def normalize_views(rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    out = []
    for r in rows:
        out.append(
            {
                "user_id": r["user_id"],
                "movie_id": r["movie_id"],
                "view_date": r.get("view_date") or None,
                "device": r.get("device") or "desktop",
                "progress": float(r.get("progress") or 0),
            }
        )
    return out


def normalize_ratings(rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    out = []
    for r in rows:
        out.append(
            {
                "user_id": r["user_id"],
                "movie_id": r["movie_id"],
                "rating": float(r.get("rating") or 0),
                "rating_date": r.get("rating_date") or None,
                "comment": r.get("comment") or "Sin comentario",
            }
        )
    return out


def normalize_preferences(rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    out = []
    for r in rows:
        out.append(
            {
                "user_id": r["user_id"],
                "genre": r["genre"],
                "weight": float(r.get("weight") or 0),
                "last_updated": r.get("last_updated") or None,
                "source": r.get("source") or "behavior",
            }
        )
    return out


def normalize_friendships(rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    out = []
    for r in rows:
        out.append(
            {
                "user_id_1": r["user_id_1"],
                "user_id_2": r["user_id_2"],
                "since_date": r.get("since_date") or None,
                "closeness": float(r.get("closeness") or 0),
                "interactions": int(float(r.get("interactions") or 0)),
            }
        )
    return out


LANGUAGE_NAMES = {
    "en": ("English", "Global", "Germanic", False),
    "es": ("Spanish", "Latin America / Spain", "Romance", False),
    "fr": ("French", "France / Francophone", "Romance", False),
    "de": ("German", "Germany / German-speaking", "Germanic", False),
    "it": ("Italian", "Italy / Italian-speaking", "Romance", False),
    "pt": ("Portuguese", "Portugal / Brazil", "Romance", False),
    "ja": ("Japanese", "Japan", "Japonic", False),
    "ko": ("Korean", "Korea", "Koreanic", False),
}


def normalize_languages(movies: List[Dict[str, str]], users: List[Dict[str, str]]) -> List[Dict[str, object]]:
    codes = set()

    for movie in movies:
        code = (movie.get("original_language") or "").strip().lower()
        if code:
            codes.add(code)

    for user in users:
        for code in (user.get("favorite_languages") or "").split("|"):
            code = code.strip().lower()
            if code:
                codes.add(code)

    out = []
    for code in sorted(codes):
        name, region, family, rtl = LANGUAGE_NAMES.get(code, (code.upper(), "Unknown", "Unknown", False))
        out.append(
            {
                "code": code,
                "name": name,
                "region": region,
                "family": family,
                "rtl": rtl,
            }
        )
    return out


def normalize_collections(movie_genres: List[Dict[str, str]]) -> List[Dict[str, object]]:
    genre_counts: Dict[str, int] = {}
    for row in movie_genres:
        genre = (row.get("genre") or "").strip()
        if not genre:
            continue
        genre_counts[genre] = genre_counts.get(genre, 0) + 1

    out = []
    for genre, count in sorted(genre_counts.items()):
        collection_id = "COL_" + genre.lower().replace(" ", "_")
        out.append(
            {
                "collection_id": collection_id,
                "name": f"Collection - {genre}",
                "created_at": None,
                "public": True,
                "followers_count": count,
                "genre": genre,
            }
        )
    return out


def create_constraints(session):
    stmts = [
        "CREATE CONSTRAINT movie_id_unique IF NOT EXISTS FOR (m:Movie) REQUIRE m.movie_id IS UNIQUE",
        "CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE",
        "CREATE CONSTRAINT genre_name_unique IF NOT EXISTS FOR (g:Genre) REQUIRE g.name IS UNIQUE",
        "CREATE CONSTRAINT director_id_unique IF NOT EXISTS FOR (d:Director) REQUIRE d.director_id IS UNIQUE",
        "CREATE CONSTRAINT language_code_unique IF NOT EXISTS FOR (l:Language) REQUIRE l.code IS UNIQUE",
        "CREATE CONSTRAINT collection_id_unique IF NOT EXISTS FOR (c:Collection) REQUIRE c.collection_id IS UNIQUE",
    ]
    for stmt in stmts:
        session.run(stmt)


def run_batched_write(session, query: str, rows: List[Dict[str, object]], batch_size: int, label: str):
    total = len(rows)
    for i, chunk in enumerate(batched(rows, batch_size), start=1):
        session.run(query, rows=chunk)
        if i % 10 == 0 or i == 1 or i * batch_size >= total:
            print(f"[{label}] {min(i * batch_size, total)}/{total}")


def main():
    parser = argparse.ArgumentParser(description="Load cleaned CSV data into Neo4j AuraDB")
    parser.add_argument("--data-dir", default="data/clean", help="Directory containing cleaned CSV files")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for UNWIND writes")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print counts without writing to Neo4j")
    args = parser.parse_args()

    load_dotenv()

    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USERNAME")
    pwd = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    data_dir = Path(args.data_dir)

    movies_raw = read_csv(data_dir / "movies_clean.csv")
    movie_genres_raw = read_csv(data_dir / "movie_genres_clean.csv")
    users_raw = read_csv(data_dir / "users_clean.csv")
    views_raw = read_csv(data_dir / "user_views_clean.csv")
    ratings_raw = read_csv(data_dir / "user_ratings_clean.csv")
    preferences_raw = read_csv(data_dir / "user_preferences_clean.csv")
    friendships_raw = read_csv(data_dir / "user_friendships_clean.csv")

    movies = normalize_movies(movies_raw)
    movie_genres = normalize_movie_genres(movie_genres_raw)
    users = normalize_users(users_raw)
    languages = normalize_languages(movies_raw, users_raw)
    collections = normalize_collections(movie_genres_raw)
    views = normalize_views(views_raw)
    ratings = normalize_ratings(ratings_raw)
    preferences = normalize_preferences(preferences_raw)
    friendships = normalize_friendships(friendships_raw)
    directors = normalize_directors(movies_raw)
    directed_by = normalize_directed_by(movies_raw)

    print("Prepared records:")
    print(f"- movies: {len(movies)}")
    print(f"- genres links: {len(movie_genres)}")
    print(f"- users: {len(users)}")
    print(f"- languages: {len(languages)}")
    print(f"- collections: {len(collections)}")
    print(f"- views: {len(views)}")
    print(f"- ratings: {len(ratings)}")
    print(f"- preferences: {len(preferences)}")
    print(f"- friendships: {len(friendships)}")
    print(f"- directors: {len(directors)}")
    print(f"- directed_by: {len(directed_by)}")

    if args.dry_run:
        print("Dry-run mode: no writes executed.")
        return

    missing = [k for k, v in {"NEO4J_URI": uri, "NEO4J_USERNAME": user, "NEO4J_PASSWORD": pwd}.items() if not v]
    if missing:
        raise ValueError(f"Missing environment variables: {', '.join(missing)}")

    driver = GraphDatabase.driver(uri, auth=(user, pwd))

    query_movies = """
    UNWIND $rows AS row
    MERGE (m:Movie {movie_id: row.movie_id})
    SET m.title = row.title,
        m.original_title = row.original_title,
        m.original_language = row.original_language,
        m.status = row.status,
        m.overview = row.overview,
        m.release_date = CASE WHEN row.release_date IS NULL THEN null ELSE date(row.release_date) END,
        m.runtime = row.runtime,
        m.budget = row.budget,
        m.revenue = row.revenue,
        m.vote_average = row.vote_average,
        m.vote_count = row.vote_count,
        m.popularity = row.popularity
    """

    query_users = """
    UNWIND $rows AS row
    MERGE (u:User {user_id: row.user_id})
    SET u.name = row.name,
        u.age = row.age,
        u.country = row.country,
        u.register_date = CASE WHEN row.register_date IS NULL THEN null ELSE date(row.register_date) END,
        u.premium = row.premium,
        u.favorite_languages = row.favorite_languages,
        u.preferred_genres = row.preferred_genres
    """

    query_directors = """
    UNWIND $rows AS row
    MERGE (d:Director {director_id: row.director_id})
    SET d.name = row.name
    """

    query_languages = """
    UNWIND $rows AS row
    MERGE (l:Language {code: row.code})
    SET l.name = row.name,
        l.region = row.region,
        l.family = row.family,
        l.rtl = row.rtl
    """

    query_collections = """
    UNWIND $rows AS row
    MERGE (c:Collection {collection_id: row.collection_id})
    SET c.name = row.name,
        c.created_at = date(),
        c.public = row.public,
        c.followers_count = row.followers_count
    """

    query_directed_by = """
    UNWIND $rows AS row
    MATCH (d:Director {director_id: row.director_id})
    MATCH (m:Movie {movie_id: row.movie_id})
    MERGE (d)-[r:DIRECTED]->(m)
    SET r.source = 'movies_clean',
        r.last_updated = date()
    """

    query_genre_rel = """
    UNWIND $rows AS row
    MERGE (g:Genre {name: row.genre})
    WITH row, g
    MATCH (m:Movie {movie_id: row.movie_id})
    MERGE (m)-[r:HAS_GENRE]->(g)
    SET r.source = 'movies_clean',
        r.last_updated = date()
    """

    query_language_rel = """
    UNWIND $rows AS row
    MATCH (m:Movie {movie_id: row.movie_id})
    MATCH (l:Language {code: row.code})
    MERGE (m)-[r:IN_LANGUAGE]->(l)
    SET r.source = 'movies_clean',
        r.last_updated = date()
    """

    query_collection_rel = """
    UNWIND $rows AS row
    MATCH (c:Collection {collection_id: row.collection_id})
    MATCH (m:Movie {movie_id: row.movie_id})
    MERGE (c)-[r:CONTAINS]->(m)
    SET r.source = 'genre_grouping',
        r.last_updated = date()
    """

    query_views = """
    UNWIND $rows AS row
    MATCH (u:User {user_id: row.user_id})
    MATCH (m:Movie {movie_id: row.movie_id})
    MERGE (u)-[r:VIEWED {view_date: date(row.view_date), movie_id: row.movie_id}]->(m)
    SET r.device = row.device,
        r.progress = row.progress
    """

    query_ratings = """
    UNWIND $rows AS row
    MATCH (u:User {user_id: row.user_id})
    MATCH (m:Movie {movie_id: row.movie_id})
    MERGE (u)-[r:RATED {rating_date: date(row.rating_date), movie_id: row.movie_id}]->(m)
    SET r.rating = row.rating,
        r.comment = row.comment
    """

    query_preferences = """
    UNWIND $rows AS row
    MERGE (g:Genre {name: row.genre})
    WITH row, g
    MATCH (u:User {user_id: row.user_id})
    MERGE (u)-[r:PREFERS]->(g)
    SET r.weight = row.weight,
        r.last_updated = date(row.last_updated),
        r.source = row.source
    """

    query_friendships = """
    UNWIND $rows AS row
    MATCH (u1:User {user_id: row.user_id_1})
    MATCH (u2:User {user_id: row.user_id_2})
    MERGE (u1)-[r:FRIEND_OF]-(u2)
    SET r.since_date = date(row.since_date),
        r.closeness = row.closeness,
        r.interactions = row.interactions
    """

    with driver.session(database=database) as session:
        print("Creating constraints...")
        create_constraints(session)

        print("Loading nodes...")
        run_batched_write(session, query_movies, movies, args.batch_size, "movies")
        run_batched_write(session, query_users, users, args.batch_size, "users")
        run_batched_write(session, query_directors, directors, args.batch_size, "directors")
        run_batched_write(session, query_languages, languages, args.batch_size, "languages")
        run_batched_write(session, query_collections, collections, args.batch_size, "collections")

        print("Loading relationships...")
        run_batched_write(session, query_directed_by, directed_by, args.batch_size, "directed_by")
        run_batched_write(session, query_genre_rel, movie_genres, args.batch_size, "movie_genres")
        language_rows = [
            {"movie_id": row["movie_id"], "code": (row.get("original_language") or "").strip().lower()}
            for row in movies_raw
            if row.get("movie_id") and (row.get("original_language") or "").strip()
        ]
        collection_rows = [
            {"collection_id": "COL_" + row["genre"].lower().replace(" ", "_"), "movie_id": row["movie_id"]}
            for row in movie_genres_raw
            if row.get("movie_id") and row.get("genre")
        ]
        run_batched_write(session, query_language_rel, language_rows, args.batch_size, "movie_languages")
        run_batched_write(session, query_collection_rel, collection_rows, args.batch_size, "collections")
        run_batched_write(session, query_views, views, args.batch_size, "views")
        run_batched_write(session, query_ratings, ratings, args.batch_size, "ratings")
        run_batched_write(session, query_preferences, preferences, args.batch_size, "preferences")
        run_batched_write(session, query_friendships, friendships, args.batch_size, "friendships")

        print("Running validation counts...")
        checks = {
            "movies": "MATCH (m:Movie) RETURN count(m) AS c",
            "users": "MATCH (u:User) RETURN count(u) AS c",
            "genres": "MATCH (g:Genre) RETURN count(g) AS c",
            "directors": "MATCH (d:Director) RETURN count(d) AS c",
            "languages": "MATCH (l:Language) RETURN count(l) AS c",
            "collections": "MATCH (c:Collection) RETURN count(c) AS c",
            "viewed": "MATCH ()-[r:VIEWED]->() RETURN count(r) AS c",
            "rated": "MATCH ()-[r:RATED]->() RETURN count(r) AS c",
            "prefers": "MATCH ()-[r:PREFERS]->() RETURN count(r) AS c",
            "friend_of": "MATCH ()-[r:FRIEND_OF]-() RETURN count(r) AS c",
            "has_genre": "MATCH ()-[r:HAS_GENRE]->() RETURN count(r) AS c",
            "directed": "MATCH ()-[r:DIRECTED]->() RETURN count(r) AS c",
            "in_language": "MATCH ()-[r:IN_LANGUAGE]->() RETURN count(r) AS c",
            "contains": "MATCH ()-[r:CONTAINS]->() RETURN count(r) AS c",
        }

        for name, stmt in checks.items():
            c = session.run(stmt).single()["c"]
            print(f"- {name}: {c}")

    driver.close()
    print("Done.")


if __name__ == "__main__":
    main()
