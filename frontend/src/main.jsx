import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Bookmark,
  Clapperboard,
  Film,
  FolderPlus,
  Heart,
  LogIn,
  Search,
  Sparkles,
  UserRound,
  Users,
  WifiOff,
} from 'lucide-react';
import { api } from './services/api';
import './styles.css';

function metric(value, fallback = '-') {
  return value === null || value === undefined || value === '' ? fallback : value;
}

function movieId(movie) {
  return movie.movie_id || movie.properties?.movie_id;
}

function movieTitle(movie) {
  return movie.title || movie.properties?.title || movie.original_title || 'Pelicula sin titulo';
}

function movieRating(movie) {
  return movie.vote_average || movie.properties?.vote_average;
}

function movieGenres(movie) {
  return movie.genres || movie.properties?.genres || [];
}

function userId(user) {
  return user.user_id || user.properties?.user_id;
}

function userName(user) {
  return user.name || user.properties?.name || userId(user);
}

function Header({ active, setActive, status, currentUser, onLogout }) {
  const tabs = [
    ['discover', 'Descubrir', Film],
    ['recommendations', 'Recomendaciones', Sparkles],
    ['library', 'Biblioteca', Bookmark],
    ['social', 'Social', Users],
  ];

  return (
    <header className="header">
      <div className="brand">
        <div className="logo"><Clapperboard size={22} /></div>
        <div>
          <h1>CineGraph</h1>
          <p>Neo4j Social Recommender</p>
        </div>
      </div>

      <nav aria-label="Secciones principales">
        {tabs.map(([id, label, Icon]) => (
          <button key={id} onClick={() => setActive(id)} className={active === id ? 'active' : ''}>
            <Icon size={17} />
            <span>{label}</span>
          </button>
        ))}
      </nav>

      <div className="session">
        <span className={status === 'ok' ? 'pill ok' : 'pill'}>{status === 'ok' ? 'API conectada' : 'API sin conexion'}</span>
        <button className="ghostButton" onClick={onLogout}>
          <UserRound size={16} />
          <span>{currentUser}</span>
        </button>
      </div>
    </header>
  );
}

function LoginScreen({ users, status, selectedUser, setSelectedUser, onEnter }) {
  return (
    <main className="loginShell">
      <section className="loginPanel">
        <div className="loginCopy">
          <div className="logo large"><Clapperboard size={30} /></div>
          <span className="eyebrow">Proyecto Bases de Datos 2</span>
          <h1>CineGraph</h1>
          <p>Selecciona un usuario de Neo4j para ver recomendaciones, biblioteca y actividad social.</p>
          <span className={status === 'ok' ? 'pill ok' : 'pill error'}>
            {status === 'ok' ? 'Backend conectado' : 'Esperando backend'}
          </span>
        </div>

        <div className="loginCard">
          <h2>Entrar</h2>
          <label htmlFor="user-select">Usuario</label>
          <select id="user-select" value={selectedUser} onChange={(event) => setSelectedUser(event.target.value)}>
            {users.map((user) => (
              <option key={userId(user)} value={userId(user)}>
                {userName(user)}
              </option>
            ))}
          </select>
          <button onClick={onEnter} disabled={!selectedUser || status !== 'ok'}>
            <LogIn size={18} />
            Entrar al dashboard
          </button>
          {status !== 'ok' && (
            <p className="inlineError"><WifiOff size={16} /> Revisa que FastAPI este corriendo y que `VITE_API_URL` apunte al backend.</p>
          )}
        </div>
      </section>
    </main>
  );
}

function Hero({ users, currentUser, setCurrentUser }) {
  return (
    <section className="hero">
      <div>
        <span className="eyebrow">Dashboard</span>
        <h2>Peliculas, gustos y conexiones en Neo4j.</h2>
        <p>Explora el catalogo, guarda peliculas, crea colecciones y consulta recomendaciones basadas en el grafo.</p>
      </div>
      <div className="userCard">
        <UserRound size={24} />
        <label>Usuario activo</label>
        <select value={currentUser} onChange={(event) => setCurrentUser(event.target.value)}>
          {users.map((user) => (
            <option key={userId(user)} value={userId(user)}>
              {userName(user)}
            </option>
          ))}
        </select>
      </div>
    </section>
  );
}

function MovieCard({ movie, onOpen, onLike, onSave }) {
  const rating = Number(movieRating(movie) || 0).toFixed(1);

  return (
    <article className="movieCard">
      <div className="poster">
        <Film size={32} />
        <span>{rating}</span>
      </div>
      <div className="movieBody">
        <h3>{movieTitle(movie)}</h3>
        <p>{metric(movie.overview || movie.properties?.overview, 'Sin descripcion disponible.')}</p>
        <div className="chips">
          {movieGenres(movie).slice(0, 3).map((genre) => <span key={genre}>{genre}</span>)}
        </div>
      </div>
      <div className="actions">
        <button onClick={() => onOpen(movieId(movie))}>Ver detalle</button>
        <button aria-label="Agregar like" onClick={() => onLike(movieId(movie))}><Heart size={16} /></button>
        <button aria-label="Guardar en watchlist" onClick={() => onSave(movieId(movie))}><Bookmark size={16} /></button>
      </div>
    </article>
  );
}

function Discover({ movies, setSelectedMovie, currentUser, refreshLists }) {
  const [query, setQuery] = useState('');
  const filtered = useMemo(
    () => movies.filter((movie) => movieTitle(movie).toLowerCase().includes(query.toLowerCase())),
    [movies, query],
  );
  const like = async (id) => {
    await api.addLike(currentUser, id);
    refreshLists();
  };
  const save = async (id) => {
    await api.addWatchlist(currentUser, id);
    refreshLists();
  };

  return (
    <section className="panel">
      <div className="panelHead">
        <div>
          <h2>Catalogo de peliculas</h2>
          <p>{filtered.length} resultados disponibles</p>
        </div>
        <div className="search">
          <Search size={18} />
          <input placeholder="Buscar pelicula..." value={query} onChange={(event) => setQuery(event.target.value)} />
        </div>
      </div>
      <div className="grid">
        {filtered.map((movie) => (
          <MovieCard key={movieId(movie)} movie={movie} onOpen={setSelectedMovie} onLike={like} onSave={save} />
        ))}
      </div>
    </section>
  );
}

function Recommendations({ currentUser, recommendations, setSelectedMovie, refreshLists }) {
  return (
    <section className="panel">
      <div className="panelHead">
        <div>
          <h2>Recomendaciones</h2>
          <p>Basadas en similitud de usuarios, preferencias y contenido.</p>
        </div>
      </div>
      <div className="grid">
        {recommendations.map((movie) => (
          <MovieCard
            key={movie.movie_id}
            movie={movie}
            onOpen={setSelectedMovie}
            onLike={(id) => api.addLike(currentUser, id).then(refreshLists)}
            onSave={(id) => api.addWatchlist(currentUser, id).then(refreshLists)}
          />
        ))}
      </div>
    </section>
  );
}

function Library({ likes, watchlist, collections, currentUser, reload }) {
  const [name, setName] = useState('');
  const create = async () => {
    if (!name.trim()) return;
    await api.createCollection(currentUser, { name, description: 'Coleccion creada desde el frontend' });
    setName('');
    reload();
  };

  return (
    <section className="panel library">
      <h2>Biblioteca</h2>
      <div className="columns">
        <List title="Likes" items={likes} empty="Aun no tienes likes." />
        <List title="Watchlist" items={watchlist} empty="Aun no guardas peliculas." />
        <div className="list">
          <h3>Colecciones</h3>
          <div className="create">
            <input placeholder="Nueva coleccion" value={name} onChange={(event) => setName(event.target.value)} />
            <button onClick={create}><FolderPlus size={16} />Crear</button>
          </div>
          {collections.map((collection) => (
            <div className="row" key={collection.collection_id}>
              <b>{collection.name}</b>
              <small>{collection.movie_count} peliculas</small>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function List({ title, items, empty }) {
  return (
    <div className="list">
      <h3>{title}</h3>
      {items.length === 0 && <p className="muted">{empty}</p>}
      {items.map((item) => (
        <div className="row" key={item.movie_id || item.collection_id}>
          <b>{item.title || item.name}</b>
          <small>{metric(item.vote_average)} rating</small>
        </div>
      ))}
    </div>
  );
}

function Social({ friends, profile }) {
  return (
    <section className="panel">
      <h2>Perfil social</h2>
      <div className="stats">
        <div><b>{metric(profile?.total_likes, 0)}</b><span>Likes</span></div>
        <div><b>{metric(profile?.total_ratings, 0)}</b><span>Ratings</span></div>
        <div><b>{friends.length}</b><span>Amigos</span></div>
      </div>
      <div className="list wide">
        <h3>Amigos cercanos</h3>
        {friends.map((friend) => (
          <div className="row" key={friend.user_id}>
            <b>{friend.name || friend.user_id}</b>
            <small>Cercania: {metric(friend.closeness)}</small>
          </div>
        ))}
      </div>
    </section>
  );
}

function Modal({ movieId: selectedMovieId, close }) {
  const [movie, setMovie] = useState(null);
  const [similar, setSimilar] = useState([]);

  useEffect(() => {
    if (!selectedMovieId) return;
    api.movie(selectedMovieId).then(setMovie);
    api.similarMovies(selectedMovieId).then((response) => setSimilar(response.items || []));
  }, [selectedMovieId]);

  if (!selectedMovieId) return null;

  return (
    <div className="modalBackdrop" onClick={close}>
      <div className="modal" onClick={(event) => event.stopPropagation()}>
        <button className="x" onClick={close}>x</button>
        {!movie ? (
          <p>Cargando...</p>
        ) : (
          <>
            <h2>{movie.title}</h2>
            <p>{movie.overview || 'Sin descripcion.'}</p>
            <div className="facts">
              <span>Rating {metric(movie.vote_average)}</span>
              <span>{metric(movie.runtime)} min</span>
              <span>{metric(movie.release_date)}</span>
            </div>
            <h3>Peliculas similares</h3>
            <div className="miniGrid">
              {similar.map((item) => (
                <div key={item.movie_id} className="mini">
                  <b>{item.title}</b>
                  <small>Score {metric(item.score || item.similarity_score)}</small>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function App() {
  const [active, setActive] = useState('discover');
  const [status, setStatus] = useState('loading');
  const [movies, setMovies] = useState([]);
  const [users, setUsers] = useState([]);
  const [currentUser, setCurrentUser] = useState('');
  const [loggedIn, setLoggedIn] = useState(false);
  const [recommendations, setRecommendations] = useState([]);
  const [likes, setLikes] = useState([]);
  const [watchlist, setWatchlist] = useState([]);
  const [collections, setCollections] = useState([]);
  const [friends, setFriends] = useState([]);
  const [profile, setProfile] = useState(null);
  const [selectedMovie, setSelectedMovie] = useState(null);

  useEffect(() => {
    Promise.all([api.health(), api.searchMovies(), api.searchUsers()])
      .then(([health, movieResponse, userResponse]) => {
        const loadedUsers = userResponse.items || [];
        setStatus(health.status);
        setMovies(movieResponse.items || []);
        setUsers(loadedUsers);
        setCurrentUser(userId(loadedUsers[0]) || '');
      })
      .catch(() => setStatus('error'));
  }, []);

  const reloadUser = () => {
    if (!currentUser) return;
    Promise.all([
      api.recommendations(currentUser),
      api.likes(currentUser),
      api.watchlist(currentUser),
      api.collections(currentUser),
      api.friends(currentUser),
      api.profile(currentUser),
    ])
      .then(([recResponse, likeResponse, watchResponse, collectionResponse, friendResponse, profileResponse]) => {
        setRecommendations(recResponse.items || []);
        setLikes(likeResponse.items || []);
        setWatchlist(watchResponse.items || []);
        setCollections(collectionResponse.items || []);
        setFriends(friendResponse.items || []);
        setProfile(profileResponse);
      })
      .catch(console.error);
  };

  useEffect(reloadUser, [currentUser]);

  if (!loggedIn) {
    return (
      <LoginScreen
        users={users}
        status={status}
        selectedUser={currentUser}
        setSelectedUser={setCurrentUser}
        onEnter={() => setLoggedIn(true)}
      />
    );
  }

  return (
    <>
      <Header
        active={active}
        setActive={setActive}
        status={status}
        currentUser={currentUser}
        onLogout={() => setLoggedIn(false)}
      />
      <main>
        <Hero users={users} currentUser={currentUser} setCurrentUser={setCurrentUser} />
        {active === 'discover' && (
          <Discover movies={movies} setSelectedMovie={setSelectedMovie} currentUser={currentUser} refreshLists={reloadUser} />
        )}
        {active === 'recommendations' && (
          <Recommendations currentUser={currentUser} recommendations={recommendations} setSelectedMovie={setSelectedMovie} refreshLists={reloadUser} />
        )}
        {active === 'library' && (
          <Library likes={likes} watchlist={watchlist} collections={collections} currentUser={currentUser} reload={reloadUser} />
        )}
        {active === 'social' && <Social friends={friends} profile={profile} />}
      </main>
      <Modal movieId={selectedMovie} close={() => setSelectedMovie(null)} />
    </>
  );
}

createRoot(document.getElementById('root')).render(<App />);
