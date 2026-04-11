import argparse
import csv
import random
from datetime import date, datetime, timedelta
from pathlib import Path

FIRST_NAMES = [
    "Alex", "Sam", "Jordan", "Taylor", "Casey", "Morgan", "Riley", "Avery", "Cameron", "Emerson",
    "Diego", "Sofia", "Lucia", "Mateo", "Valeria", "Andres", "Elena", "Daniel", "Paula", "Nicolas",
    "Carla", "Jose", "Mariana", "Luis", "Fernanda", "Gabriel", "Camila", "Ricardo", "Natalia", "Hector",
]

LAST_NAMES = [
    "Lopez", "Garcia", "Rodriguez", "Martinez", "Hernandez", "Gonzalez", "Perez", "Sanchez", "Ramirez", "Torres",
    "Flores", "Rivera", "Gomez", "Diaz", "Vasquez", "Ramos", "Castillo", "Morales", "Ortega", "Mendoza",
]

COUNTRIES = [
    "Guatemala", "Mexico", "Colombia", "Argentina", "Chile", "Peru", "Spain", "United States", "Canada", "Brazil",
]

DEVICES = ["mobile", "desktop", "tablet", "tv"]

GENRES = [
    "Action", "Adventure", "Animation", "Comedy", "Crime", "Documentary", "Drama", "Family", "Fantasy",
    "History", "Horror", "Music", "Mystery", "Romance", "Science Fiction", "Thriller", "War", "Western",
]

COMMENTS = [
    "Me gusto bastante",
    "Buen ritmo",
    "Excelente recomendacion",
    "No era lo que esperaba",
    "Gran actuacion",
    "Visualmente increible",
    "Historia entretenida",
    "Final inesperado",
    "La volveria a ver",
    "Buena para recomendar",
]


def random_date_between(start: date, end: date) -> date:
    delta_days = (end - start).days
    if delta_days <= 0:
        return start
    return start + timedelta(days=random.randint(0, delta_days))


def safe_float(value: str, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def load_movies(movies_csv: Path):
    movies = []
    with movies_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            movie_id = (row.get("id") or "").strip()
            title = (row.get("title") or "").strip()
            if not movie_id or not title:
                continue
            movies.append(
                {
                    "id": movie_id,
                    "title": title,
                    "vote_average": safe_float(row.get("vote_average"), 6.0),
                    "popularity": safe_float(row.get("popularity"), 1.0),
                }
            )
    return movies


def build_movie_weights(movies):
    # More popular and better-rated movies become slightly more likely to be viewed.
    weights = []
    for m in movies:
        score = (m["vote_average"] + 1.0) * (1.0 + min(m["popularity"], 200.0) / 200.0)
        weights.append(max(score, 0.1))
    return weights


def generate_users(users_count: int):
    today = date.today()
    users = []
    for i in range(1, users_count + 1):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        name = f"{first} {last}"
        register_start = today - timedelta(days=365 * 4)
        register_date = random_date_between(register_start, today)

        pref_genres = random.sample(GENRES, k=random.randint(2, 4))
        pref_languages = random.sample(["en", "es", "fr", "de", "it", "pt", "ja", "ko"], k=random.randint(1, 3))

        users.append(
            {
                "user_id": f"U{i:05d}",
                "name": name,
                "age": random.randint(18, 65),
                "country": random.choice(COUNTRIES),
                "register_date": register_date.isoformat(),
                "premium": random.choice(["true", "false"]),
                "favorite_languages": "|".join(pref_languages),
                "preferred_genres": "|".join(pref_genres),
            }
        )
    return users


def generate_interactions(users, movies, movie_weights, min_views: int, max_views: int, rating_probability: float):
    today = date.today()
    views = []
    ratings = []
    preferences = []

    movie_ids = [m["id"] for m in movies]
    movie_by_id = {m["id"]: m for m in movies}

    for u in users:
        user_id = u["user_id"]
        register_date = datetime.strptime(u["register_date"], "%Y-%m-%d").date()

        k = random.randint(min_views, max_views)
        k = min(k, len(movie_ids))

        chosen = set()
        # Weighted sampling without replacement.
        while len(chosen) < k:
            picked = random.choices(movie_ids, weights=movie_weights, k=1)[0]
            chosen.add(picked)

        preferred = u["preferred_genres"].split("|")
        weight_parts = [random.random() for _ in preferred]
        total_weight = sum(weight_parts)
        for g, w in zip(preferred, weight_parts):
            preferences.append(
                {
                    "user_id": user_id,
                    "genre": g,
                    "weight": round(w / total_weight, 4),
                    "last_updated": random_date_between(register_date, today).isoformat(),
                    "source": random.choice(["onboarding", "behavior", "hybrid"]),
                }
            )

        for movie_id in chosen:
            view_date = random_date_between(register_date, today)
            progress = round(random.uniform(0.35, 1.0), 2)
            views.append(
                {
                    "user_id": user_id,
                    "movie_id": movie_id,
                    "view_date": view_date.isoformat(),
                    "device": random.choice(DEVICES),
                    "progress": progress,
                }
            )

            if random.random() <= rating_probability:
                base = movie_by_id[movie_id]["vote_average"]
                noise = random.uniform(-1.5, 1.5)
                score = max(1.0, min(10.0, round(base + noise, 1)))
                ratings.append(
                    {
                        "user_id": user_id,
                        "movie_id": movie_id,
                        "rating": score,
                        "rating_date": view_date.isoformat(),
                        "comment": random.choice(COMMENTS),
                    }
                )

    return views, ratings, preferences


def generate_friendships(users, min_friends: int = 2, max_friends: int = 8):
    today = date.today()
    friendships = []
    user_ids = [u["user_id"] for u in users]
    seen_pairs = set()

    for uid in user_ids:
        target = random.randint(min_friends, max_friends)
        candidates = random.sample(user_ids, k=min(len(user_ids), target * 3))

        added = 0
        for other in candidates:
            if other == uid:
                continue
            pair = tuple(sorted((uid, other)))
            if pair in seen_pairs:
                continue

            seen_pairs.add(pair)
            friendships.append(
                {
                    "user_id_1": pair[0],
                    "user_id_2": pair[1],
                    "since_date": random_date_between(today - timedelta(days=365 * 3), today).isoformat(),
                    "closeness": round(random.uniform(0.1, 1.0), 2),
                    "interactions": random.randint(1, 200),
                }
            )
            added += 1
            if added >= target:
                break

    return friendships


def write_csv(path: Path, rows, fieldnames):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic users and interactions based on movies.csv")
    parser.add_argument("--movies", default="data/movies.csv", help="Path to source movies CSV")
    parser.add_argument("--outdir", default="data", help="Output directory for generated CSV files")
    parser.add_argument("--users", type=int, default=2200, help="Number of users to generate")
    parser.add_argument("--min-views", type=int, default=8, help="Minimum views per user")
    parser.add_argument("--max-views", type=int, default=25, help="Maximum views per user")
    parser.add_argument("--rating-prob", type=float, default=0.55, help="Probability that a view has rating")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()

    random.seed(args.seed)

    movies_path = Path(args.movies)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    movies = load_movies(movies_path)
    if not movies:
        raise ValueError("No valid movies found. Verify the input CSV path and columns.")

    users = generate_users(args.users)
    weights = build_movie_weights(movies)
    views, ratings, preferences = generate_interactions(
        users, movies, weights, args.min_views, args.max_views, args.rating_prob
    )
    friendships = generate_friendships(users)

    write_csv(
        outdir / "users.csv",
        users,
        ["user_id", "name", "age", "country", "register_date", "premium", "favorite_languages", "preferred_genres"],
    )
    write_csv(
        outdir / "user_views.csv",
        views,
        ["user_id", "movie_id", "view_date", "device", "progress"],
    )
    write_csv(
        outdir / "user_ratings.csv",
        ratings,
        ["user_id", "movie_id", "rating", "rating_date", "comment"],
    )
    write_csv(
        outdir / "user_preferences.csv",
        preferences,
        ["user_id", "genre", "weight", "last_updated", "source"],
    )
    write_csv(
        outdir / "user_friendships.csv",
        friendships,
        ["user_id_1", "user_id_2", "since_date", "closeness", "interactions"],
    )

    print("Synthetic data generated successfully:")
    print(f"- users.csv: {len(users)}")
    print(f"- user_views.csv: {len(views)}")
    print(f"- user_ratings.csv: {len(ratings)}")
    print(f"- user_preferences.csv: {len(preferences)}")
    print(f"- user_friendships.csv: {len(friendships)}")


if __name__ == "__main__":
    main()
