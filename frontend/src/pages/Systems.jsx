import { useEffect, useState } from "react";
import { createSystem, listSystems } from "../api.js";

export default function Systems() {
  const [items, setItems] = useState([]);
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  async function refresh() {
    setItems(await listSystems());
  }

  useEffect(() => {
    refresh().catch((err) => setError(err.message));
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    try {
      await createSystem(name);
      setName("");
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section>
      <h2>Systems</h2>
      <form className="row" onSubmit={handleSubmit}>
        <input
          placeholder="nombre del sistema"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <button type="submit">Dar de alta</button>
      </form>
      {error ? <p className="error">{error}</p> : null}
      <ul className="list">
        {items.map((item) => (
          <li key={item.id}>
            {item.name} {item.is_active ? "" : "(inactivo)"}
          </li>
        ))}
        {!items.length ? <li className="muted">Aún no hay Systems.</li> : null}
      </ul>
    </section>
  );
}
