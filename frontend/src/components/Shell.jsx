import { NavLink } from "react-router-dom";
import { logout } from "../api.js";

export default function Shell({ session, onSession, children }) {
  async function handleLogout() {
    try {
      await logout();
    } finally {
      onSession(null);
    }
  }

  const company = session.current_company;

  return (
    <div className="wrap">
      <header className="top">
        <div>
          <p className="eyebrow">BeatLab</p>
          <h1>Hub{company ? ` · ${company.name}` : ""}</h1>
        </div>
        <nav>
          <NavLink to="/" end>
            Salud
          </NavLink>
          <NavLink to="/systems">Systems</NavLink>
          <NavLink to="/operators">Operators</NavLink>
          <NavLink to="/tipos">Tipos</NavLink>
          <NavLink to="/beats">Beats</NavLink>
          <button type="button" onClick={handleLogout}>
            Salir
          </button>
        </nav>
      </header>
      <main>{children}</main>
    </div>
  );
}
