import argparse
import csv
import hashlib
import os
import random
from datetime import date, datetime, timedelta
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
    nationalities = [
        "US",
        "MX",
        "GT",
        "ES",
        "AR",
        "CO",
        "CL",
        "FR",
        "DE",
        "IT",
    ]

    def _stable_int(seed: str, modulo: int) -> int:
        raw = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:8]
        return int(raw, 16) % modulo

    for m in movies:
        d = (m.get("director") or "").strip()
        if d:
            director_id = "D_" + d.lower().replace(" ", "_")
            idx = _stable_int(director_id, len(nationalities))
            birth_year = 1945 + _stable_int(director_id + "_birth", 45)
            birth_month = 1 + _stable_int(director_id + "_month", 12)
            birth_day = 1 + _stable_int(director_id + "_day", 28)
            unique[director_id] = {
                "director_id": director_id,
                "name": d,
                "nationality": nationalities[idx],
                "birth_date": f"{birth_year:04d}-{birth_month:02d}-{birth_day:02d}",
                "active": _stable_int(director_id + "_active", 10) >= 2,
                "style_tags": ["cinema", "feature", f"region_{nationalities[idx].lower()}"],
            }
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


def normalize_genres(movie_genres: List[Dict[str, str]]) -> List[Dict[str, object]]:
    counts: Dict[str, int] = {}
    for row in movie_genres:
        genre = (row.get("genre") or "").strip()
        if genre:
            counts[genre] = counts.get(genre, 0) + 1

    if not counts:
        return []

    max_count = max(counts.values())
    out: List[Dict[str, object]] = []
    for genre, count in sorted(counts.items()):
        out.append(
            {
                "name": genre,
                "description": f"Titles categorized as {genre}",
                "popularity_index": round(count / max_count, 4),
                "active": True,
                "created_at": None,
            }
        )
    return out


def _safe_date(date_text: str, fallback: date) -> date:
    if not date_text:
        return fallback
    try:
        return datetime.strptime(date_text, "%Y-%m-%d").date()
    except ValueError:
        return fallback


def build_additional_relationship_data(
    users: List[Dict[str, object]],
    movies_raw: List[Dict[str, str]],
    movie_genres_raw: List[Dict[str, str]],
    views: List[Dict[str, object]],
    ratings: List[Dict[str, object]],
) -> Dict[str, List[Dict[str, object]]]:
    rng = random.Random(42)
    today = date.today()

    movie_ids = [row["movie_id"] for row in movies_raw if row.get("movie_id")]
    movie_director: Dict[str, str] = {}
    for row in movies_raw:
        movie_id = row.get("movie_id")
        director = (row.get("director") or "").strip()
        if movie_id and director:
            movie_director[movie_id] = "D_" + director.lower().replace(" ", "_")

    movie_genres_map: Dict[str, set] = {}
    genre_names: set = set()
    for row in movie_genres_raw:
        movie_id = row.get("movie_id")
        genre = row.get("genre")
        if not movie_id or not genre:
            continue
        movie_genres_map.setdefault(movie_id, set()).add(genre)
        genre_names.add(genre)

    viewed_by_user: Dict[str, set] = {}
    for row in views:
        viewed_by_user.setdefault(str(row["user_id"]), set()).add(str(row["movie_id"]))

    rated_by_user: Dict[str, set] = {}
    likes_seed = []
    for row in ratings:
        user_id = str(row["user_id"])
        movie_id = str(row["movie_id"])
        rated_by_user.setdefault(user_id, set()).add(movie_id)
        if float(row.get("rating") or 0) >= 8.0:
            likes_seed.append(
                {
                    "user_id": user_id,
                    "movie_id": movie_id,
                    "liked_at": str(row.get("rating_date") or today.isoformat()),
                    "strength": round(min(1.0, float(row.get("rating") or 8.0) / 10.0), 3),
                    "source": "high_rating",
                }
            )

    watchlisted_rows: List[Dict[str, object]] = []
    liked_rows: List[Dict[str, object]] = likes_seed[:]
    follows_rows: List[Dict[str, object]] = []
    created_rows: List[Dict[str, object]] = []
    user_collections: List[Dict[str, object]] = []
    user_collection_contains_rows: List[Dict[str, object]] = []

    liked_seen = {(row["user_id"], row["movie_id"]) for row in liked_rows}

    for user in users:
        user_id = str(user["user_id"])
        register_date = _safe_date(str(user.get("register_date") or ""), today - timedelta(days=365))
        preferred_genres = set(user.get("preferred_genres") or [])
        seen_movies = viewed_by_user.get(user_id, set()) | rated_by_user.get(user_id, set())

        # WATCHLISTED: unseen movies aligned with preferred genres.
        candidates = []
        for movie_id in movie_ids:
            if movie_id in seen_movies:
                continue
            genres = movie_genres_map.get(movie_id, set())
            score = len(preferred_genres.intersection(genres))
            if score > 0:
                candidates.append((movie_id, score))
        candidates.sort(key=lambda x: (-x[1], x[0]))
        watchlist_size = min(6, max(2, len(candidates) // 400 + 2))
        for rank, (movie_id, _score) in enumerate(candidates[:watchlist_size], start=1):
            added_at = register_date + timedelta(days=rng.randint(15, 1200))
            if added_at > today:
                added_at = today
            watchlisted_rows.append(
                {
                    "user_id": user_id,
                    "movie_id": movie_id,
                    "added_at": added_at.isoformat(),
                    "priority": rank,
                    "source": "genre_match",
                }
            )

        # LIKED: derive additional likes from deep views when no high rating exists.
        for row in views:
            if str(row["user_id"]) != user_id:
                continue
            if float(row.get("progress") or 0) < 0.95:
                continue
            key = (user_id, str(row["movie_id"]))
            if key in liked_seen:
                continue
            liked_seen.add(key)
            liked_rows.append(
                {
                    "user_id": user_id,
                    "movie_id": str(row["movie_id"]),
                    "liked_at": str(row.get("view_date") or today.isoformat()),
                    "strength": round(0.6 + 0.4 * float(row.get("progress") or 1.0), 3),
                    "source": "high_completion",
                }
            )

        # FOLLOWS_DIRECTOR: top directors from liked movies.
        director_counts: Dict[str, int] = {}
        for like in liked_rows:
            if like["user_id"] != user_id:
                continue
            director_id = movie_director.get(str(like["movie_id"]))
            if not director_id:
                continue
            director_counts[director_id] = director_counts.get(director_id, 0) + 1
        top_directors = sorted(director_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
        for director_id, count in top_directors:
            since_date = register_date + timedelta(days=rng.randint(30, 900))
            if since_date > today:
                since_date = today
            follows_rows.append(
                {
                    "user_id": user_id,
                    "director_id": director_id,
                    "since_date": since_date.isoformat(),
                    "affinity": round(min(1.0, 0.35 + 0.15 * count), 3),
                    "source": "liked_movies",
                }
            )

        # User collections for recommendation and social use cases.
        liked_movies = [row["movie_id"] for row in liked_rows if row["user_id"] == user_id][:20]
        watchlist_movies = [row["movie_id"] for row in watchlisted_rows if row["user_id"] == user_id][:20]

        # Keep collections non-empty even for low-activity users.
        if not liked_movies:
            fallback_seen = sorted(seen_movies)
            if fallback_seen:
                liked_movies = fallback_seen[:1]
            elif movie_ids:
                liked_movies = [movie_ids[0]]
        if not watchlist_movies:
            unseen = [m for m in movie_ids if m not in seen_movies]
            if unseen:
                watchlist_movies = unseen[:1]
            elif movie_ids:
                watchlist_movies = [movie_ids[-1]]

        fav_collection_id = f"COL_U_{user_id}_FAV"
        watch_collection_id = f"COL_U_{user_id}_WATCH"

        user_collections.append(
            {
                "collection_id": fav_collection_id,
                "name": f"{user_id} Favorites",
                "created_at": register_date.isoformat(),
                "public": bool(user.get("premium", False)),
                "followers_count": rng.randint(0, 40),
                "genre": "",
            }
        )
        user_collections.append(
            {
                "collection_id": watch_collection_id,
                "name": f"{user_id} Watchlist",
                "created_at": register_date.isoformat(),
                "public": False,
                "followers_count": 0,
                "genre": "",
            }
        )

        created_rows.append(
            {
                "user_id": user_id,
                "collection_id": fav_collection_id,
                "created_at": register_date.isoformat(),
                "title": "favorites",
                "public": bool(user.get("premium", False)),
            }
        )
        created_rows.append(
            {
                "user_id": user_id,
                "collection_id": watch_collection_id,
                "created_at": register_date.isoformat(),
                "title": "watchlist",
                "public": False,
            }
        )

        for movie_id in liked_movies:
            user_collection_contains_rows.append(
                {
                    "collection_id": fav_collection_id,
                    "movie_id": movie_id,
                    "source": "liked_seed",
                }
            )
        for movie_id in watchlist_movies:
            user_collection_contains_rows.append(
                {
                    "collection_id": watch_collection_id,
                    "movie_id": movie_id,
                    "source": "watchlist_seed",
                }
            )

    # Assign a creator to global genre collections using a stable existing user.
    owner_user_id = str(users[0]["user_id"]) if users else None
    if owner_user_id:
        for genre in sorted(genre_names):
            collection_id = "COL_" + genre.lower().replace(" ", "_")
            created_rows.append(
                {
                    "user_id": owner_user_id,
                    "collection_id": collection_id,
                    "created_at": today.isoformat(),
                    "title": "genre_catalog",
                    "public": True,
                }
            )

    return {
        "watchlisted": watchlisted_rows,
        "liked": liked_rows,
        "follows_director": follows_rows,
        "created": created_rows,
        "user_collections": user_collections,
        "user_collection_contains": user_collection_contains_rows,
    }


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
    genres = normalize_genres(movie_genres_raw)
    users = normalize_users(users_raw)
    languages = normalize_languages(movies_raw, users_raw)
    collections = normalize_collections(movie_genres_raw)
    views = normalize_views(views_raw)
    ratings = normalize_ratings(ratings_raw)
    preferences = normalize_preferences(preferences_raw)
    friendships = normalize_friendships(friendships_raw)
    directors = normalize_directors(movies_raw)
    directed_by = normalize_directed_by(movies_raw)
    additional = build_additional_relationship_data(users, movies_raw, movie_genres_raw, views, ratings)
    collections.extend(additional["user_collections"])

    print("Prepared records:")
    print(f"- movies: {len(movies)}")
    print(f"- genres links: {len(movie_genres)}")
    print(f"- genres: {len(genres)}")
    print(f"- users: {len(users)}")
    print(f"- languages: {len(languages)}")
    print(f"- collections: {len(collections)}")
    print(f"- views: {len(views)}")
    print(f"- ratings: {len(ratings)}")
    print(f"- preferences: {len(preferences)}")
    print(f"- friendships: {len(friendships)}")
    print(f"- directors: {len(directors)}")
    print(f"- directed_by: {len(directed_by)}")
    print(f"- watchlisted: {len(additional['watchlisted'])}")
    print(f"- liked: {len(additional['liked'])}")
    print(f"- follows_director: {len(additional['follows_director'])}")
    print(f"- created: {len(additional['created'])}")

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
    SET d.name = row.name,
        d.nationality = row.nationality,
        d.birth_date = CASE WHEN row.birth_date IS NULL THEN null ELSE date(row.birth_date) END,
        d.active = row.active,
        d.style_tags = row.style_tags
    """

    query_genres = """
    UNWIND $rows AS row
    MERGE (g:Genre {name: row.name})
    SET g.description = row.description,
        g.popularity_index = row.popularity_index,
        g.active = row.active,
        g.created_at = CASE WHEN row.created_at IS NULL THEN date() ELSE date(row.created_at) END
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
        c.created_at = CASE WHEN row.created_at IS NULL THEN date() ELSE date(row.created_at) END,
        c.public = row.public,
        c.followers_count = row.followers_count
    """

    query_directed_by = """
    UNWIND $rows AS row
    MATCH (d:Director {director_id: row.director_id})
    MATCH (m:Movie {movie_id: row.movie_id})
    MERGE (d)-[r:DIRECTED]->(m)
    SET r.source = 'movies_clean',
        r.last_updated = date(),
        r.role = 'director'
    """

    query_genre_rel = """
    UNWIND $rows AS row
    MERGE (g:Genre {name: row.genre})
    WITH row, g
    MATCH (m:Movie {movie_id: row.movie_id})
    MERGE (m)-[r:HAS_GENRE]->(g)
    SET r.source = 'movies_clean',
        r.last_updated = date(),
        r.relevance = 1.0
    """

    query_language_rel = """
    UNWIND $rows AS row
    MATCH (m:Movie {movie_id: row.movie_id})
    MATCH (l:Language {code: row.code})
    MERGE (m)-[r:IN_LANGUAGE]->(l)
    SET r.source = 'movies_clean',
        r.last_updated = date(),
        r.is_original = true
    """

    query_collection_rel = """
    UNWIND $rows AS row
    MATCH (c:Collection {collection_id: row.collection_id})
    MATCH (m:Movie {movie_id: row.movie_id})
    MERGE (c)-[r:CONTAINS]->(m)
    SET r.source = COALESCE(row.source, 'genre_grouping'),
        r.last_updated = date(),
        r.position = COALESCE(row.position, 0)
    """

    query_watchlisted = """
    UNWIND $rows AS row
    MATCH (u:User {user_id: row.user_id})
    MATCH (m:Movie {movie_id: row.movie_id})
    MERGE (u)-[r:WATCHLISTED {movie_id: row.movie_id}]->(m)
    SET r.added_at = date(row.added_at),
        r.priority = row.priority,
        r.source = row.source
    """

    query_liked = """
    UNWIND $rows AS row
    MATCH (u:User {user_id: row.user_id})
    MATCH (m:Movie {movie_id: row.movie_id})
    MERGE (u)-[r:LIKED {movie_id: row.movie_id}]->(m)
    SET r.liked_at = date(row.liked_at),
        r.strength = row.strength,
        r.source = row.source
    """

    query_follows_director = """
    UNWIND $rows AS row
    MATCH (u:User {user_id: row.user_id})
    MATCH (d:Director {director_id: row.director_id})
    MERGE (u)-[r:FOLLOWS_DIRECTOR]->(d)
    SET r.since_date = date(row.since_date),
        r.affinity = row.affinity,
        r.source = row.source
    """

    query_created_collection = """
    UNWIND $rows AS row
    MATCH (u:User {user_id: row.user_id})
    MATCH (c:Collection {collection_id: row.collection_id})
    MERGE (u)-[r:CREATED]->(c)
    SET r.created_at = date(row.created_at),
        r.title = row.title,
        r.public = row.public
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
        run_batched_write(session, query_genres, genres, args.batch_size, "genres")
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
            {
                "collection_id": "COL_" + row["genre"].lower().replace(" ", "_"),
                "movie_id": row["movie_id"],
                "source": "genre_grouping",
            }
            for row in movie_genres_raw
            if row.get("movie_id") and row.get("genre")
        ]
        collection_rows.extend(additional["user_collection_contains"])
        run_batched_write(session, query_language_rel, language_rows, args.batch_size, "movie_languages")
        run_batched_write(session, query_collection_rel, collection_rows, args.batch_size, "collections")
        run_batched_write(session, query_views, views, args.batch_size, "views")
        run_batched_write(session, query_ratings, ratings, args.batch_size, "ratings")
        run_batched_write(session, query_preferences, preferences, args.batch_size, "preferences")
        run_batched_write(session, query_friendships, friendships, args.batch_size, "friendships")
        run_batched_write(session, query_watchlisted, additional["watchlisted"], args.batch_size, "watchlisted")
        run_batched_write(session, query_liked, additional["liked"], args.batch_size, "liked")
        run_batched_write(session, query_follows_director, additional["follows_director"], args.batch_size, "follows")
        run_batched_write(session, query_created_collection, additional["created"], args.batch_size, "created")

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
            "watchlisted": "MATCH ()-[r:WATCHLISTED]->() RETURN count(r) AS c",
            "liked": "MATCH ()-[r:LIKED]->() RETURN count(r) AS c",
            "follows_director": "MATCH ()-[r:FOLLOWS_DIRECTOR]->() RETURN count(r) AS c",
            "created": "MATCH ()-[r:CREATED]->() RETURN count(r) AS c",
        }

        for name, stmt in checks.items():
            c = session.run(stmt).single()["c"]
            print(f"- {name}: {c}")

    driver.close()
    print("Done.")


if __name__ == "__main__":
    main()
