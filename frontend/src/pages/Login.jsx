import { useState } from "react";
import { Link } from "react-router-dom";
import { login } from "../api.js";
import { EMAIL_ERROR, isValidEmail } from "../fieldRules.js";

export default function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [emailBlurred, setEmailBlurred] = useState(false);

  const emailInvalid = Boolean(email) && !isValidEmail(email.trim());

  async function handleSubmit(event) {
    event.preventDefault();
    const nextEmail = email.trim();
    const pass = password.trim();
    setEmail(nextEmail);
    setPassword(pass);
    if (nextEmail) {
      setEmailBlurred(true);
    }
    if (!nextEmail || !pass) {
      setError("El correo y la contraseña son obligatorios.");
      return;
    }
    if (!isValidEmail(nextEmail)) {
      setError(EMAIL_ERROR);
      return;
    }
    setError("");
    setPending(true);
    try {
      const data = await login(nextEmail, pass);
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
        Correo
        <input
          name="email"
          type="email"
          autoComplete="email"
          placeholder="Correo"
          value={email}
          className={emailBlurred && emailInvalid ? "invalid" : undefined}
          onChange={(e) => setEmail(e.target.value)}
          onBlur={() => setEmailBlurred(true)}
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
