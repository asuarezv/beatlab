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
  const isOperator = session.role === "operator";

  return (
    <div className="wrap">
      <header className="top">
        <div>
          <p className="eyebrow">BeatLab</p>
          <h1>Hub{company ? ` · ${company.name}` : ""}</h1>
          {!isOperator && company?.trial_active ? (
            <p className="muted">
              Demo · {company.trial_days_left} día
              {company.trial_days_left === 1 ? "" : "s"} ·{" "}
              {Number(company.beats_remaining || 0).toLocaleString("es-MX")} Beats
              restantes
            </p>
          ) : null}
        </div>
        <nav>
          {isOperator ? (
            <>
              <NavLink to="/" end>
                Monitoreo
              </NavLink>
              <NavLink to="/perfil">Perfil</NavLink>
            </>
          ) : (
            <>
              <NavLink to="/" end>
                Salud
              </NavLink>
              <NavLink to="/systems">Systems</NavLink>
              <NavLink to="/operators">Operators</NavLink>
              <NavLink to="/tipos">Tipos</NavLink>
              <NavLink to="/beats">Beats</NavLink>
              <NavLink to="/glosario">Glosario</NavLink>
              <NavLink to="/perfil">Perfil</NavLink>
            </>
          )}
          <button type="button" onClick={handleLogout}>
            Salir
          </button>
        </nav>
      </header>
      <main>{children}</main>
    </div>
  );
}
