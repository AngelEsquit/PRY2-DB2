const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || 'Error al consultar el backend');
  }
  return response.json();
}

export const api = {
  health: () => request('/health'),
  searchMovies: (limit = 120) => request('/nodes/search', { method: 'POST', body: JSON.stringify({ label: 'Movie', limit }) }),
  searchUsers: (limit = 20) => request('/nodes/search', { method: 'POST', body: JSON.stringify({ label: 'User', limit }) }),
  searchMoviesAdvanced: (filters = {}) => request('/movies/search', { method: 'POST', body: JSON.stringify(filters) }),
  suggestDirectors: (query = '', limit = 8) => request(`/directors/suggest?q=${encodeURIComponent(query)}&limit=${limit}`),
  movie: (id) => request(`/movies/${id}`),
  similarMovies: (id) => request(`/movies/${id}/similar?top_k=8`),
  recommendations: (userId) => request(`/recommendations/${userId}?top_k=12&include_reasons=true`),
  profile: (userId) => request(`/users/${userId}/recommendation-profile`),
  watchlist: (userId) => request(`/users/${userId}/watchlist`),
  likes: (userId) => request(`/users/${userId}/likes`),
  collections: (userId) => request(`/users/${userId}/collections`),
  friends: (userId) => request(`/users/${userId}/friends`),
  addLike: (userId, movieId) => request(`/users/${userId}/likes?movie_id=${movieId}`, { method: 'POST' }),
  removeLike: (userId, movieId) => request(`/users/${userId}/likes/${movieId}`, { method: 'DELETE' }),
  addWatchlist: (userId, movieId) => request(`/users/${userId}/watchlist?movie_id=${movieId}`, { method: 'POST' }),
  removeWatchlist: (userId, movieId) => request(`/users/${userId}/watchlist/${movieId}`, { method: 'DELETE' }),
  createCollection: (userId, data) => request(`/users/${userId}/collections`, { method: 'POST', body: JSON.stringify(data) }),
  addMovieToCollection: (userId, collectionId, movieId) => request(`/users/${userId}/collections/${collectionId}/movies?movie_id=${movieId}`, { method: 'POST' }),
  removeMovieFromCollection: (userId, collectionId, movieId) => request(`/users/${userId}/collections/${collectionId}/movies/${movieId}`, { method: 'DELETE' }),
  addNodePropertiesOne: (payload) => request('/nodes/properties/add-one', { method: 'PATCH', body: JSON.stringify(payload) }),
  updateNodePropertiesOne: (payload) => request('/nodes/properties/update-one', { method: 'PATCH', body: JSON.stringify(payload) }),
  addNodePropertiesMany: (payload) => request('/nodes/properties/add-many', { method: 'PATCH', body: JSON.stringify(payload) }),
  updateNodePropertiesMany: (payload) => request('/nodes/properties/update-many', { method: 'PATCH', body: JSON.stringify(payload) }),
  deleteNodePropertiesOne: (payload) => request('/nodes/properties/delete-one', { method: 'DELETE', body: JSON.stringify(payload) }),
  deleteNodePropertiesMany: (payload) => request('/nodes/properties/delete-many', { method: 'DELETE', body: JSON.stringify(payload) }),
};
