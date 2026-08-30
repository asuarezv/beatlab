import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import PasswordField from "../components/PasswordField.jsx";
import { changePassword, logout, updateProfile } from "../api.js";
import {
  EMAIL_ERROR,
  PASSWORD_CHANGE_REQUIRED,
  PASSWORD_MISMATCH_ERROR,
  isValidEmail,
  isValidPassword,
} from "../fieldRules.js";

export default function Profile({ session, onSession }) {
  const user = session?.user || {};
  const [firstName, setFirstName] = useState(user.first_name || "");
  const [lastName, setLastName] = useState(user.last_name || "");
  const [email, setEmail] = useState(user.email || "");
  const [emailBlurred, setEmailBlurred] = useState(false);
  const [profileError, setProfileError] = useState("");
  const [profileOk, setProfileOk] = useState("");
  const [profilePending, setProfilePending] = useState(false);

  const [currentPassword, setCurrentPassword] = useState("");
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [showCurrent, setShowCurrent] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showPassword2, setShowPassword2] = useState(false);
  const [passError, setPassError] = useState("");
  const [passPending, setPassPending] = useState(false);
  const [passwordChanged, setPasswordChanged] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);

  const titleId = useId();
  const descId = useId();
  const acceptRef = useRef(null);
  const loggingOutRef = useRef(false);

  const first = firstName.trim();
  const last = lastName.trim();
  const nextEmail = email.trim();
  const emailInvalid = Boolean(nextEmail) && !isValidEmail(nextEmail);
  const profileOkToSave =
    Boolean(first) && Boolean(last) && Boolean(nextEmail) && isValidEmail(nextEmail);

  const current = currentPassword.trim();
  const pass = password.trim();
  const pass2 = password2.trim();
  const passwordsMismatch = Boolean(pass) && Boolean(pass2) && pass !== pass2;
  const formOk =
    Boolean(current) &&
    isValidPassword(pass) &&
    Boolean(pass2) &&
    pass === pass2;

  useEffect(() => {
    if (!passwordChanged) return undefined;
    acceptRef.current?.focus();
    function onKey(event) {
      if (event.key === "Escape") {
        event.preventDefault();
        acceptRef.current?.click();
      }
    }
    document.addEventListener("keydown", onKey);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previousOverflow;
    };
  }, [passwordChanged]);

  async function handleProfileSubmit(event) {
    event.preventDefault();
    setFirstName(first);
    setLastName(last);
    setEmail(nextEmail);
    if (nextEmail) setEmailBlurred(true);
    if (!first || !last || !nextEmail) {
      setProfileOk("");
      setProfileError("El nombre, los apellidos y el correo son obligatorios.");
      return;
    }
    if (!isValidEmail(nextEmail)) {
      setProfileOk("");
      setProfileError(EMAIL_ERROR);
      return;
    }
    setProfileError("");
    setProfileOk("");
    setProfilePending(true);
    try {
      const data = await updateProfile(first, last, nextEmail);
      onSession?.(data);
      setProfileOk(data.detail || "Datos actualizados.");
    } catch (err) {
      setProfileError(err.message);
    } finally {
      setProfilePending(false);
    }
  }

  async function handlePasswordSubmit(event) {
    event.preventDefault();
    setCurrentPassword(current);
    setPassword(pass);
    setPassword2(pass2);
    if (!formOk) {
      setPassError(
        !current || !pass || !pass2
          ? PASSWORD_CHANGE_REQUIRED
          : passwordsMismatch
            ? PASSWORD_MISMATCH_ERROR
            : "La contraseña debe tener al menos 8 caracteres.",
      );
      return;
    }
    setPassError("");
    setPassPending(true);
    try {
      await changePassword(current, pass, pass2);
      setCurrentPassword("");
      setPassword("");
      setPassword2("");
      setPasswordChanged(true);
    } catch (err) {
      setPassError(err.message);
    } finally {
      setPassPending(false);
    }
  }

  async function handleAcceptLogout() {
    if (loggingOutRef.current) return;
    loggingOutRef.current = true;
    setLoggingOut(true);
    try {
      await logout();
    } finally {
      onSession?.(null);
      window.location.assign("/entrar");
    }
  }

  return (
    <section>
      <h2>Perfil</h2>
      <p className="hint">Datos de la cuenta con la que entras al Hub.</p>
      <div className="profile-cards">
        <form className="card profile-password" onSubmit={handleProfileSubmit}>
          <h3>Datos de la cuenta</h3>
          <label>
            Usuario
            <input
              name="username"
              value={user.username || ""}
              readOnly
              disabled
              autoComplete="username"
            />
          </label>
          <label>
            Nombre <span className="req">*</span>
            <input
              name="first_name"
              autoComplete="given-name"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              required
            />
          </label>
          <label>
            Apellidos <span className="req">*</span>
            <input
              name="last_name"
              autoComplete="family-name"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
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
          {profileError ? <p className="error">{profileError}</p> : null}
          {profileOk ? <p className="ok">{profileOk}</p> : null}
          <button type="submit" disabled={!profileOkToSave || profilePending}>
            {profilePending ? "Guardando…" : "Guardar datos"}
          </button>
        </form>
        <form className="card profile-password" onSubmit={handlePasswordSubmit}>
          <h3>Cambiar contraseña</h3>
          <PasswordField
            label="Contraseña actual"
            name="current_password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            autoComplete="current-password"
            visible={showCurrent}
            onToggle={() => setShowCurrent((value) => !value)}
          />
          <PasswordField
            label="Nueva contraseña"
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
          {passwordsMismatch ? (
            <p className="error">{PASSWORD_MISMATCH_ERROR}</p>
          ) : null}
          {passError ? <p className="error">{passError}</p> : null}
          <button type="submit" disabled={!formOk || passPending}>
            {passPending ? "Guardando…" : "Actualizar contraseña"}
          </button>
        </form>
      </div>
      {passwordChanged
        ? createPortal(
            <div className="glossary-backdrop">
              <div
                className="glossary-dialog confirm-dialog"
                role="dialog"
                aria-modal="true"
                aria-labelledby={titleId}
                aria-describedby={descId}
              >
                <div className="glossary-dialog-bar" aria-hidden="true" />
                <p className="eyebrow">Perfil</p>
                <h2 id={titleId}>Contraseña actualizada</h2>
                <p id={descId}>
                  La contraseña se cambió. Inicia sesión de nuevo.
                </p>
                <button
                  ref={acceptRef}
                  type="button"
                  onClick={handleAcceptLogout}
                  disabled={loggingOut}
                >
                  {loggingOut ? "Saliendo…" : "Aceptar"}
                </button>
              </div>
            </div>,
            document.body,
          )
        : null}
    </section>
  );
}
