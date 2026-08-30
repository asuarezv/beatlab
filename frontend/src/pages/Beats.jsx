import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { issueSystemJwt, listBeats, listBeatTypes, listSystems } from "../api.js";
import ConfirmDialog from "../components/ConfirmDialog.jsx";

const PUBLIC_INGEST = "https://hub.nynusoft.com/api/ingest/beats/";
const POLL_MS = 4000;

function formatWhen(value) {
  if (!value) return "";
  try {
    return new Date(value).toLocaleString("es-MX");
  } catch {
    return value;
  }
}

export default function Beats() {
  const [items, setItems] = useState([]);
  const [systems, setSystems] = useState([]);
  const [types, setTypes] = useState([]);
  const [systemId, setSystemId] = useState("");
  const [token, setToken] = useState("");
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirmRotate, setConfirmRotate] = useState(false);

  const selected = systems.find((item) => String(item.id) === String(systemId));
  const exampleType = types[0]?.slug || "alerta";

  const curlExample = useMemo(
    () =>
      [
        `curl -X POST ${PUBLIC_INGEST} \\`,
        `  -H "Authorization: Bearer TU_JWT" \\`,
        `  -H "Content-Type: application/json" \\`,
        `  -d '{"type":"${exampleType}","title":"Cola de pagos recuperada"}'`,
      ].join("\n"),
    [exampleType],
  );

  const jsExample = useMemo(
    () =>
      [
        "await fetch('https://hub.nynusoft.com/api/ingest/beats/', {",
        "  method: 'POST',",
        "  headers: {",
        "    Authorization: 'Bearer TU_JWT',",
        "    'Content-Type': 'application/json',",
        "  },",
        `  body: JSON.stringify({ type: '${exampleType}', title: 'Cola de pagos recuperada' }),`,
        "});",
      ].join("\n"),
    [exampleType],
  );

  async function refreshList() {
    const beats = await listBeats();
    setItems(Array.isArray(beats) ? beats : beats.results || []);
  }

  async function refreshMeta() {
    const [nextSystems, nextTypes] = await Promise.all([listSystems(), listBeatTypes()]);
    setSystems(nextSystems);
    setTypes(nextTypes);
    setSystemId((current) => current || (nextSystems[0] ? String(nextSystems[0].id) : ""));
  }

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await Promise.all([refreshList(), refreshMeta()]);
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    })();
    const id = setInterval(() => {
      refreshList().catch(() => {});
    }, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  async function issueJwt() {
    if (!systemId) return;
    setError("");
    setCopied(false);
    setBusy(true);
    try {
      const data = await issueSystemJwt(Number(systemId));
      setToken(data.token);
      setConfirmRotate(false);
      await refreshMeta();
    } catch (err) {
      setError(err.message);
      setConfirmRotate(false);
    } finally {
      setBusy(false);
    }
  }

  function handleIssue() {
    if (!systemId) return;
    if (selected?.has_jwt) {
      setConfirmRotate(true);
      return;
    }
    issueJwt();
  }

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(token);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <section>
      <h2>Beats</h2>
      <p className="hint">
        Los Beats los envían tus Systems al Hub. Aquí creas el JWT, ves cómo
        implementarlo y revisas lo que ya llegó. Cada Beat se descuenta de la
        cuota y llega a los Operators en Monitor.
      </p>

      <div className="panel">
        <h3>JWT del System</h3>
        <p className="hint">
          El token se muestra una sola vez. Si lo pierdes, rótalo: el anterior
          deja de servir.
        </p>
        {systems.length ? (
          <div className="row">
            <select
              value={systemId}
              onChange={(e) => {
                setSystemId(e.target.value);
                setToken("");
                setCopied(false);
              }}
            >
              {systems.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                  {item.has_jwt ? " · JWT activo" : " · sin JWT"}
                </option>
              ))}
            </select>
            <button type="button" onClick={handleIssue} disabled={busy || !systemId}>
              {selected?.has_jwt ? "Rotar JWT" : "Crear JWT"}
            </button>
          </div>
        ) : (
          <p className="muted">
            Primero da de alta un <Link to="/systems">System</Link>.
          </p>
        )}
        {token ? (
          <div className="token-panel">
            <p className="ok">Cópialo ahora. No se vuelve a mostrar.</p>
            <pre className="code-block token-box">{token}</pre>
            <button type="button" className="secondary" onClick={handleCopy}>
              {copied ? "Copiado" : "Copiar JWT"}
            </button>
          </div>
        ) : null}
      </div>

      <div className="panel">
        <h3>Cómo enviar un Beat</h3>
        <p className="hint">
          Un Beat es una señal de salud de un System: siempre va autenticado con
          el JWT y clasificado con un tipo que hayas definido en el Hub.
        </p>
        <p className="hint">
          <strong>URL</strong> · <code>POST {PUBLIC_INGEST}</code>
        </p>
        <p className="hint">
          <strong>Header</strong> · <code>Authorization: Bearer TU_JWT</code>
        </p>
        <p className="hint">
          <strong>Cuerpo</strong> · <code>type</code> es el slug del tipo (
          {types.length
            ? types.map((item) => item.slug).join(", ")
            : "crea uno en Tipos"}
          ), <code>title</code> el mensaje. <code>payload</code> es opcional.
        </p>
        <pre className="code-block">{`{\n  "type": "${exampleType}",\n  "title": "Cola de pagos recuperada"\n}`}</pre>
        <p className="hint">
          <strong>Respuestas</strong> · 201 al registrarlo. 401 si el JWT falta o
          ya no vale. 403 si el System está inactivo o el Hub no admite más
          envíos. 409 si no quedan Beats en la cuota. 400 si el tipo no existe.
        </p>
        <p className="muted">curl</p>
        <pre className="code-block">{curlExample}</pre>
        <p className="muted">JavaScript</p>
        <pre className="code-block">{jsExample}</pre>
      </div>

      <div className="panel">
        <h3>Recibidos</h3>
        {error ? <p className="error">{error}</p> : null}
        <ul className="list">
          {items.map((item) => (
            <li key={item.id}>
              <strong>{item.title}</strong>
              <span className="muted">
                {" "}
                · {item.system_name} · {item.beat_type_name}
              </span>
              <span className="muted beat-when"> {formatWhen(item.created_at)}</span>
            </li>
          ))}
          {!items.length ? <li className="muted">Aún no hay Beats.</li> : null}
        </ul>
      </div>
      <ConfirmDialog
        open={confirmRotate}
        eyebrow="Beats"
        title="¿Rotar el JWT?"
        description="Al rotar, el JWT anterior deja de funcionar."
        acceptLabel={busy ? "Rotando…" : "Aceptar"}
        pending={busy}
        onAccept={issueJwt}
        onCancel={() => {
          if (!busy) setConfirmRotate(false);
        }}
      />
    </section>
  );
}
