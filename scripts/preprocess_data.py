import csv
import re
from datetime import datetime
from pathlib import Path

KNOWN_GENRES = [
    "Science Fiction",
    "TV Movie",
    "Action",
    "Adventure",
    "Animation",
    "Comedy",
    "Crime",
    "Documentary",
    "Drama",
    "Family",
    "Fantasy",
    "History",
    "Horror",
    "Music",
    "Mystery",
    "Romance",
    "Thriller",
    "War",
    "Western",
]

VALID_DEVICES = {"mobile", "desktop", "tablet", "tv"}


def clean_text(value: str) -> str:
    if value is None:
        return ""
    value = value.strip()
    value = re.sub(r"\s+", " ", value)
    return value


def parse_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_int(value: str, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def valid_date(value: str) -> str:
    value = clean_text(value)
    if not value:
        return ""
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return value
    except ValueError:
        return ""


def extract_genres(raw_genres: str):
    text = f" {clean_text(raw_genres).lower()} "
    matched = []
    for genre in sorted(KNOWN_GENRES, key=len, reverse=True):
        pattern = rf"\b{re.escape(genre.lower())}\b"
        if re.search(pattern, text):
            matched.append(genre)
    return matched


def read_csv(path: Path):
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows, fieldnames):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def clean_movies(data_dir: Path, out_dir: Path):
    rows = read_csv(data_dir / "movies.csv")
    cleaned = []
    movie_ids = set()
    movie_genres = []

    for row in rows:
        movie_id = clean_text(row.get("id", ""))
        title = clean_text(row.get("title", ""))
        if not movie_id or not title:
            continue
        if movie_id in movie_ids:
            continue

        movie_ids.add(movie_id)
        genres = extract_genres(row.get("genres", ""))
        director = clean_text(row.get("director", ""))

        cleaned_row = {
            "movie_id": movie_id,
            "title": title,
            "original_title": clean_text(row.get("original_title", "")),
            "original_language": clean_text(row.get("original_language", "")).lower(),
            "status": clean_text(row.get("status", "")),
            "overview": clean_text(row.get("overview", "")),
            "release_date": valid_date(row.get("release_date", "")),
            "runtime": parse_float(row.get("runtime", ""), 0.0),
            "budget": parse_int(row.get("budget", ""), 0),
            "revenue": parse_int(row.get("revenue", ""), 0),
            "vote_average": parse_float(row.get("vote_average", ""), 0.0),
            "vote_count": parse_int(row.get("vote_count", ""), 0),
            "popularity": parse_float(row.get("popularity", ""), 0.0),
            "director": director,
            "genres_list": "|".join(genres),
        }
        cleaned.append(cleaned_row)

        for g in genres:
            movie_genres.append({"movie_id": movie_id, "genre": g})

    write_csv(
        out_dir / "movies_clean.csv",
        cleaned,
        [
            "movie_id",
            "title",
            "original_title",
            "original_language",
            "status",
            "overview",
            "release_date",
            "runtime",
            "budget",
            "revenue",
            "vote_average",
            "vote_count",
            "popularity",
            "director",
            "genres_list",
        ],
    )

    write_csv(out_dir / "movie_genres_clean.csv", movie_genres, ["movie_id", "genre"])
    return movie_ids, cleaned, movie_genres


def clean_users(data_dir: Path, out_dir: Path):
    rows = read_csv(data_dir / "users.csv")
    cleaned = []
    user_ids = set()

    for row in rows:
        user_id = clean_text(row.get("user_id", ""))
        name = clean_text(row.get("name", ""))
        if not user_id or not name:
            continue
        if user_id in user_ids:
            continue

        user_ids.add(user_id)

        age = parse_int(row.get("age", ""), 18)
        age = max(13, min(100, age))

        premium = clean_text(row.get("premium", "false")).lower()
        premium = "true" if premium in {"true", "1", "yes"} else "false"

        preferred_genres = "|".join([g for g in row.get("preferred_genres", "").split("|") if clean_text(g)])
        favorite_languages = "|".join(
            [lang.strip().lower() for lang in row.get("favorite_languages", "").split("|") if clean_text(lang)]
        )

        cleaned.append(
            {
                "user_id": user_id,
                "name": name,
                "age": age,
                "country": clean_text(row.get("country", "")),
                "register_date": valid_date(row.get("register_date", "")),
                "premium": premium,
                "favorite_languages": favorite_languages,
                "preferred_genres": preferred_genres,
            }
        )

    write_csv(
        out_dir / "users_clean.csv",
        cleaned,
        [
            "user_id",
            "name",
            "age",
            "country",
            "register_date",
            "premium",
            "favorite_languages",
            "preferred_genres",
        ],
    )
    return user_ids, cleaned


def clean_views(data_dir: Path, out_dir: Path, user_ids, movie_ids):
    rows = read_csv(data_dir / "user_views.csv")
    cleaned = []
    seen = set()

    for row in rows:
        user_id = clean_text(row.get("user_id", ""))
        movie_id = clean_text(row.get("movie_id", ""))
        view_date = valid_date(row.get("view_date", ""))
        device = clean_text(row.get("device", "")).lower()
        progress = parse_float(row.get("progress", ""), 0.0)

        if user_id not in user_ids or movie_id not in movie_ids:
            continue
        if not view_date:
            continue

        if device not in VALID_DEVICES:
            device = "desktop"

        progress = max(0.0, min(1.0, progress))

        row_key = (user_id, movie_id, view_date)
        if row_key in seen:
            continue
        seen.add(row_key)

        cleaned.append(
            {
                "user_id": user_id,
                "movie_id": movie_id,
                "view_date": view_date,
                "device": device,
                "progress": round(progress, 2),
            }
        )

    write_csv(out_dir / "user_views_clean.csv", cleaned, ["user_id", "movie_id", "view_date", "device", "progress"])
    return cleaned


def clean_ratings(data_dir: Path, out_dir: Path, user_ids, movie_ids):
    rows = read_csv(data_dir / "user_ratings.csv")
    cleaned = []
    seen = set()

    for row in rows:
        user_id = clean_text(row.get("user_id", ""))
        movie_id = clean_text(row.get("movie_id", ""))
        rating_date = valid_date(row.get("rating_date", ""))

        if user_id not in user_ids or movie_id not in movie_ids:
            continue
        if not rating_date:
            continue

        rating = parse_float(row.get("rating", ""), 0.0)
        if rating <= 0:
            continue

        rating = max(1.0, min(10.0, rating))
        comment = clean_text(row.get("comment", "")) or "Sin comentario"

        row_key = (user_id, movie_id, rating_date)
        if row_key in seen:
            continue
        seen.add(row_key)

        cleaned.append(
            {
                "user_id": user_id,
                "movie_id": movie_id,
                "rating": round(rating, 1),
                "rating_date": rating_date,
                "comment": comment,
            }
        )

    write_csv(
        out_dir / "user_ratings_clean.csv",
        cleaned,
        ["user_id", "movie_id", "rating", "rating_date", "comment"],
    )
    return cleaned


def clean_preferences(data_dir: Path, out_dir: Path, user_ids):
    rows = read_csv(data_dir / "user_preferences.csv")
    cleaned = []
    seen = set()

    known_lower = {g.lower(): g for g in KNOWN_GENRES}

    for row in rows:
        user_id = clean_text(row.get("user_id", ""))
        genre_raw = clean_text(row.get("genre", ""))
        last_updated = valid_date(row.get("last_updated", ""))

        if user_id not in user_ids or not genre_raw or not last_updated:
            continue

        genre = known_lower.get(genre_raw.lower(), genre_raw.title())
        weight = parse_float(row.get("weight", ""), 0.0)
        weight = max(0.0, min(1.0, weight))

        source = clean_text(row.get("source", "")).lower()
        if source not in {"onboarding", "behavior", "hybrid"}:
            source = "behavior"

        row_key = (user_id, genre)
        if row_key in seen:
            continue
        seen.add(row_key)

        cleaned.append(
            {
                "user_id": user_id,
                "genre": genre,
                "weight": round(weight, 4),
                "last_updated": last_updated,
                "source": source,
            }
        )

    write_csv(
        out_dir / "user_preferences_clean.csv",
        cleaned,
        ["user_id", "genre", "weight", "last_updated", "source"],
    )
    return cleaned


def clean_friendships(data_dir: Path, out_dir: Path, user_ids):
    rows = read_csv(data_dir / "user_friendships.csv")
    cleaned = []
    seen = set()

    for row in rows:
        u1 = clean_text(row.get("user_id_1", ""))
        u2 = clean_text(row.get("user_id_2", ""))
        since_date = valid_date(row.get("since_date", ""))

        if u1 not in user_ids or u2 not in user_ids:
            continue
        if u1 == u2:
            continue
        if not since_date:
            continue

        pair = tuple(sorted((u1, u2)))
        if pair in seen:
            continue
        seen.add(pair)

        closeness = parse_float(row.get("closeness", ""), 0.5)
        closeness = max(0.0, min(1.0, closeness))
        interactions = max(0, parse_int(row.get("interactions", ""), 0))

        cleaned.append(
            {
                "user_id_1": pair[0],
                "user_id_2": pair[1],
                "since_date": since_date,
                "closeness": round(closeness, 2),
                "interactions": interactions,
            }
        )

    write_csv(
        out_dir / "user_friendships_clean.csv",
        cleaned,
        ["user_id_1", "user_id_2", "since_date", "closeness", "interactions"],
    )
    return cleaned


def main():
    repo_root = Path(__file__).resolve().parents[1]
    data_dir = repo_root / "data"
    out_dir = data_dir / "clean"
    out_dir.mkdir(parents=True, exist_ok=True)

    movie_ids, movies_clean, movie_genres_clean = clean_movies(data_dir, out_dir)
    user_ids, users_clean = clean_users(data_dir, out_dir)

    views_clean = clean_views(data_dir, out_dir, user_ids, movie_ids)
    ratings_clean = clean_ratings(data_dir, out_dir, user_ids, movie_ids)
    preferences_clean = clean_preferences(data_dir, out_dir, user_ids)
    friendships_clean = clean_friendships(data_dir, out_dir, user_ids)

    print("Cleaning completed:")
    print(f"- movies_clean.csv: {len(movies_clean)}")
    print(f"- movie_genres_clean.csv: {len(movie_genres_clean)}")
    print(f"- users_clean.csv: {len(users_clean)}")
    print(f"- user_views_clean.csv: {len(views_clean)}")
    print(f"- user_ratings_clean.csv: {len(ratings_clean)}")
    print(f"- user_preferences_clean.csv: {len(preferences_clean)}")
    print(f"- user_friendships_clean.csv: {len(friendships_clean)}")


if __name__ == "__main__":
    main()
