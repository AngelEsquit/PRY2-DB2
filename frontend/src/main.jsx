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

function movieDirector(movie) {
  return movie.director || movie.properties?.director || movie.properties?.director_name || '';
}

function movieLanguage(movie) {
  return movie.original_language || movie.properties?.original_language || '';
}

function movieYear(movie) {
  const rawDate = movie.release_date || movie.properties?.release_date || '';
  if (!rawDate) return '';
  if (typeof rawDate === 'string') return rawDate.slice(0, 4);
  if (typeof rawDate === 'object') return String(rawDate._Date__year || rawDate.year || '').slice(0, 4);
  return String(rawDate).slice(0, 4);
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
    ['admin', 'Admin', FolderPlus],
  ];

  return (
    <>
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
    </>
  );
}


function NodePropertyManager() {
  const [selectorLabel, setSelectorLabel] = useState('Movie');
  const [selectorIdProperty, setSelectorIdProperty] = useState('movie_id');
  const [selectorIdValue, setSelectorIdValue] = useState('');
  const [manyLabel, setManyLabel] = useState('Movie');
  const [onePropertiesText, setOnePropertiesText] = useState(() => ['{', '  "status": "featured"', '}'].join('\n'));
  const [manyFiltersText, setManyFiltersText] = useState(() => ['{', '  "genre": "Drama"', '}'].join('\n'));
  const [manyPropertiesText, setManyPropertiesText] = useState(() => ['{', '  "reviewed_by": "admin"', '}'].join('\n'));
  const [deleteKeysText, setDeleteKeysText] = useState('["status"]');
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState('');
  const [result, setResult] = useState('');

  const parseJsonInput = (text, fallback) => {
    const trimmed = text.trim();
    if (!trimmed) return fallback;
    try {
      return JSON.parse(trimmed);
    } catch {
      throw new Error('JSON inválido');
    }
  };

  const parseValueInput = (text) => {
    const trimmed = text.trim();
    if (!trimmed) return '';
    try {
      return JSON.parse(trimmed);
    } catch {
      return text;
    }
  };

  const buildSelector = () => ({
    label: selectorLabel.trim(),
    id_property: selectorIdProperty.trim(),
    id_value: parseValueInput(selectorIdValue),
  });

  const runAction = async (action) => {
    setBusy(action);
    setStatus('Ejecutando operación...');
    try {
      const selector = buildSelector();
      let response = null;

      if (action === 'add-one') {
        response = await api.addNodePropertiesOne({ selector, properties: parseJsonInput(onePropertiesText, {}) });
      } else if (action === 'update-one') {
        response = await api.updateNodePropertiesOne({ selector, properties: parseJsonInput(onePropertiesText, {}) });
      } else if (action === 'delete-one') {
        response = await api.deleteNodePropertiesOne({ selector, property_keys: parseJsonInput(deleteKeysText, []) });
      } else if (action === 'add-many') {
        response = await api.addNodePropertiesMany({
          label: manyLabel.trim(),
          filters: parseJsonInput(manyFiltersText, {}),
          properties: parseJsonInput(manyPropertiesText, {}),
        });
      } else if (action === 'update-many') {
        response = await api.updateNodePropertiesMany({
          label: manyLabel.trim(),
          filters: parseJsonInput(manyFiltersText, {}),
          properties: parseJsonInput(manyPropertiesText, {}),
        });
      } else if (action === 'delete-many') {
        response = await api.deleteNodePropertiesMany({
          label: manyLabel.trim(),
          filters: parseJsonInput(manyFiltersText, {}),
          property_keys: parseJsonInput(deleteKeysText, []),
        });
      }

      setResult(JSON.stringify(response, null, 2));
      setStatus('Operación completada');
    } catch (err) {
      setStatus(err.message);
    } finally {
      setBusy('');
    }
  };

  const cardStyle = {
    padding: '16px',
    borderRadius: '12px',
    border: '1px solid rgba(233, 237, 245, 0.08)',
    background: 'rgba(233, 237, 245, 0.03)',
    display: 'grid',
    gap: '12px',
  };

  const fieldStyle = {
    width: '100%',
    minHeight: '38px',
    padding: '10px 12px',
    borderRadius: '10px',
    border: '1px solid rgba(233, 237, 245, 0.12)',
    background: 'rgba(13, 17, 23, 0.8)',
    color: '#e9edf5',
  };

  const textAreaStyle = {
    ...fieldStyle,
    minHeight: '92px',
    resize: 'vertical',
    fontFamily: 'monospace',
    fontSize: '12px',
  };

  const actionButtonStyle = (tone) => ({
    minHeight: '38px',
    padding: '0 12px',
    borderRadius: '10px',
    cursor: busy ? 'not-allowed' : 'pointer',
    opacity: busy ? 0.65 : 1,
    border: tone.border,
    background: tone.background,
    color: tone.color,
    fontWeight: '600',
  });

  return (
    <section className="panel" style={{marginTop: '18px'}}>
      <h2>Gestión de propiedades en nodos</h2>
      <p>Define un nodo por label e identificador, o filtra varios nodos al mismo tiempo. Las propiedades y filtros se escriben en JSON.</p>

      <div style={{display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '16px', marginTop: '18px'}}>
        <div style={cardStyle}>
          <h3>Nodo individual</h3>
          <input
            value={selectorLabel}
            onChange={(event) => setSelectorLabel(event.target.value)}
            placeholder="Label"
            style={fieldStyle}
          />
          <input
            value={selectorIdProperty}
            onChange={(event) => setSelectorIdProperty(event.target.value)}
            placeholder="Propiedad identificadora"
            style={fieldStyle}
          />
          <input
            value={selectorIdValue}
            onChange={(event) => setSelectorIdValue(event.target.value)}
            placeholder="Valor del identificador"
            style={fieldStyle}
          />
          <textarea
            value={onePropertiesText}
            onChange={(event) => setOnePropertiesText(event.target.value)}
            placeholder={`{\n  "campo": "valor"\n}`}
            style={textAreaStyle}
          />
          <textarea
            value={deleteKeysText}
            onChange={(event) => setDeleteKeysText(event.target.value)}
            placeholder='["campo_a_eliminar"]'
            style={textAreaStyle}
          />
          <div style={{display: 'flex', flexWrap: 'wrap', gap: '8px'}}>
            <button type="button" onClick={() => runAction('add-one')} disabled={!!busy} style={actionButtonStyle({border: '1px solid rgba(111, 182, 255, 0.22)', background: 'rgba(111, 182, 255, 0.1)', color: '#6fb6ff'})}>
              Agregar propiedades
            </button>
            <button type="button" onClick={() => runAction('update-one')} disabled={!!busy} style={actionButtonStyle({border: '1px solid rgba(229, 166, 84, 0.22)', background: 'rgba(229, 166, 84, 0.1)', color: '#e5a654'})}>
              Actualizar propiedades
            </button>
            <button type="button" onClick={() => runAction('delete-one')} disabled={!!busy} style={actionButtonStyle({border: '1px solid rgba(255, 143, 143, 0.22)', background: 'rgba(255, 143, 143, 0.1)', color: '#ff8f8f'})}>
              Eliminar propiedades
            </button>
          </div>
        </div>

        <div style={cardStyle}>
          <h3>Múltiples nodos</h3>
          <input
            value={manyLabel}
            onChange={(event) => setManyLabel(event.target.value)}
            placeholder="Label"
            style={fieldStyle}
          />
          <textarea
            value={manyFiltersText}
            onChange={(event) => setManyFiltersText(event.target.value)}
            placeholder='{"campo": "valor"}'
            style={textAreaStyle}
          />
          <textarea
            value={manyPropertiesText}
            onChange={(event) => setManyPropertiesText(event.target.value)}
            placeholder='{"campo": "valor"}'
            style={textAreaStyle}
          />
          <textarea
            value={deleteKeysText}
            onChange={(event) => setDeleteKeysText(event.target.value)}
            placeholder='["campo_a_eliminar"]'
            style={textAreaStyle}
          />
          <div style={{display: 'flex', flexWrap: 'wrap', gap: '8px'}}>
            <button type="button" onClick={() => runAction('add-many')} disabled={!!busy} style={actionButtonStyle({border: '1px solid rgba(111, 182, 255, 0.22)', background: 'rgba(111, 182, 255, 0.1)', color: '#6fb6ff'})}>
              Agregar propiedades
            </button>
            <button type="button" onClick={() => runAction('update-many')} disabled={!!busy} style={actionButtonStyle({border: '1px solid rgba(229, 166, 84, 0.22)', background: 'rgba(229, 166, 84, 0.1)', color: '#e5a654'})}>
              Actualizar propiedades
            </button>
            <button type="button" onClick={() => runAction('delete-many')} disabled={!!busy} style={actionButtonStyle({border: '1px solid rgba(255, 143, 143, 0.22)', background: 'rgba(255, 143, 143, 0.1)', color: '#ff8f8f'})}>
              Eliminar propiedades
            </button>
          </div>
        </div>
      </div>

      <div style={{marginTop: '16px', display: 'grid', gap: '10px'}}>
        <p style={{fontSize: '12px', color: '#9aa7bd'}}>Consejo: para el valor del identificador puedes escribir texto plano, un número o JSON válido. Ejemplo: <span style={{fontFamily: 'monospace'}}>123</span> o <span style={{fontFamily: 'monospace'}}>"M001"</span>.</p>
        <pre style={{
          margin: 0,
          padding: '14px',
          borderRadius: '10px',
          background: 'rgba(13, 17, 23, 0.6)',
          border: '1px solid rgba(233, 237, 245, 0.08)',
          fontSize: '12px',
          color: '#9aa7bd',
          overflow: 'auto',
          minHeight: '120px',
          whiteSpace: 'pre-wrap',
        }}>
          {result || 'Aquí aparecerá la respuesta del backend.'}
        </pre>
        <p style={{fontSize: '12px', color: status.includes('completada') ? '#42d392' : '#9aa7bd', margin: 0}}>{status || 'Listo para ejecutar operaciones.'}</p>
      </div>
    </section>
  );
}
function AdminUpload() {
  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const [files, setFiles] = useState(null);
  const [dataDir, setDataDir] = useState('');
  const [log, setLog] = useState('');

  const prepareLoader = async (isDemo = false) => {
    const msg = isDemo ? 'Preparando datos de demostración...' : 'Preparando carga automática...';
    setLog(msg);
    try {
      const url = new URL(`${API_URL}/prepare-loader`);
      if (isDemo) url.searchParams.append('use_demo', 'true');
      const res = await fetch(url, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Error al preparar carga');
      setDataDir(data.data_dir || '');
      const lines = ['✓ Archivos copiados: ' + (data.copied || []).map((s) => s.split('/').pop()).join(', ')];
      (data.rubric_nodes || []).forEach((node) => {
        lines.push(`${node.operation}: ${node.labels?.join(':') || ''}`);
        lines.push(`Propiedades: ${Object.keys(node.properties || {}).slice(0, 6).join(', ')}`);
      });
      setLog(lines.join('\n'));
    } catch (err) {
      setLog('✗ Error: ' + err.message);
    }
  };

  const upload = async () => {
    if (!files || files.length === 0) return;
    const fd = new FormData();
    for (let i = 0; i < files.length; i++) fd.append('files', files[i]);
    setLog('Uploading...');
    try {
      const res = await fetch(`${API_URL}/upload-csv`, { method: 'POST', body: fd });
      const data = await res.json();
      setDataDir(data.data_dir || '');
      setLog('Uploaded: ' + (data.saved || []).map((s) => s.split('/').pop()).join(', '));
    } catch (err) {
      setLog('Upload failed: ' + err.message);
    }
  };

  const runLoader = async (dry = true) => {
    if (!dataDir) return setLog('No data_dir to run loader against. Prepare or upload first.');
    setLog(dry ? 'Running dry-run...' : 'Running real load...');
    const fd = new FormData();
    fd.append('data_dir', dataDir);
    fd.append('dry_run', dry ? 'true' : 'false');
    try {
      const res = await fetch(`${API_URL}/run-loader`, { method: 'POST', body: fd });
      const data = await res.json();
      setLog('Loader finished. stdout:\n' + (data.stdout || '') + '\nstderr:\n' + (data.stderr || ''));
    } catch (err) {
      setLog('Loader failed: ' + err.message);
    }
  };

  const clearDemoData = async () => {
    if (!window.confirm('¿Eliminar datos de demo de Neo4j?')) return;
    setLog('Limpiando datos de demo...');
    try {
      const res = await fetch(`${API_URL}/clear-loader-data?use_demo=true`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Error al limpiar');
      setLog('✓ ' + (data.message || 'Datos eliminados correctamente'));
    } catch (err) {
      setLog('✗ Error: ' + err.message);
    }
  };



  return (
    <section className="panel">
      <h2>Administración - Carga de datos</h2>
      <p>Prepara y carga datos a Neo4j directamente desde el frontend.</p>
      
      <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '24px'}}>
        <div style={{
          padding: '16px',
          borderRadius: '12px',
          border: '1px solid rgba(111, 182, 255, 0.3)',
          background: 'rgba(111, 182, 255, 0.05)'
        }}>
          <h3 style={{fontSize: '14px', fontWeight: '600', color: '#6fb6ff', marginBottom: '12px'}}>Demostración Rápida</h3>
          <p style={{fontSize: '13px', color: '#9aa7bd', marginBottom: '12px'}}>Carga datos mínimos y agrega nodos de rúbrica: un User simple, un Reviewer con 2 labels y una Collection curada con CREATE/MERGE.</p>
          <button onClick={() => prepareLoader(true)} style={{
            width: '100%',
            minHeight: '40px',
            padding: '0 16px',
            border: 'none',
            borderRadius: '10px',
            background: '#6fb6ff',
            color: '#0d1117',
            fontWeight: '600',
            cursor: 'pointer',
            transition: 'background 0.2s ease'
          }} onMouseOver={(e) => e.target.style.background = '#5ba3e8'} onMouseOut={(e) => e.target.style.background = '#6fb6ff'}>
            → Usar Datos de Demo
          </button>
        </div>
        
        <div style={{
          padding: '16px',
          borderRadius: '12px',
          border: '1px solid rgba(229, 166, 84, 0.3)',
          background: 'rgba(229, 166, 84, 0.05)'
        }}>
          <h3 style={{fontSize: '14px', fontWeight: '600', color: '#e5a654', marginBottom: '12px'}}>Datos Completos</h3>
          <p style={{fontSize: '13px', color: '#9aa7bd', marginBottom: '12px'}}>Copia todos los CSVs limpios del directorio data/clean/ a un directorio temporal.</p>
          <button onClick={() => prepareLoader(false)} style={{
            width: '100%',
            minHeight: '40px',
            padding: '0 16px',
            border: 'none',
            borderRadius: '10px',
            background: '#e5a654',
            color: '#0d1117',
            fontWeight: '600',
            cursor: 'pointer',
            transition: 'background 0.2s ease'
          }} onMouseOver={(e) => e.target.style.background = '#d4934a'} onMouseOut={(e) => e.target.style.background = '#e5a654'}>
            → Preparar Carga Completa
          </button>
        </div>
      </div>
      
      <div style={{marginTop: '28px', paddingTop: '20px', borderTop: '1px solid rgba(233, 237, 245, 0.08)'}}>
        <p style={{fontSize: '12px', color: '#9aa7bd', marginBottom: '12px', fontWeight: '500'}}>Subida manual (opcional):</p>
        <div className="uploadRow">
          <input type="file" multiple accept=".csv" onChange={(e) => setFiles(e.target.files)} style={{flex: 1}} />
          <button onClick={upload} style={{
            padding: '0 16px',
            border: '1px solid rgba(233, 237, 245, 0.1)',
            borderRadius: '10px',
            background: 'rgba(233, 237, 245, 0.05)',
            color: '#e9edf5',
            fontWeight: '500',
            cursor: 'pointer',
            transition: 'background 0.2s ease'
          }} onMouseOver={(e) => e.target.style.background = 'rgba(111, 182, 255, 0.15)'} onMouseOut={(e) => e.target.style.background = 'rgba(233, 237, 245, 0.05)'}>
            Subir CSV
          </button>
        </div>
      </div>
      
      <div style={{marginTop: '24px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px'}}>
        <button onClick={() => runLoader(true)} style={{
          minHeight: '42px',
          padding: '0 16px',
          border: '1px solid rgba(111, 182, 255, 0.2)',
          borderRadius: '10px',
          background: 'rgba(111, 182, 255, 0.08)',
          color: '#6fb6ff',
          fontWeight: '600',
          cursor: 'pointer',
          transition: 'all 0.2s ease'
        }} onMouseOver={(e) => {e.target.style.background = 'rgba(111, 182, 255, 0.15)'; e.target.style.borderColor = 'rgba(111, 182, 255, 0.4)'}} onMouseOut={(e) => {e.target.style.background = 'rgba(111, 182, 255, 0.08)'; e.target.style.borderColor = 'rgba(111, 182, 255, 0.2)'}}>
          ◇ Ejecutar Dry-Run
        </button>
        <button onClick={() => runLoader(false)} style={{
          minHeight: '42px',
          padding: '0 16px',
          border: '1px solid rgba(229, 166, 84, 0.2)',
          borderRadius: '10px',
          background: 'rgba(229, 166, 84, 0.12)',
          color: '#e5a654',
          fontWeight: '600',
          cursor: 'pointer',
          transition: 'all 0.2s ease'
        }} onMouseOver={(e) => {e.target.style.background = 'rgba(229, 166, 84, 0.2)'; e.target.style.borderColor = 'rgba(229, 166, 84, 0.4)'}} onMouseOut={(e) => {e.target.style.background = 'rgba(229, 166, 84, 0.12)'; e.target.style.borderColor = 'rgba(229, 166, 84, 0.2)'}}>
          ✓ Ejecutar Carga Real
        </button>
      </div>
      
      <div style={{marginTop: '20px'}}>
        <button onClick={clearDemoData} style={{
          width: '100%',
          minHeight: '38px',
          padding: '0 16px',
          border: '1px solid rgba(255, 112, 112, 0.2)',
          borderRadius: '10px',
          background: 'rgba(255, 112, 112, 0.08)',
          color: '#ff8f8f',
          fontWeight: '500',
          fontSize: '13px',
          cursor: 'pointer',
          transition: 'all 0.2s ease'
        }} onMouseOver={(e) => {e.target.style.background = 'rgba(255, 112, 112, 0.15)'; e.target.style.borderColor = 'rgba(255, 112, 112, 0.3)'}} onMouseOut={(e) => {e.target.style.background = 'rgba(255, 112, 112, 0.08)'; e.target.style.borderColor = 'rgba(255, 112, 112, 0.2)'}}>
          🗑️ Limpiar Datos de Demo
        </button>
      </div>

      
      <pre style={{
        marginTop: '20px',
        padding: '14px',
        borderRadius: '10px',
        background: 'rgba(13, 17, 23, 0.6)',
        border: '1px solid rgba(233, 237, 245, 0.08)',
        fontSize: '12px',
        color: '#9aa7bd',
        overflow: 'auto',
        maxHeight: '240px',
        fontFamily: 'monospace'
      }} className="log">{log}</pre>
      
      {dataDir && <p style={{marginTop: '12px', fontSize: '12px', color: '#9aa7bd'}}>
        <span style={{color: '#42d392'}}>✓</span> Data dir: <code style={{color: '#6fb6ff', fontFamily: 'monospace', fontSize: '11px'}}>{dataDir}</code>
      </p>}
      
      <p style={{marginTop: '16px', fontSize: '12px', color: '#9aa7bd', fontStyle: 'italic'}}>
        Nota: Asegúrate de que el backend tenga las variables de entorno de Neo4j en `.env` para carga real.
      </p>
      <NodePropertyManager />
    </section>
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

function MovieCard({ movie, onOpen, onLike, onSave, liked = false, saved = false }) {
  const rating = Number(movieRating(movie) || 0).toFixed(1);
  const director = movieDirector(movie);
  const year = movieYear(movie);
  const [likedState, setLikedState] = useState(liked);
  const [savedState, setSavedState] = useState(saved);
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState(null);

  useEffect(() => setLikedState(liked), [liked]);
  useEffect(() => setSavedState(saved), [saved]);

  const flash = (message) => {
    setStatus(message);
    window.clearTimeout(MovieCard._statusTimer);
    MovieCard._statusTimer = window.setTimeout(() => setStatus(''), 1600);
  };

  const toggleLike = async () => {
    if (busy) return;
    const nextValue = !likedState;
    setBusy('like');
    setLikedState(nextValue);
    flash(nextValue ? 'Añadido a Me gusta' : 'Quitado de Me gusta');
    try {
      await onLike(movieId(movie), likedState);
    } catch (error) {
      setLikedState(!nextValue);
      flash('No se pudo actualizar');
    } finally {
      setBusy(null);
    }
  };

  const toggleSave = async () => {
    if (busy) return;
    const nextValue = !savedState;
    setBusy('save');
    setSavedState(nextValue);
    flash(nextValue ? 'Añadida a watchlist' : 'Quitada de watchlist');
    try {
      await onSave(movieId(movie), savedState);
    } catch (error) {
      setSavedState(!nextValue);
      flash('No se pudo actualizar');
    } finally {
      setBusy(null);
    }
  };

  return (
    <article className="movieCard">
      <div className="poster">
        <Film size={32} />
        <span>{rating}</span>
      </div>
      <div className="movieBody">
        <h3>{movieTitle(movie)}</h3>
        {(director || year) && (
          <p style={{margin: '0 0 8px', fontSize: '12px', color: '#9aa7bd'}}>
            {director && <span>Dir. {director}</span>}
            {director && year && <span> · </span>}
            {year && <span>{year}</span>}
          </p>
        )}
        <p>{metric(movie.overview || movie.properties?.overview, 'Sin descripcion disponible.')}</p>
        <div className="chips">
          {movieGenres(movie).slice(0, 3).map((genre) => <span key={genre}>{genre}</span>)}
        </div>
        {status && <p style={{margin: '10px 0 0', fontSize: '11px', color: '#9aa7bd'}}>{status}</p>}
      </div>
      <div className="actions">
        <button onClick={() => onOpen(movieId(movie))}>Ver detalle</button>
        <button
          aria-label={likedState ? 'Quitar like' : 'Agregar like'}
          onClick={toggleLike}
          disabled={busy === 'like'}
          style={{
            background: likedState ? 'rgba(255, 143, 143, 0.16)' : 'rgba(233, 237, 245, 0.04)',
            borderColor: likedState ? 'rgba(255, 143, 143, 0.35)' : 'rgba(233, 237, 245, 0.08)',
            color: likedState ? '#ff8f8f' : '#e9edf5',
          }}
        >
          <Heart size={16} fill={likedState ? 'currentColor' : 'none'} />
        </button>
        <button
          aria-label={savedState ? 'Quitar de watchlist' : 'Guardar en watchlist'}
          onClick={toggleSave}
          disabled={busy === 'save'}
          style={{
            background: savedState ? 'rgba(111, 182, 255, 0.16)' : 'rgba(233, 237, 245, 0.04)',
            borderColor: savedState ? 'rgba(111, 182, 255, 0.35)' : 'rgba(233, 237, 245, 0.08)',
            color: savedState ? '#6fb6ff' : '#e9edf5',
          }}
        >
          <Bookmark size={16} fill={savedState ? 'currentColor' : 'none'} />
        </button>
      </div>
    </article>
  );
}

function Discover({ movies, likes, watchlist, setSelectedMovie, currentUser, refreshLists }) {
  const [query, setQuery] = useState('');
  const [genre, setGenre] = useState('');
  const [directorQuery, setDirectorQuery] = useState('');
  const [language, setLanguage] = useState('');
  const [year, setYear] = useState('');
  const [minRating, setMinRating] = useState('');
  const [results, setResults] = useState([]);
  const [totalResults, setTotalResults] = useState(0);
  const [directorSuggestions, setDirectorSuggestions] = useState([]);
  const [directorOpen, setDirectorOpen] = useState(false);
  const [loadingResults, setLoadingResults] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const availableGenres = useMemo(
    () => [...new Set(movies.flatMap((movie) => movieGenres(movie)).filter(Boolean))].sort(),
    [movies],
  );
  const availableLanguages = useMemo(
    () => [...new Set(movies.map((movie) => movieLanguage(movie)).filter(Boolean))].sort(),
    [movies],
  );
  const availableYears = useMemo(
    () => [...new Set(movies.map((movie) => movieYear(movie)).filter(Boolean))].sort((a, b) => Number(b) - Number(a)),
    [movies],
  );
  const likedIds = useMemo(() => new Set(likes.map((item) => movieId(item)).filter(Boolean)), [likes]);
  const savedIds = useMemo(() => new Set(watchlist.map((item) => movieId(item)).filter(Boolean)), [watchlist]);

  const clearFilters = () => {
    setQuery('');
    setGenre('');
    setDirectorQuery('');
    setLanguage('');
    setYear('');
    setMinRating('');
    setDirectorSuggestions([]);
    setDirectorOpen(false);
    setPage(1);
  };

  const controlStyle = {
    minHeight: '38px',
    padding: '0 12px',
    borderRadius: '10px',
    border: '1px solid rgba(233, 237, 245, 0.12)',
    background: 'rgba(13, 17, 23, 0.92)',
    color: '#e9edf5',
    outline: 'none',
    fontSize: '13px',
  };

  useEffect(() => {
    setPage(1);
  }, [query, genre, directorQuery, language, year, minRating, pageSize]);

  useEffect(() => {
    const skip = (page - 1) * pageSize;
    const timer = window.setTimeout(() => {
      setLoadingResults(true);
      api.searchMoviesAdvanced({
        query,
        genre,
        director: directorQuery,
        language,
        year,
        min_rating: minRating === '' ? null : Number(minRating),
        skip,
        limit: pageSize,
      })
        .then((response) => {
          setResults(response.items || []);
          setTotalResults(Number(response.count || 0));
        })
        .catch(() => {
          setResults([]);
          setTotalResults(0);
        })
        .finally(() => setLoadingResults(false));
    }, 250);

    return () => window.clearTimeout(timer);
  }, [page, pageSize, query, genre, directorQuery, language, year, minRating]);

  useEffect(() => {
    const text = directorQuery.trim();
    if (text.length < 2) {
      setDirectorSuggestions([]);
      return;
    }

    const timer = window.setTimeout(() => {
      api.suggestDirectors(text, 6)
        .then((response) => setDirectorSuggestions(response.items || []))
        .catch(() => setDirectorSuggestions([]));
    }, 200);

    return () => window.clearTimeout(timer);
  }, [directorQuery]);

  const like = async (id) => {
    if (likedIds.has(id)) {
      await api.removeLike(currentUser, id);
    } else {
      await api.addLike(currentUser, id);
    }
    refreshLists();
  };
  const save = async (id) => {
    if (savedIds.has(id)) {
      await api.removeWatchlist(currentUser, id);
    } else {
      await api.addWatchlist(currentUser, id);
    }
    refreshLists();
  };

  return (
    <section className="panel">
      <div className="panelHead">
        <div>
          <h2>Catalogo de peliculas</h2>
          <p>{loadingResults ? 'Buscando...' : `${totalResults} resultados disponibles`}</p>
        </div>
      </div>
      <div style={{display: 'grid', gap: '12px', marginBottom: '18px'}}>
        <div className="search">
          <Search size={18} />
          <input placeholder="Buscar por título u overview..." value={query} onChange={(event) => setQuery(event.target.value)} />
        </div>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
          gap: '10px',
        }}>
          <select className="filterSelect" value={genre} onChange={(event) => setGenre(event.target.value)} style={controlStyle}>
            <option value="">Todos los géneros</option>
            {availableGenres.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
          <div style={{position: 'relative'}}>
            <input
              value={directorQuery}
              onChange={(event) => {
                setDirectorQuery(event.target.value);
                setDirectorOpen(true);
              }}
              onFocus={() => setDirectorOpen(true)}
              onBlur={() => window.setTimeout(() => setDirectorOpen(false), 150)}
              placeholder="Filtrar por director"
              style={{...controlStyle, width: '100%'}}
            />
            {directorOpen && directorSuggestions.length > 0 && (
              <div style={{
                position: 'absolute',
                top: 'calc(100% + 6px)',
                left: 0,
                right: 0,
                zIndex: 20,
                background: '#111827',
                border: '1px solid rgba(233, 237, 245, 0.12)',
                borderRadius: '12px',
                overflow: 'hidden',
                boxShadow: '0 18px 40px rgba(0, 0, 0, 0.35)',
                maxHeight: '220px',
                overflowY: 'auto',
              }}>
                {directorSuggestions.map((item) => (
                  <button
                    key={item.director_id}
                    type="button"
                    onMouseDown={(event) => {
                      event.preventDefault();
                      setDirectorQuery(item.name || item.director_id);
                      setDirectorOpen(false);
                    }}
                    style={{
                      display: 'block',
                      width: '100%',
                      textAlign: 'left',
                      padding: '10px 12px',
                      background: 'transparent',
                      color: '#e9edf5',
                      border: 'none',
                      borderBottom: '1px solid rgba(233, 237, 245, 0.06)',
                      cursor: 'pointer',
                    }}
                  >
                    <b style={{display: 'block', fontSize: '13px'}}>{item.name || item.director_id}</b>
                    <small style={{color: '#9aa7bd'}}>{item.director_id}</small>
                  </button>
                ))}
              </div>
            )}
            {directorOpen && directorQuery.trim().length >= 2 && directorSuggestions.length === 0 && (
              <div style={{
                position: 'absolute',
                top: 'calc(100% + 6px)',
                left: 0,
                right: 0,
                zIndex: 20,
                background: '#111827',
                border: '1px solid rgba(233, 237, 245, 0.12)',
                borderRadius: '12px',
                padding: '10px 12px',
                color: '#9aa7bd',
                fontSize: '12px',
              }}>
                Sin coincidencias
              </div>
            )}
          </div>
          <select className="filterSelect" value={language} onChange={(event) => setLanguage(event.target.value)} style={controlStyle}>
            <option value="">Todos los idiomas</option>
            {availableLanguages.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
          <select className="filterSelect" value={year} onChange={(event) => setYear(event.target.value)} style={controlStyle}>
            <option value="">Todos los años</option>
            {availableYears.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
          <input
            type="number"
            min="0"
            max="10"
            step="0.1"
            placeholder="Rating mínimo"
            value={minRating}
            onChange={(event) => setMinRating(event.target.value)}
            style={controlStyle}
          />
          <select value={pageSize} onChange={(event) => setPageSize(Number(event.target.value))} style={controlStyle}>
            <option value={12}>12 por página</option>
            <option value={20}>20 por página</option>
            <option value={40}>40 por página</option>
            <option value={80}>80 por página</option>
          </select>
          <button
            type="button"
            onClick={clearFilters}
            style={{
              minHeight: '38px',
              padding: '0 12px',
              borderRadius: '10px',
              border: '1px solid rgba(111, 182, 255, 0.18)',
              background: 'rgba(111, 182, 255, 0.08)',
              color: '#6fb6ff',
              fontWeight: '600',
              cursor: 'pointer',
            }}
          >
            Limpiar filtros
          </button>
        </div>
      </div>
      <div className="grid">
        {results.map((movie) => (
          <MovieCard
            key={movieId(movie)}
            movie={movie}
            onOpen={setSelectedMovie}
            onLike={like}
            onSave={save}
            liked={likedIds.has(movieId(movie))}
            saved={savedIds.has(movieId(movie))}
          />
        ))}
      </div>
      <div style={{
        marginTop: '18px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '12px',
        flexWrap: 'wrap',
      }}>
        <p style={{margin: 0, color: '#9aa7bd', fontSize: '12px'}}>
          Página {page} de {Math.max(1, Math.ceil(totalResults / pageSize))}
        </p>
        <div style={{display: 'flex', gap: '8px'}}>
          <button
            type="button"
            onClick={() => setPage((value) => Math.max(1, value - 1))}
            disabled={page <= 1 || loadingResults}
            style={{
              minHeight: '36px',
              padding: '0 14px',
              borderRadius: '10px',
              border: '1px solid rgba(233, 237, 245, 0.12)',
              background: 'rgba(233, 237, 245, 0.05)',
              color: '#e9edf5',
              cursor: page <= 1 || loadingResults ? 'not-allowed' : 'pointer',
              opacity: page <= 1 || loadingResults ? 0.5 : 1,
            }}
          >
            Anterior
          </button>
          <button
            type="button"
            onClick={() => setPage((value) => value + 1)}
            disabled={page >= Math.ceil(totalResults / pageSize) || loadingResults}
            style={{
              minHeight: '36px',
              padding: '0 14px',
              borderRadius: '10px',
              border: '1px solid rgba(111, 182, 255, 0.18)',
              background: 'rgba(111, 182, 255, 0.08)',
              color: '#6fb6ff',
              cursor: page >= Math.ceil(totalResults / pageSize) || loadingResults ? 'not-allowed' : 'pointer',
              opacity: page >= Math.ceil(totalResults / pageSize) || loadingResults ? 0.5 : 1,
            }}
          >
            Siguiente
          </button>
        </div>
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

function Library({ likes, watchlist, collections, movies, currentUser, reload }) {
  const [name, setName] = useState('');
  const [selectedCollectionId, setSelectedCollectionId] = useState('');
  const [movieQuery, setMovieQuery] = useState('');
  const [movieToAdd, setMovieToAdd] = useState('');
  const [collectionsExpanded, setCollectionsExpanded] = useState(false);

  useEffect(() => {
    if (!selectedCollectionId && collections.length > 0) {
      setSelectedCollectionId(collections[0].collection_id);
    }
  }, [collections, selectedCollectionId]);

  const selectedCollection = useMemo(
    () => collections.find((collection) => collection.collection_id === selectedCollectionId) || null,
    [collections, selectedCollectionId],
  );
  const likedIds = useMemo(() => new Set(likes.map((item) => movieId(item)).filter(Boolean)), [likes]);

  const filteredMovies = useMemo(() => {
    const text = movieQuery.trim().toLowerCase();
    return movies
      .filter((movie) => !text || movieTitle(movie).toLowerCase().includes(text))
      .slice(0, 25);
  }, [movies, movieQuery]);

  const create = async () => {
    if (!name.trim()) return;
    await api.createCollection(currentUser, { name, description: 'Coleccion creada desde el frontend' });
    setName('');
    reload();
  };

  const addMovie = async () => {
    if (!selectedCollectionId || !movieToAdd) return;
    await api.addMovieToCollection(currentUser, selectedCollectionId, movieToAdd);
    setMovieToAdd('');
    setMovieQuery('');
    reload();
  };

  const removeMovie = async (movieIdValue) => {
    if (!selectedCollectionId || !movieIdValue) return;
    await api.removeMovieFromCollection(currentUser, selectedCollectionId, movieIdValue);
    reload();
  };

  const toggleFavorite = async (movieIdValue) => {
    if (!movieIdValue) return;
    if (likedIds.has(movieIdValue)) {
      await api.removeLike(currentUser, movieIdValue);
    } else {
      await api.addLike(currentUser, movieIdValue);
    }
    reload();
  };

  return (
    <section className="panel library">
      <h2>Biblioteca</h2>
      <div className="columns">
        <List title="Likes" items={likes} empty="Aun no tienes likes." />
        <List title="Watchlist" items={watchlist} empty="Aun no guardas peliculas." />
        <div className="list">
          <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px'}}>
            <h3 style={{margin: 0}}>Colecciones</h3>
            <button
              type="button"
              onClick={() => setCollectionsExpanded((value) => !value)}
              style={{
                minHeight: '32px',
                padding: '0 10px',
                borderRadius: '10px',
                border: '1px solid rgba(233, 237, 245, 0.12)',
                background: 'rgba(233, 237, 245, 0.05)',
                color: '#e9edf5',
                cursor: 'pointer',
                fontSize: '12px',
              }}
            >
              {collectionsExpanded ? 'Ocultar lista' : 'Ver lista'}
            </button>
          </div>
          <div className="create">
            <input placeholder="Nueva coleccion" value={name} onChange={(event) => setName(event.target.value)} />
            <button onClick={create}><FolderPlus size={16} />Crear</button>
          </div>
          {!collectionsExpanded ? (
            <div style={{marginTop: '12px', padding: '12px', borderRadius: '12px', background: 'rgba(233, 237, 245, 0.04)', border: '1px solid rgba(233, 237, 245, 0.08)'}}>
              <b style={{display: 'block', marginBottom: '4px'}}>Mostrando solo la colección activa</b>
              <small style={{color: '#9aa7bd'}}>
                {selectedCollection ? `${selectedCollection.name} · ${selectedCollection.movie_count} películas` : `${collections.length} colecciones disponibles`}
              </small>
            </div>
          ) : (
            <div style={{display: 'grid', gap: '8px', marginTop: '12px', maxHeight: '320px', overflowY: 'auto', paddingRight: '4px'}}>
              {collections.map((collection) => (
                <button
                  type="button"
                  key={collection.collection_id}
                  onClick={() => setSelectedCollectionId(collection.collection_id)}
                  style={{
                    textAlign: 'left',
                    padding: '12px',
                    borderRadius: '12px',
                    border: selectedCollectionId === collection.collection_id ? '1px solid rgba(111, 182, 255, 0.35)' : '1px solid rgba(233, 237, 245, 0.08)',
                    background: selectedCollectionId === collection.collection_id ? 'rgba(111, 182, 255, 0.08)' : 'rgba(13, 17, 23, 0.42)',
                    color: '#e9edf5',
                    cursor: 'pointer',
                  }}
                >
                  <b style={{display: 'block'}}>{collection.name}</b>
                  <small style={{color: '#9aa7bd'}}>{collection.movie_count} peliculas</small>
                  <div style={{marginTop: '8px', display: 'flex', gap: '6px', flexWrap: 'wrap'}}>
                    {(collection.movies || []).slice(0, 3).map((movie) => (
                      <span key={movie.movie_id} style={{fontSize: '11px', padding: '3px 8px', borderRadius: '999px', background: 'rgba(233, 237, 245, 0.06)', color: '#9aa7bd'}}>
                        {movie.title}
                      </span>
                    ))}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="list wide">
          <h3>Detalle de colección</h3>
          {!selectedCollection ? (
            <p className="muted">Selecciona una colección para ver su contenido.</p>
          ) : (
            <>
              <div style={{display: 'grid', gap: '8px', marginBottom: '14px'}}>
                <b>{selectedCollection.name}</b>
                <small style={{color: '#9aa7bd'}}>{selectedCollection.description || 'Sin descripción.'}</small>
                <small style={{color: '#9aa7bd'}}>{selectedCollection.movie_count} películas dentro</small>
              </div>
              <div style={{display: 'grid', gap: '10px', marginBottom: '16px'}}>
                <input
                  placeholder="Buscar película para agregar"
                  value={movieQuery}
                  onChange={(event) => setMovieQuery(event.target.value)}
                  style={{padding: '10px 12px', borderRadius: '10px', border: '1px solid rgba(233, 237, 245, 0.12)', background: 'rgba(13, 17, 23, 0.8)', color: '#e9edf5'}}
                />
                <select
                  value={movieToAdd}
                  onChange={(event) => setMovieToAdd(event.target.value)}
                  style={{padding: '10px 12px', borderRadius: '10px', border: '1px solid rgba(233, 237, 245, 0.12)', background: 'rgba(13, 17, 23, 0.8)', color: '#e9edf5'}}
                >
                  <option value="">Selecciona una película</option>
                  {filteredMovies.map((movie) => (
                    <option key={movieId(movie)} value={movieId(movie)}>{movieTitle(movie)}</option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={addMovie}
                  disabled={!movieToAdd}
                  style={{
                    minHeight: '38px',
                    borderRadius: '10px',
                    border: '1px solid rgba(111, 182, 255, 0.18)',
                    background: 'rgba(111, 182, 255, 0.08)',
                    color: '#6fb6ff',
                    cursor: !movieToAdd ? 'not-allowed' : 'pointer',
                    opacity: !movieToAdd ? 0.5 : 1,
                  }}
                >
                  Agregar a esta colección
                </button>
              </div>
              <div style={{display: 'grid', gap: '8px'}}>
                {(selectedCollection.movies || []).length === 0 ? (
                  <p className="muted">Todavía no tiene películas.</p>
                ) : (
                  (selectedCollection.movies || []).map((movie) => (
                    <div key={movie.movie_id} style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px', padding: '10px 12px', borderRadius: '10px', background: 'rgba(233, 237, 245, 0.04)', border: '1px solid rgba(233, 237, 245, 0.06)'}}>
                      <div style={{flex: 1, minWidth: 0}}>
                        <b>{movie.title}</b>
                        <div style={{fontSize: '11px', color: '#9aa7bd'}}>{movie.movie_id}</div>
                      </div>
                      <div style={{display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0}}>
                        <button
                          type="button"
                          aria-label={likedIds.has(movie.movie_id) ? 'Quitar de favoritos' : 'Marcar como favorito'}
                          onClick={() => toggleFavorite(movie.movie_id)}
                          style={{
                            minHeight: '32px',
                            padding: '0 10px',
                            borderRadius: '10px',
                            border: likedIds.has(movie.movie_id) ? '1px solid rgba(255, 143, 143, 0.28)' : '1px solid rgba(233, 237, 245, 0.08)',
                            background: likedIds.has(movie.movie_id) ? 'rgba(255, 143, 143, 0.12)' : 'rgba(233, 237, 245, 0.04)',
                            color: likedIds.has(movie.movie_id) ? '#ff8f8f' : '#e9edf5',
                            cursor: 'pointer',
                          }}
                        >
                          <Heart size={15} fill={likedIds.has(movie.movie_id) ? 'currentColor' : 'none'} />
                        </button>
                        <button
                          type="button"
                          onClick={() => removeMovie(movie.movie_id)}
                          style={{
                            minHeight: '32px',
                            padding: '0 10px',
                            borderRadius: '10px',
                            border: '1px solid rgba(255, 143, 143, 0.2)',
                            background: 'rgba(255, 143, 143, 0.08)',
                            color: '#ff8f8f',
                            cursor: 'pointer',
                          }}
                        >
                          Quitar
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </>
          )}
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
              <span>{movieYear(movie) || metric(movie.release_date)}</span>
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
          <Discover movies={movies} likes={likes} watchlist={watchlist} setSelectedMovie={setSelectedMovie} currentUser={currentUser} refreshLists={reloadUser} />
        )}
        {active === 'recommendations' && (
          <Recommendations currentUser={currentUser} recommendations={recommendations} setSelectedMovie={setSelectedMovie} refreshLists={reloadUser} />
        )}
        {active === 'library' && (
          <Library likes={likes} watchlist={watchlist} collections={collections} movies={movies} currentUser={currentUser} reload={reloadUser} />
        )}
        {active === 'social' && <Social friends={friends} profile={profile} />}
        {active === 'admin' && <AdminUpload />}
      </main>
      <Modal movieId={selectedMovie} close={() => setSelectedMovie(null)} />
    </>
  );
}

createRoot(document.getElementById('root')).render(<App />);
