import { useEffect, useState } from "react";
import { listBeats, listBeatTypes, listOperators, listSystems } from "../api.js";

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [systems, operators, types, beats] = await Promise.all([
          listSystems(),
          listOperators(),
          listBeatTypes(),
          listBeats(),
        ]);
        if (!cancelled) {
          setStats({
            systems: systems.length,
            operators: operators.length,
            types: types.length,
            beats: beats.length,
          });
        }
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

  return (
    <section className="grid">
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
      <article className="card">
        <p className="eyebrow">Beats</p>
        <strong>{stats.beats}</strong>
      </article>
    </section>
  );
}
