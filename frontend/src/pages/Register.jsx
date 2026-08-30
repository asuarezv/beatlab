import { useState } from "react";
import { Link } from "react-router-dom";
import PasswordField from "../components/PasswordField.jsx";
import { confirmRegisterOtp, requestRegisterOtp } from "../api.js";
import {
  COMPANY_NAME_ERROR,
  EMAIL_ERROR,
  USERNAME_ERROR,
  isValidCompanyName,
  isValidEmail,
  isValidUsername,
  sanitizeUsername,
} from "../fieldRules.js";

export default function Register({ onLogin }) {
  const [companyName, setCompanyName] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [otp, setOtp] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showPassword2, setShowPassword2] = useState(false);
  const [step, setStep] = useState("form");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [emailBlurred, setEmailBlurred] = useState(false);

  const emailInvalid = Boolean(email) && !isValidEmail(email.trim());
  const pass = password.trim();
  const pass2 = password2.trim();
  const passwordsMismatch = Boolean(pass) && Boolean(pass2) && pass !== pass2;
  const formOk =
    Boolean(companyName.trim()) &&
    isValidCompanyName(companyName.trim()) &&
    Boolean(username) &&
    isValidUsername(username) &&
    Boolean(email.trim()) &&
    isValidEmail(email.trim()) &&
    Boolean(pass) &&
    pass.length >= 8 &&
    Boolean(pass2) &&
    pass === pass2;

  async function handleStart(event) {
    event.preventDefault();
    const nextCompany = companyName.trim();
    const user = username;
    const nextEmail = email.trim();
    const pass = password.trim();
    const pass2 = password2.trim();
    setCompanyName(nextCompany);
    setUsername(user);
    setEmail(nextEmail);
    setPassword(pass);
    setPassword2(pass2);
    if (nextEmail) {
      setEmailBlurred(true);
    }
    if (!nextCompany || !user || !nextEmail || !pass) {
      setError("Empresa, usuario, correo y contraseña son obligatorios.");
      return;
    }
    if (!isValidCompanyName(nextCompany)) {
      setError(COMPANY_NAME_ERROR);
      return;
    }
    if (!isValidUsername(user)) {
      setError(USERNAME_ERROR);
      return;
    }
    if (!isValidEmail(nextEmail)) {
      setError(EMAIL_ERROR);
      return;
    }
    if (pass !== pass2) {
      setError("Las contraseñas no coinciden.");
      return;
    }
    setError("");
    setPending(true);
    try {
      await requestRegisterOtp({
        company_name: nextCompany,
        username: user,
        email: nextEmail,
        password: pass,
        password2: pass2,
      });
      setStep("otp");
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  async function handleVerify(event) {
    event.preventDefault();
    const code = otp.trim();
    setOtp(code);
    if (!code) {
      setError("Escribe el código que te enviamos.");
      return;
    }
    setError("");
    setPending(true);
    try {
      const data = await confirmRegisterOtp(email.trim(), code);
      onLogin(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  if (step === "otp") {
    return (
      <div className="wrap center">
        <form className="card" onSubmit={handleVerify}>
          <p className="eyebrow">BeatLab</p>
          <h1>Código de verificación</h1>
          <p className="muted">
            Enviamos un código a <strong>{email}</strong> desde info@nynusoft.com.
          </p>
          <label>
            Código <span className="req">*</span>
            <input
              name="otp"
              inputMode="numeric"
              autoComplete="one-time-code"
              value={otp}
              onChange={(e) => setOtp(e.target.value)}
              required
            />
          </label>
          {error ? <p className="error">{error}</p> : null}
          <button type="submit" disabled={pending}>
            {pending ? "Verificando…" : "Crear Hub"}
          </button>
          <p className="auth-switch">
            <button
              type="button"
              className="linkish"
              disabled={pending}
              onClick={() => setStep("form")}
            >
              Volver
            </button>
          </p>
        </form>
      </div>
    );
  }

  return (
    <div className="wrap center">
      <form className="card" onSubmit={handleStart}>
        <p className="eyebrow">BeatLab</p>
        <h1>Crear mi Hub</h1>
        <p className="muted">
          Demo de 15 días con 10,000 Beats. Te mandamos un código a tu correo
          para confirmar el alta.
        </p>
        <label>
          Empresa <span className="req">*</span>
          <input
            name="company"
            autoComplete="organization"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            required
          />
        </label>
        <label>
          Usuario <span className="req">*</span>
          <input
            name="username"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(sanitizeUsername(e.target.value))}
            required
          />
        </label>
        <label>
          Correo <span className="req">*</span>
          <input
            name="email"
            type="email"
            autoComplete="email"
            value={email}
            className={emailBlurred && emailInvalid ? "invalid" : undefined}
            onChange={(e) => setEmail(e.target.value)}
            onBlur={() => setEmailBlurred(true)}
            required
          />
        </label>
        <PasswordField
          label="Contraseña"
          name="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="new-password"
          visible={showPassword}
          onToggle={() => setShowPassword((value) => !value)}
          invalid={passwordsMismatch}
        />
        <PasswordField
          label="Confirmar contraseña"
          name="password2"
          value={password2}
          onChange={(e) => setPassword2(e.target.value)}
          autoComplete="new-password"
          visible={showPassword2}
          onToggle={() => setShowPassword2((value) => !value)}
          invalid={passwordsMismatch}
        />
        {error ? <p className="error">{error}</p> : null}
        <button type="submit" disabled={!formOk || pending}>
          {pending ? "Enviando código…" : "Enviar código"}
        </button>
        <p className="auth-switch">
          ¿Ya tienes Hub? <Link to="/entrar">Entrar</Link>
        </p>
      </form>
    </div>
  );
}
