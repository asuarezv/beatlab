import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import BeatCharts from "../components/BeatCharts.jsx";
import { fetchBeatStats, fetchSalud } from "../api.js";

function formatNumber(value) {
  return Number(value || 0).toLocaleString("es-MX");
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        let data;
        try {
          data = await fetchSalud();
        } catch (err) {
          if (err.status !== 403) throw err;
          data = await fetchBeatStats();
        }
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
  if (!stats) return <p className="muted">Cargando salud…</p>;

  const hasUsage = stats.systems !== undefined;
  const trialNote = stats.trial_active
    ? `Demo · ${stats.trial_days_left} día${stats.trial_days_left === 1 ? "" : "s"}`
    : hasUsage
      ? "Demo terminado"
      : "";

  return (
    <section>
      {trialNote ? <p className="muted">{trialNote}</p> : null}
      {hasUsage ? (
        <div className="grid">
          <article className="card">
            <p className="eyebrow">Systems</p>
            <strong>{stats.systems}</strong>
          </article>
          <article className="card">
            <p className="eyebrow">Operators</p>
            <strong>{stats.operators}</strong>
          </article>
          <article className="card">
            <p className="eyebrow">Tipos de Beat</p>
            <strong>{stats.types}</strong>
          </article>
          <Link className="card card-link" to="/consumo">
            <p className="eyebrow">Beats</p>
            <strong>{formatNumber(stats.beats_remaining)}</strong>
            <span className="muted">
              restantes de {formatNumber(stats.beats_included)}
            </span>
          </Link>
        </div>
      ) : null}
      <div className="panel charts-panel">
        <h3>Beats por tipo</h3>
        <BeatCharts stats={stats} />
      </div>
    </section>
  );
}
