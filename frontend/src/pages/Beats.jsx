import { useEffect, useState } from "react";
import { createBeat, listBeats, listBeatTypes, listSystems } from "../api.js";

export default function Beats() {
  const [items, setItems] = useState([]);
  const [systems, setSystems] = useState([]);
  const [types, setTypes] = useState([]);
  const [system, setSystem] = useState("");
  const [beatType, setBeatType] = useState("");
  const [title, setTitle] = useState("");
  const [error, setError] = useState("");

  async function refresh() {
    const [beats, nextSystems, nextTypes] = await Promise.all([
      listBeats(),
      listSystems(),
      listBeatTypes(),
    ]);
    setItems(beats);
    setSystems(nextSystems);
    setTypes(nextTypes);
    if (!system && nextSystems[0]) setSystem(String(nextSystems[0].id));
    if (!beatType && nextTypes[0]) setBeatType(String(nextTypes[0].id));
  }

  useEffect(() => {
    refresh().catch((err) => setError(err.message));
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    try {
      await createBeat({
        system: Number(system),
        beat_type: Number(beatType),
        title,
        payload: {},
      });
      setTitle("");
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section>
      <h2>Beats</h2>
      <form className="row" onSubmit={handleSubmit}>
        <select value={system} onChange={(e) => setSystem(e.target.value)} required>
          <option value="">System</option>
          {systems.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
        <select value={beatType} onChange={(e) => setBeatType(e.target.value)} required>
          <option value="">Tipo</option>
          {types.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
        <input
          placeholder="título"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
        <button type="submit">Registrar</button>
      </form>
      {error ? <p className="error">{error}</p> : null}
      <ul className="list">
        {items.map((item) => (
          <li key={item.id}>
            <strong>{item.title}</strong>
            <span className="muted">
              {" "}
              · {item.system_name} · {item.beat_type_name}
            </span>
          </li>
        ))}
        {!items.length ? <li className="muted">Aún no hay Beats.</li> : null}
      </ul>
    </section>
  );
}
