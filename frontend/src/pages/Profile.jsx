import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import OtpInput from "../components/OtpInput.jsx";
import PasswordField from "../components/PasswordField.jsx";
import { changePassword, logout, updateProfile, verifyProfileEmail } from "../api.js";
import {
  EMAIL_ERROR,
  PASSWORD_CHANGE_REQUIRED,
  PASSWORD_MISMATCH_ERROR,
  isValidEmail,
  isValidPassword,
} from "../fieldRules.js";

function accountFields(user) {
  return {
    firstName: user?.first_name || "",
    lastName: user?.last_name || "",
    email: user?.email || "",
  };
}

export default function Profile({ session, onSession }) {
  const user = session?.user || {};
  const saved = accountFields(user);
  const [firstName, setFirstName] = useState(saved.firstName);
  const [lastName, setLastName] = useState(saved.lastName);
  const [email, setEmail] = useState(saved.email);
  const [emailBlurred, setEmailBlurred] = useState(false);
  const [profileError, setProfileError] = useState("");
  const [profileOk, setProfileOk] = useState("");
  const [profilePending, setProfilePending] = useState(false);
  const [step, setStep] = useState("form");
  const [pendingEmail, setPendingEmail] = useState("");
  const [otp, setOtp] = useState("");
  const verifyingRef = useRef(false);

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
  const savedFirst = saved.firstName.trim();
  const savedLast = saved.lastName.trim();
  const savedEmail = saved.email.trim();
  const emailInvalid = Boolean(nextEmail) && !isValidEmail(nextEmail);
  const emailChanged = nextEmail.toLowerCase() !== savedEmail.toLowerCase();
  const profileDirty =
    first !== savedFirst || last !== savedLast || emailChanged;
  const profileOkToSave =
    profileDirty &&
    Boolean(first) &&
    Boolean(last) &&
    Boolean(nextEmail) &&
    isValidEmail(nextEmail);

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
    if (profileDirty) return;
    setFirstName(saved.firstName);
    setLastName(saved.lastName);
    setEmail(saved.email);
  }, [saved.firstName, saved.lastName, saved.email, profileDirty]);

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
      const next = accountFields(data.user);
      setFirstName(next.firstName || first);
      setLastName(next.lastName || last);
      if (data.pending_email) {
        setPendingEmail(data.pending_email);
        setEmail(data.pending_email);
        setOtp("");
        setStep("otp");
        return;
      }
      setEmail(next.email || nextEmail);
      setProfileOk(data.detail || "Datos actualizados.");
    } catch (err) {
      setProfileError(err.message);
    } finally {
      setProfilePending(false);
    }
  }

  async function verifyEmailOtp(code) {
    const next = String(code ?? otp).replace(/\D/g, "");
    setOtp(next);
    if (next.length !== 6) {
      setProfileError("Escribe el código de 6 dígitos que enviamos.");
      return;
    }
    if (verifyingRef.current) {
      return;
    }
    verifyingRef.current = true;
    setProfileError("");
    setProfileOk("");
    setProfilePending(true);
    try {
      const data = await verifyProfileEmail(pendingEmail, next);
      onSession?.(data);
      const nextFields = accountFields(data.user);
      setFirstName(nextFields.firstName || first);
      setLastName(nextFields.lastName || last);
      setEmail(nextFields.email || pendingEmail);
      setPendingEmail("");
      setOtp("");
      setStep("form");
      setProfileOk(data.detail || "Datos actualizados.");
    } catch (err) {
      setProfileError(err.message);
    } finally {
      verifyingRef.current = false;
      setProfilePending(false);
    }
  }

  async function handleResendEmailOtp() {
    setProfileError("");
    setProfileOk("");
    setProfilePending(true);
    try {
      const data = await updateProfile(first, last, pendingEmail);
      onSession?.(data);
      if (data.pending_email) {
        setPendingEmail(data.pending_email);
        setOtp("");
      }
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
        <form
          className="card profile-password"
          onSubmit={(event) => {
            if (step === "otp") {
              event.preventDefault();
              verifyEmailOtp(otp);
              return;
            }
            handleProfileSubmit(event);
          }}
          autoComplete="on"
        >
          <h3>Datos de la cuenta</h3>
          <div className="profile-readonly">
            <span>Usuario</span>
            <strong>{user.username || "—"}</strong>
          </div>
          {step === "otp" ? (
            <>
              <p className="muted profile-readonly-hint">
                Enviamos un código a <strong>{pendingEmail}</strong>. El correo
                no cambia hasta que el código sea correcto.
              </p>
              <OtpInput
                id="profile-email-otp"
                value={otp}
                onChange={(next) => {
                  setOtp(next);
                  if (profileError) setProfileError("");
                }}
                onComplete={verifyEmailOtp}
                disabled={profilePending}
                invalid={Boolean(profileError)}
              />
              {profileError ? <p className="error">{profileError}</p> : null}
              <div className="row">
                <button
                  type="button"
                  disabled={profilePending || otp.length !== 6}
                  onClick={() => verifyEmailOtp(otp)}
                >
                  {profilePending ? "Verificando…" : "Confirmar correo"}
                </button>
                <button
                  type="button"
                  className="secondary"
                  disabled={profilePending}
                  onClick={handleResendEmailOtp}
                >
                  Reenviar código
                </button>
                <button
                  type="button"
                  className="secondary"
                  disabled={profilePending}
                  onClick={() => {
                    setOtp("");
                    setProfileError("");
                    setStep("form");
                  }}
                >
                  Volver
                </button>
              </div>
            </>
          ) : (
            <>
              <p className="muted profile-readonly-hint">
                El usuario no se cambia. El nombre y los apellidos se guardan al
                momento. El correo nuevo se confirma con un código.
              </p>
              <label>
                Nombre <span className="req">*</span>
                <input
                  name="first_name"
                  autoComplete="given-name"
                  placeholder="Nombre"
                  value={firstName}
                  onChange={(e) => {
                    setFirstName(e.target.value);
                    setProfileOk("");
                  }}
                  required
                />
              </label>
              <label>
                Apellidos <span className="req">*</span>
                <input
                  name="last_name"
                  autoComplete="family-name"
                  placeholder="Apellidos"
                  value={lastName}
                  onChange={(e) => {
                    setLastName(e.target.value);
                    setProfileOk("");
                  }}
                  required
                />
              </label>
              <label>
                Correo <span className="req">*</span>
                <input
                  name="email"
                  type="email"
                  autoComplete="email"
                  placeholder="correo@empresa.com"
                  value={email}
                  className={emailBlurred && emailInvalid ? "invalid" : undefined}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    setProfileOk("");
                  }}
                  onBlur={() => setEmailBlurred(true)}
                  required
                />
              </label>
              {profileError ? <p className="error">{profileError}</p> : null}
              {profileOk ? <p className="ok">{profileOk}</p> : null}
              <button type="submit" disabled={!profileOkToSave || profilePending}>
                {profilePending
                  ? emailChanged
                    ? "Enviando código…"
                    : "Guardando…"
                  : emailChanged
                    ? "Enviar código"
                    : "Guardar datos"}
              </button>
            </>
          )}
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
