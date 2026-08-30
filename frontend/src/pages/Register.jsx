import { useState } from "react";
import { Link } from "react-router-dom";
import { register } from "../api.js";

export default function Register({ onLogin }) {
  const [companyName, setCompanyName] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    const nextCompany = companyName.trim();
    const user = username.trim();
    const nextEmail = email.trim();
    const pass = password.trim();
    const pass2 = password2.trim();
    setCompanyName(nextCompany);
    setUsername(user);
    setEmail(nextEmail);
    setPassword(pass);
    setPassword2(pass2);
    if (!nextCompany || !user || !pass) {
      setError("Empresa, usuario y contraseña son obligatorios.");
      return;
    }
    if (pass !== pass2) {
      setError("Las contraseñas no coinciden.");
      return;
    }
    setError("");
    setPending(true);
    try {
      const data = await register({
        company_name: nextCompany,
        username: user,
        email: nextEmail,
        password: pass,
        password2: pass2,
      });
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
        <h1>Crear mi Hub</h1>
        <p className="muted">
          Demo de 15 días con 10,000 Beats para dar de alta Systems, Operators y
          tipos.
        </p>
        <label>
          Empresa
          <input
            name="company"
            autoComplete="organization"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            required
          />
        </label>
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
          Correo (opcional)
          <input
            name="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label>
          Contraseña
          <input
            name="password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            required
          />
        </label>
        <label>
          Confirmar contraseña
          <input
            name="password2"
            type="password"
            autoComplete="new-password"
            value={password2}
            onChange={(e) => setPassword2(e.target.value)}
            minLength={8}
            required
          />
        </label>
        {error ? <p className="error">{error}</p> : null}
        <button type="submit" disabled={pending}>
          {pending ? "Creando…" : "Empezar demo"}
        </button>
        <p className="auth-switch">
          ¿Ya tienes Hub? <Link to="/">Entrar</Link>
        </p>
      </form>
    </div>
  );
}
