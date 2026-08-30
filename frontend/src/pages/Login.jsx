import { useState } from "react";
import { login } from "../api.js";

export default function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    const user = username.trim();
    const pass = password.trim();
    setUsername(user);
    setPassword(pass);
    if (!user || !pass) {
      setError("Usuario y contraseña son obligatorios.");
      return;
    }
    setError("");
    setPending(true);
    try {
      const data = await login(user, pass);
      onLogin(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="wrap center">
      <form className="card" onSubmit={handleSubmit}>
        <p className="eyebrow">BeatLab</p>
        <h1>Entrar al Hub</h1>
        <label>
          Usuario
          <input
            name="username"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
        </label>
        <label>
          Contraseña
          <input
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        {error ? <p className="error">{error}</p> : null}
        <button type="submit" disabled={pending}>
          {pending ? "Entrando…" : "Entrar"}
        </button>
      </form>
    </div>
  );
}
