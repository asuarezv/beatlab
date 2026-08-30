import { Link, NavLink, Outlet } from "react-router-dom";

function HeartbeatIcon() {
  return (
    <svg
      className="heartbeat"
      viewBox="0 0 24 24"
      width="22"
      height="22"
      aria-hidden="true"
    >
      <path
        fill="currentColor"
        d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"
      />
    </svg>
  );
}

export default function PublicShell({ children }) {
  const year = new Date().getFullYear();

  return (
    <div className="public-shell">
      <header className="public-header">
        <div className="public-header-inner">
          <Link to="/" className="public-brand">
            <img
              src="/brand/wordmark-on-dark.svg"
              alt="NynuSoft"
              width="140"
              height="26"
            />
            <HeartbeatIcon />
          </Link>
          <nav className="public-nav" aria-label="Principal">
            <NavLink to="/" end>
              Inicio
            </NavLink>
            <NavLink to="/registro">Crear mi Hub</NavLink>
            <NavLink to="/entrar">Entrar</NavLink>
          </nav>
        </div>
      </header>
      <div className="public-shell-body">{children ?? <Outlet />}</div>
      <footer className="public-footer">
        <div className="public-footer-inner">
          <p>
            <Link to="/">BeatLab</Link>
            {" · "}
            NynuSoft
          </p>
          <p className="muted">© {year}</p>
        </div>
      </footer>
    </div>
  );
}
