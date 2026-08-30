import { useEffect, useState } from "react";
import {
  deleteOperator,
  inviteOperator,
  listOperators,
  listPendingOperatorInvites,
  updateOperator,
} from "../api.js";
import ConfirmDialog from "../components/ConfirmDialog.jsx";
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
  const [pendingInvites, setPendingInvites] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [emailBlurred, setEmailBlurred] = useState(false);
  const [pending, setPending] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [pendingDelete, setPendingDelete] = useState(null);

  const emailInvalid = Boolean(form.email) && !isValidEmail(form.email.trim());
  const formOk =
    Boolean(form.first_name.trim()) &&
    Boolean(form.last_name.trim()) &&
    Boolean(form.email.trim()) &&
    isValidEmail(form.email.trim());

  async function refresh() {
    const [operators, invites] = await Promise.all([
      listOperators(),
      listPendingOperatorInvites(),
    ]);
    setItems(operators);
    setPendingInvites(invites);
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
      setOk("");
      return;
    }
    if (!isValidEmail(email)) {
      setError(EMAIL_ERROR);
      setOk("");
      return;
    }
    setError("");
    setOk("");
    setPending(true);
    const payload = { first_name, last_name, email };
    try {
      if (editingId) {
        await updateOperator(editingId, payload);
        resetForm();
        await refresh();
      } else {
        const result = await inviteOperator(payload);
        resetForm();
        setOk(result.detail || "Enviamos la invitación a ese correo.");
        await refresh();
      }
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
    setOk("");
  }

  function requestDelete(item) {
    setError("");
    setOk("");
    setPendingDelete(item);
  }

  async function confirmDelete() {
    const item = pendingDelete;
    if (!item || deleting) return;
    setError("");
    setDeleting(true);
    try {
      await deleteOperator(item.id);
      setPendingDelete(null);
      if (editingId === item.id) {
        resetForm();
      }
      await refresh();
    } catch (err) {
      setError(err.message);
      setPendingDelete(null);
    } finally {
      setDeleting(false);
    }
  }

  const deleteLabel = pendingDelete
    ? `${pendingDelete.first_name} ${pendingDelete.last_name}`.trim() ||
      pendingDelete.email
    : "";

  return (
    <section>
      <h2>Operators</h2>
      <p className="hint">
        Envía una invitación con nombre, apellidos y correo. El Operator abre el
        vínculo, escribe el código y elige su contraseña. Hasta entonces no
        está activo en Monitor.
      </p>
      <form onSubmit={handleSubmit}>
        {editingId ? <p className="muted">Editando operator.</p> : null}
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
            {pending
              ? editingId
                ? "Guardando…"
                : "Enviando invitación…"
              : editingId
                ? "Guardar"
                : "Enviar invitación"}
          </button>
          {editingId ? (
            <button type="button" className="secondary" onClick={resetForm}>
              Cancelar
            </button>
          ) : null}
        </div>
      </form>
      {error ? <p className="error">{error}</p> : null}
      {ok ? <p className="ok">{ok}</p> : null}
      {pendingInvites.length ? (
        <ul className="list">
          {pendingInvites.map((item) => (
            <li key={item.email} className="list-item">
              <div>
                <strong>
                  {item.first_name} {item.last_name}
                </strong>
                <span className="muted"> · {item.email}</span>
                <span className="muted beat-when">
                  Invitación enviada · aún no activo en Monitor
                </span>
              </div>
            </li>
          ))}
        </ul>
      ) : null}
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
                onClick={() => requestDelete(item)}
              >
                Baja
              </button>
            </div>
          </li>
        ))}
        {!items.length && !pendingInvites.length ? (
          <li className="muted">Aún no hay Operators.</li>
        ) : null}
      </ul>
      <ConfirmDialog
        open={Boolean(pendingDelete)}
        eyebrow="Operators"
        title={deleteLabel ? `¿Dar de baja a ${deleteLabel}?` : "¿Dar de baja?"}
        description="Ya no podrá entrar a Monitor."
        acceptLabel={deleting ? "Dando de baja…" : "Aceptar"}
        pending={deleting}
        onAccept={confirmDelete}
        onCancel={() => {
          if (!deleting) setPendingDelete(null);
        }}
      />
    </section>
  );
}
