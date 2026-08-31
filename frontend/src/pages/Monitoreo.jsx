import { useEffect, useState } from "react";
import BeatCharts from "../components/BeatCharts.jsx";
import { BeatMarks } from "../components/BeatIcons.jsx";
import { fetchBeatStats, listBeats, monitorWsUrl } from "../api.js";

const POLL_MS = 4000;

function formatWhen(value) {
  if (!value) return "";
  try {
    return new Date(value).toLocaleString("es-MX");
  } catch {
    return value;
  }
}

export default function Monitoreo() {
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState(null);
  const [live, setLive] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function refresh() {
      try {
        const [beats, nextStats] = await Promise.all([listBeats(), fetchBeatStats()]);
        if (!cancelled) {
          setItems(Array.isArray(beats) ? beats : beats.results || []);
          setStats(nextStats);
          setError("");
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }
    refresh();
    const id = setInterval(refresh, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  useEffect(() => {
    let closed = false;
    let socket;
    let retry;

    function connect() {
      if (closed) return;
      socket = new WebSocket(monitorWsUrl());
      socket.onopen = () => setLive(true);
      socket.onmessage = (event) => {
        let data;
        try {
          data = JSON.parse(event.data);
        } catch {
          return;
        }
        if (data.type === "beat" && data.beat) {
          setItems((prev) => {
            if (prev.some((item) => item.id === data.beat.id)) return prev;
            return [data.beat, ...prev];
          });
        }
      };
      socket.onerror = () => {};
      socket.onclose = () => {
        setLive(false);
        if (!closed) retry = setTimeout(connect, 3000);
      };
    }

    connect();
    return () => {
      closed = true;
      clearTimeout(retry);
      if (socket) socket.close();
    };
  }, []);

  return (
    <section>
      <h2>Monitoreo</h2>
      <p className="hint">
        Beats que te corresponden. {live ? "En vivo." : "Reconectando…"}
      </p>
      {error ? <p className="error">{error}</p> : null}
      <div className="panel charts-panel">
        <h3>Beats por tipo</h3>
        {stats ? <BeatCharts stats={stats} /> : <p className="muted">Cargando…</p>}
      </div>
      <div className="panel">
        <h3>Recibidos</h3>
        <ul className="list">
          {items.map((item) => (
            <li key={item.id} className="beat-item">
              <BeatMarks item={item} />
              <span>
                <strong>{item.title}</strong>
                <span className="muted">
                  {" "}
                  · {item.system_name} · {item.beat_type_name} ·{" "}
                  {item.severity_label || item.severity}
                </span>
                <span className="muted beat-when">{formatWhen(item.created_at)}</span>
              </span>
            </li>
          ))}
          {!items.length ? <li className="muted">Aún no hay Beats.</li> : null}
        </ul>
      </div>
    </section>
  );
}
