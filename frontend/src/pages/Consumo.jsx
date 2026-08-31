import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchSalud } from "../api.js";

function formatNumber(value) {
  return Number(value || 0).toLocaleString("es-MX");
}

export default function Consumo() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchSalud();
        if (!cancelled) setStats(data);
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) return <p className="error">{error}</p>;
  if (!stats) return <p className="muted">Cargando consumo…</p>;

  return (
    <section>
      <p className="eyebrow">Salud</p>
      <h2>Beats consumidos por tipo</h2>
      <p className="muted">
        {formatNumber(stats.beats_used)} usados · {formatNumber(stats.beats_remaining)}{" "}
        restantes de {formatNumber(stats.beats_included)}
      </p>
      <ul className="list">
        {stats.by_type.map((item) => (
          <li key={item.id} className="consumo-row">
            <span>
              {item.name}
              {item.severity_label ? (
                <span className={`sev-badge sev-${item.severity}`}>
                  {item.severity_label}
                </span>
              ) : null}
            </span>
            <strong>{formatNumber(item.consumed)}</strong>
          </li>
        ))}
        {!stats.by_type.length ? (
          <li className="muted">Aún no hay tipos de Beat.</li>
        ) : null}
      </ul>
      <p className="auth-switch">
        <Link to="/">Volver a Salud</Link>
      </p>
    </section>
  );
}
