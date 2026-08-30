import { useEffect, useState } from "react";
import { createBeatType, listBeatTypes } from "../api.js";

export default function BeatTypes() {
  const [items, setItems] = useState([]);
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  async function refresh() {
    setItems(await listBeatTypes());
  }

  useEffect(() => {
    refresh().catch((err) => setError(err.message));
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    try {
      await createBeatType(name);
      setName("");
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section>
      <h2>Tipos de Beat</h2>
      <form className="row" onSubmit={handleSubmit}>
        <input
          placeholder="alerta, error, estado…"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <button type="submit">Dar de alta</button>
      </form>
      {error ? <p className="error">{error}</p> : null}
      <ul className="list">
        {items.map((item) => (
          <li key={item.id}>{item.name}</li>
        ))}
        {!items.length ? <li className="muted">Aún no hay tipos.</li> : null}
      </ul>
    </section>
  );
}
