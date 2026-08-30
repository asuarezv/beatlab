import { useState } from "react";
import PasswordField from "../components/PasswordField.jsx";
import { changePassword } from "../api.js";
import {
  PASSWORD_CHANGE_REQUIRED,
  PASSWORD_MISMATCH_ERROR,
  isValidPassword,
} from "../fieldRules.js";

export default function Profile({ session }) {
  const user = session?.user || {};
  const [currentPassword, setCurrentPassword] = useState("");
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [showCurrent, setShowCurrent] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showPassword2, setShowPassword2] = useState(false);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [pending, setPending] = useState(false);

  const current = currentPassword.trim();
  const pass = password.trim();
  const pass2 = password2.trim();
  const passwordsMismatch = Boolean(pass) && Boolean(pass2) && pass !== pass2;
  const formOk =
    Boolean(current) &&
    isValidPassword(pass) &&
    Boolean(pass2) &&
    pass === pass2;

  async function handleSubmit(event) {
    event.preventDefault();
    setCurrentPassword(current);
    setPassword(pass);
    setPassword2(pass2);
    if (!current || !pass || !pass2) {
      setOk("");
      setError(PASSWORD_CHANGE_REQUIRED);
      return;
    }
    if (pass !== pass2) {
      setOk("");
      setError(PASSWORD_MISMATCH_ERROR);
      return;
    }
    if (!isValidPassword(pass)) {
      setOk("");
      setError("La contraseña debe tener al menos 8 caracteres.");
      return;
    }
    setError("");
    setOk("");
    setPending(true);
    try {
      const data = await changePassword(current, pass, pass2);
      setCurrentPassword("");
      setPassword("");
      setPassword2("");
      setOk(data.detail || "Contraseña actualizada.");
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  return (
    <section>
      <h2>Perfil</h2>
      <p className="hint">Datos de la cuenta con la que entras al Hub.</p>
      <dl className="profile-fields">
        <div>
          <dt>Nombre</dt>
          <dd>{user.display_name || "—"}</dd>
        </div>
        <div>
          <dt>Usuario</dt>
          <dd>{user.username || "—"}</dd>
        </div>
        <div>
          <dt>Correo</dt>
          <dd>{user.email || "—"}</dd>
        </div>
      </dl>
      <form className="card profile-password" onSubmit={handleSubmit}>
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
        {error ? <p className="error">{error}</p> : null}
        {ok ? <p className="ok">{ok}</p> : null}
        <button type="submit" disabled={!formOk || pending}>
          {pending ? "Guardando…" : "Actualizar contraseña"}
        </button>
      </form>
    </section>
  );
}
