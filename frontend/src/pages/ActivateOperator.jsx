import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  fetchCsrf,
  fetchOperatorInvite,
  requestOperatorRecover,
  setOperatorAccessPassword,
  verifyOperatorAccess,
} from "../api.js";
import OtpInput from "../components/OtpInput.jsx";
import PasswordField from "../components/PasswordField.jsx";
import {
  EMAIL_ERROR,
  PASSWORD_MISMATCH_ERROR,
  isValidEmail,
  isValidPassword,
} from "../fieldRules.js";

function PasswordStep({
  pending,
  error,
  onSubmit,
  onCancel,
  recoverTo,
}) {
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showPassword2, setShowPassword2] = useState(false);
  const pass = password.trim();
  const pass2 = password2.trim();
  const passwordsMismatch = Boolean(pass) && Boolean(pass2) && pass !== pass2;
  const formOk = isValidPassword(pass) && Boolean(pass2) && pass === pass2;

  return (
    <form
      className="card"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(pass, pass2);
      }}
    >
      <p className="eyebrow">
        <Link to="/">BeatLab</Link>
      </p>
      <h1>Elige tu contraseña</h1>
      <p className="muted">
        Con esta contraseña entrarás a Monitor. Si cancelas, no quedará
        guardada: recupera tu cuenta para volver a elegirla.
      </p>
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
      {passwordsMismatch ? <p className="error">{PASSWORD_MISMATCH_ERROR}</p> : null}
      {error ? <p className="error">{error}</p> : null}
      <button type="submit" disabled={!formOk || pending}>
        {pending ? "Guardando…" : "Guardar contraseña"}
      </button>
      <p className="auth-switch">
        <button type="button" className="linkish" disabled={pending} onClick={onCancel}>
          Cancelar
        </button>
        {" · "}
        <Link to={recoverTo}>Recuperar cuenta</Link>
      </p>
    </form>
  );
}

function DoneStep({ detail }) {
  return (
    <div className="card">
      <p className="eyebrow">
        <Link to="/">BeatLab</Link>
      </p>
      <h1>Listo</h1>
      <p className="ok">{detail}</p>
      <p className="muted">Abre Monitor e entra con tu correo y contraseña.</p>
    </div>
  );
}

export default function ActivateOperator() {
  const [params] = useSearchParams();
  const token = (params.get("token") || "").trim();
  const [info, setInfo] = useState(undefined);
  const [otp, setOtp] = useState("");
  const [grant, setGrant] = useState("");
  const [step, setStep] = useState("otp");
  const [error, setError] = useState("");
  const [detail, setDetail] = useState("");
  const [pending, setPending] = useState(false);
  const verifyingRef = useRef(false);

  useEffect(() => {
    fetchCsrf().catch(() => {});
  }, []);

  useEffect(() => {
    if (!token) {
      setInfo(null);
      setError("Este vínculo no es válido.");
      return;
    }
    let cancelled = false;
    fetchOperatorInvite(token)
      .then((data) => {
        if (cancelled) return;
        setInfo(data);
        if (data.expired) {
          setError("El código caducó. Recupera tu cuenta para recibir uno nuevo.");
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setInfo(null);
          setError(err.message);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function verifyOtp(code) {
    const next = String(code ?? otp).replace(/\D/g, "");
    setOtp(next);
    if (next.length !== 6) {
      setError("Escribe el código de 6 dígitos que te enviamos.");
      return;
    }
    if (verifyingRef.current) {
      return;
    }
    verifyingRef.current = true;
    setError("");
    setPending(true);
    try {
      const data = await verifyOperatorAccess({ token, otp: next });
      setGrant(data.grant);
      setStep("password");
    } catch (err) {
      setError(err.message);
    } finally {
      verifyingRef.current = false;
      setPending(false);
    }
  }

  async function savePassword(password, password2) {
    setError("");
    setPending(true);
    try {
      const data = await setOperatorAccessPassword({
        grant,
        password,
        password2,
      });
      setDetail(data.detail);
      setStep("done");
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  const recoverTo = info?.email
    ? `/recuperar?email=${encodeURIComponent(info.email)}`
    : "/recuperar";

  if (info === undefined) {
    return (
      <div className="card">
        <p className="muted">Cargando invitación…</p>
      </div>
    );
  }

  if (!info) {
    return (
      <div className="card">
        <p className="eyebrow">
          <Link to="/">BeatLab</Link>
        </p>
        <h1>Invitación</h1>
        {error ? <p className="error">{error}</p> : null}
        <p className="auth-switch">
          <Link to="/recuperar">Recuperar cuenta</Link>
        </p>
      </div>
    );
  }

  if (step === "done") {
    return <DoneStep detail={detail} />;
  }

  if (step === "password") {
    return (
      <PasswordStep
        pending={pending}
        error={error}
        onSubmit={savePassword}
        recoverTo={recoverTo}
        onCancel={() => {
          setGrant("");
          setOtp("");
          setError("");
          setStep("cancelled");
        }}
      />
    );
  }

  if (step === "cancelled") {
    return (
      <div className="card">
        <p className="eyebrow">
          <Link to="/">BeatLab</Link>
        </p>
        <h1>Invitación cancelada</h1>
        <p className="muted">
          No se guardó contraseña ni quedaste con acceso. Usa el correo o
          recupera tu cuenta para elegirla.
        </p>
        <p className="auth-switch">
          <Link to={recoverTo}>Recuperar cuenta</Link>
        </p>
      </div>
    );
  }

  return (
    <form
      className="card"
      onSubmit={(event) => {
        event.preventDefault();
        verifyOtp(otp);
      }}
    >
      <p className="eyebrow">
        <Link to="/">BeatLab</Link>
      </p>
      <h1>Activa Monitor</h1>
      <p className="muted">
        {info.company_name} te invitó. Escribe el código de 6 dígitos que
        llegó a <strong>{info.email}</strong>.
      </p>
      <label htmlFor="invite-otp">
        Código <span className="req">*</span>
      </label>
      <OtpInput
        id="invite-otp"
        value={otp}
        onChange={(next) => {
          setOtp(next);
          if (error) setError("");
        }}
        onComplete={verifyOtp}
        disabled={pending}
        invalid={Boolean(error)}
      />
      {error ? <p className="error">{error}</p> : null}
      <button type="submit" disabled={pending || otp.length !== 6}>
        {pending ? "Verificando…" : "Continuar"}
      </button>
      <p className="auth-switch">
        <Link to={recoverTo}>Recuperar cuenta</Link>
      </p>
    </form>
  );
}

export function RecoverOperator() {
  const [params] = useSearchParams();
  const initialEmail = (params.get("email") || "").trim();
  const [email, setEmail] = useState(initialEmail);
  const [otp, setOtp] = useState("");
  const [grant, setGrant] = useState("");
  const [step, setStep] = useState("email");
  const [error, setError] = useState("");
  const [detail, setDetail] = useState("");
  const [pending, setPending] = useState(false);
  const [emailBlurred, setEmailBlurred] = useState(Boolean(initialEmail));
  const verifyingRef = useRef(false);
  const emailInvalid = Boolean(email) && !isValidEmail(email.trim());

  useEffect(() => {
    fetchCsrf().catch(() => {});
  }, []);

  async function handleRequest(event) {
    event.preventDefault();
    const nextEmail = email.trim();
    setEmail(nextEmail);
    setEmailBlurred(true);
    if (!nextEmail) {
      setError("El correo es obligatorio.");
      return;
    }
    if (!isValidEmail(nextEmail)) {
      setError(EMAIL_ERROR);
      return;
    }
    setError("");
    setPending(true);
    try {
      await requestOperatorRecover(nextEmail);
      setOtp("");
      setStep("otp");
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  async function verifyOtp(code) {
    const next = String(code ?? otp).replace(/\D/g, "");
    setOtp(next);
    if (next.length !== 6) {
      setError("Escribe el código de 6 dígitos que te enviamos.");
      return;
    }
    if (verifyingRef.current) {
      return;
    }
    verifyingRef.current = true;
    setError("");
    setPending(true);
    try {
      const data = await verifyOperatorAccess({ email: email.trim(), otp: next });
      setGrant(data.grant);
      setStep("password");
    } catch (err) {
      setError(err.message);
    } finally {
      verifyingRef.current = false;
      setPending(false);
    }
  }

  async function savePassword(password, password2) {
    setError("");
    setPending(true);
    try {
      const data = await setOperatorAccessPassword({
        grant,
        password,
        password2,
      });
      setDetail(data.detail);
      setStep("done");
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  const recoverTo = email.trim()
    ? `/recuperar?email=${encodeURIComponent(email.trim())}`
    : "/recuperar";

  if (step === "done") {
    return <DoneStep detail={detail} />;
  }

  if (step === "password") {
    return (
      <PasswordStep
        pending={pending}
        error={error}
        onSubmit={savePassword}
        recoverTo={recoverTo}
        onCancel={() => {
          setGrant("");
          setOtp("");
          setError("");
          setStep("cancelled");
        }}
      />
    );
  }

  if (step === "cancelled") {
    return (
      <div className="card">
        <p className="eyebrow">
          <Link to="/">BeatLab</Link>
        </p>
        <h1>Sin contraseña</h1>
        <p className="muted">
          No se guardó contraseña ni quedaste con acceso. Recupera tu cuenta
          para recibir un código nuevo y elegirla.
        </p>
        <p className="auth-switch">
          <Link to={recoverTo}>Recuperar cuenta</Link>
        </p>
      </div>
    );
  }

  if (step === "otp") {
    return (
      <form
        className="card"
        onSubmit={(event) => {
          event.preventDefault();
          verifyOtp(otp);
        }}
      >
        <p className="eyebrow">
          <Link to="/">BeatLab</Link>
        </p>
        <h1>Código</h1>
        <p className="muted">
          Enviamos un código a <strong>{email}</strong>.
        </p>
        <label htmlFor="recover-otp">
          Código <span className="req">*</span>
        </label>
        <OtpInput
          id="recover-otp"
          value={otp}
          onChange={(next) => {
            setOtp(next);
            if (error) setError("");
          }}
          onComplete={verifyOtp}
          disabled={pending}
          invalid={Boolean(error)}
        />
        {error ? <p className="error">{error}</p> : null}
        <button type="submit" disabled={pending || otp.length !== 6}>
          {pending ? "Verificando…" : "Continuar"}
        </button>
        <p className="auth-switch">
          <button
            type="button"
            className="linkish"
            disabled={pending}
            onClick={() => {
              setOtp("");
              setError("");
              setStep("email");
            }}
          >
            Volver
          </button>
        </p>
      </form>
    );
  }

  return (
    <form className="card" onSubmit={handleRequest}>
      <p className="eyebrow">
        <Link to="/">BeatLab</Link>
      </p>
      <h1>Recuperar cuenta</h1>
      <p className="muted">
        Te enviamos un código para elegir la contraseña de Monitor.
      </p>
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
      {error ? <p className="error">{error}</p> : null}
      <button type="submit" disabled={pending || !isValidEmail(email.trim())}>
        {pending ? "Enviando…" : "Enviar código"}
      </button>
    </form>
  );
}
