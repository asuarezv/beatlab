import { useEffect, useState } from "react";
import {
  createOperator,
  deleteOperator,
  listOperators,
  updateOperator,
} from "../api.js";
import { EMAIL_ERROR, isValidEmail } from "../fieldRules.js";

const emptyForm = { first_name: "", last_name: "", email: "" };

function formatLastLogin(value) {
  if (!value) return "Nunca";
  try {
    return new Date(value).toLocaleString("es-MX");
  } catch {
    return value;
  }
}

export default function Operators() {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState("");
  const [emailBlurred, setEmailBlurred] = useState(false);
  const [pending, setPending] = useState(false);

  const emailInvalid = Boolean(form.email) && !isValidEmail(form.email.trim());
  const formOk =
    Boolean(form.first_name.trim()) &&
    Boolean(form.last_name.trim()) &&
    Boolean(form.email.trim()) &&
    isValidEmail(form.email.trim());

  async function refresh() {
    setItems(await listOperators());
  }

  useEffect(() => {
    refresh().catch((err) => setError(err.message));
  }, []);

  function handleChange(field) {
    return (event) => {
      setForm((current) => ({ ...current, [field]: event.target.value }));
    };
  }

  function resetForm() {
    setForm(emptyForm);
    setEditingId(null);
    setEmailBlurred(false);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const first_name = form.first_name.trim();
    const last_name = form.last_name.trim();
    const email = form.email.trim();
    setForm({ first_name, last_name, email });
    if (email) {
      setEmailBlurred(true);
    }
    if (!first_name || !last_name || !email) {
      setError("Nombre, apellidos y correo son obligatorios.");
      return;
    }
    if (!isValidEmail(email)) {
      setError(EMAIL_ERROR);
      return;
    }
    setError("");
    setPending(true);
    const payload = { first_name, last_name, email };
    try {
      if (editingId) {
        await updateOperator(editingId, payload);
      } else {
        await createOperator(payload);
      }
      resetForm();
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  function startEdit(item) {
    setEditingId(item.id);
    setForm({
      first_name: item.first_name,
      last_name: item.last_name,
      email: item.email,
    });
    setEmailBlurred(false);
    setError("");
  }

  async function handleDelete(item) {
    const label = `${item.first_name} ${item.last_name}`.trim() || item.email;
    const ok = window.confirm(
      `¿Dar de baja a ${label}? Ya no podrá entrar a Monitor.`,
    );
    if (!ok) return;
    setError("");
    try {
      await deleteOperator(item.id);
      if (editingId === item.id) {
        resetForm();
      }
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section>
      <h2>Operators</h2>
      <p className="hint">
        Entran a Monitor con su correo y un código de 6 dígitos. No usan
        contraseña.
      </p>
      <form onSubmit={handleSubmit}>
        {editingId ? (
          <p className="muted">Editando operator.</p>
        ) : null}
        <div className="row">
          <input
            placeholder="nombre"
            value={form.first_name}
            onChange={handleChange("first_name")}
            autoComplete="given-name"
            required
          />
          <input
            placeholder="apellidos"
            value={form.last_name}
            onChange={handleChange("last_name")}
            autoComplete="family-name"
            required
          />
          <input
            type="email"
            placeholder="correo"
            value={form.email}
            className={emailBlurred && emailInvalid ? "invalid" : undefined}
            onChange={handleChange("email")}
            onBlur={() => setEmailBlurred(true)}
            autoComplete="email"
            required
          />
          <button type="submit" disabled={!formOk || pending}>
            {pending ? "Guardando…" : editingId ? "Guardar" : "Dar de alta"}
          </button>
          {editingId ? (
            <button type="button" className="secondary" onClick={resetForm}>
              Cancelar
            </button>
          ) : null}
        </div>
      </form>
      {error ? <p className="error">{error}</p> : null}
      <ul className="list">
        {items.map((item) => (
          <li key={item.id} className="list-item">
            <div>
              <strong>
                {item.first_name} {item.last_name}
              </strong>
              <span className="muted"> · {item.email}</span>
              <span className="muted beat-when">
                Último acceso · {formatLastLogin(item.last_login_at)}
              </span>
            </div>
            <div className="list-actions">
              <button type="button" className="secondary" onClick={() => startEdit(item)}>
                Editar
              </button>
              <button
                type="button"
                className="danger"
                onClick={() => handleDelete(item)}
              >
                Baja
              </button>
            </div>
          </li>
        ))}
        {!items.length ? <li className="muted">Aún no hay Operators.</li> : null}
      </ul>
    </section>
  );
}
