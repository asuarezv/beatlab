import { useState } from "react";
import { Link } from "react-router-dom";
import { login } from "../api.js";
import { USERNAME_ERROR, isValidUsername, sanitizeUsername } from "../fieldRules.js";

export default function Login({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    const user = username;
    const pass = password.trim();
    setUsername(user);
    setPassword(pass);
    if (!user || !pass) {
      setError("Usuario y contraseña son obligatorios.");
      return;
    }
    if (!isValidUsername(user)) {
      setError(USERNAME_ERROR);
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
    <form className="card" onSubmit={handleSubmit}>
      <p className="eyebrow">
        <Link to="/">BeatLab</Link>
      </p>
      <h1>Entrar al Hub</h1>
      <label>
        Usuario
        <input
          name="username"
          autoComplete="username"
          value={username}
          onChange={(e) => setUsername(sanitizeUsername(e.target.value))}
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
      <p className="auth-switch">
        ¿Primera vez? <Link to="/registro">Crear mi Hub (demo 15 días)</Link>
      </p>
    </form>
  );
}
