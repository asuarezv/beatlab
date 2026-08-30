import { useEffect, useState } from "react";
import { createOperator, listOperators } from "../api.js";
import { USERNAME_ERROR, isValidUsername } from "../fieldRules.js";

export default function Operators() {
  const [items, setItems] = useState([]);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function refresh() {
    setItems(await listOperators());
  }

  useEffect(() => {
    refresh().catch((err) => setError(err.message));
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();
    const user = username.trim();
    setUsername(user);
    if (!isValidUsername(user)) {
      setError(USERNAME_ERROR);
      return;
    }
    setError("");
    try {
      await createOperator(user, password);
      setUsername("");
      setPassword("");
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section>
      <h2>Operators</h2>
      <form className="row" onSubmit={handleSubmit}>
        <input
          placeholder="usuario"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />
        <input
          type="password"
          placeholder="contraseña"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          minLength={8}
          required
        />
        <button type="submit">Dar de alta</button>
      </form>
      {error ? <p className="error">{error}</p> : null}
      <ul className="list">
        {items.map((item) => (
          <li key={item.id}>{item.display_name}</li>
        ))}
        {!items.length ? <li className="muted">Aún no hay Operators.</li> : null}
      </ul>
    </section>
  );
}
