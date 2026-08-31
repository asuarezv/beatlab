import { useEffect, useState } from "react";
import {
  deleteOperator,
  inviteOperator,
  listBeatTypes,
  listOperators,
  listPendingOperatorInvites,
  updateOperator,
  updatePendingOperatorInvite,
} from "../api.js";
import ConfirmDialog from "../components/ConfirmDialog.jsx";
import { EMAIL_ERROR, isValidEmail } from "../fieldRules.js";

const emptyForm = {
  first_name: "",
  last_name: "",
  email: "",
  receive_all_beat_types: false,
  beat_type_ids: [],
};

function assignmentLabel(item, types) {
  if (item.receive_all_beat_types) return "Recibe todos los tipos";
  const ids = new Set(item.beat_type_ids || []);
  const names = types.filter((type) => ids.has(type.id)).map((type) => type.name);
  if (!names.length) return "No recibe Beats";
  return `Recibe: ${names.join(", ")}`;
}

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
  const [types, setTypes] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [editingInviteId, setEditingInviteId] = useState(null);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [emailBlurred, setEmailBlurred] = useState(false);
  const [pending, setPending] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [pendingDelete, setPendingDelete] = useState(null);
  const [confirmEmpty, setConfirmEmpty] = useState(false);

  const emailInvalid = Boolean(form.email) && !isValidEmail(form.email.trim());
  const formOk =
    Boolean(form.first_name.trim()) &&
    Boolean(form.last_name.trim()) &&
    Boolean(form.email.trim()) &&
    isValidEmail(form.email.trim());
  const hasAssignment =
    form.receive_all_beat_types || form.beat_type_ids.length > 0;
  const editing = Boolean(editingId || editingInviteId);

  async function refresh() {
    const [operators, invites, beatTypes] = await Promise.all([
      listOperators(),
      listPendingOperatorInvites(),
      listBeatTypes(),
    ]);
    setItems(operators);
    setPendingInvites(invites);
    setTypes(beatTypes);
  }

  useEffect(() => {
    refresh().catch((err) => setError(err.message));
  }, []);

  function handleChange(field) {
    return (event) => {
      setForm((current) => ({ ...current, [field]: event.target.value }));
    };
  }

  function toggleAllTypes(event) {
    const checked = event.target.checked;
    setForm((current) => ({
      ...current,
      receive_all_beat_types: checked,
      beat_type_ids: checked ? [] : current.beat_type_ids,
    }));
  }

  function toggleType(typeId) {
    setForm((current) => {
      if (current.receive_all_beat_types) return current;
      const selected = new Set(current.beat_type_ids);
      if (selected.has(typeId)) {
        selected.delete(typeId);
      } else {
        selected.add(typeId);
      }
      return { ...current, beat_type_ids: [...selected] };
    });
  }

  function resetForm() {
    setForm(emptyForm);
    setEditingId(null);
    setEditingInviteId(null);
    setEmailBlurred(false);
    setConfirmEmpty(false);
  }

  function assignmentPayload() {
    return {
      receive_all_beat_types: form.receive_all_beat_types,
      beat_type_ids: form.receive_all_beat_types ? [] : form.beat_type_ids,
    };
  }

  async function submitAssignment() {
    const first_name = form.first_name.trim();
    const last_name = form.last_name.trim();
    const email = form.email.trim();
    setForm((current) => ({ ...current, first_name, last_name, email }));
    setError("");
    setOk("");
    setPending(true);
    const payload = { first_name, last_name, email, ...assignmentPayload() };
    try {
      if (editingInviteId) {
        await updatePendingOperatorInvite(editingInviteId, payload);
        resetForm();
        setOk("Invitación actualizada. Se aplicará al activar la cuenta.");
        await refresh();
      } else if (editingId) {
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
      setConfirmEmpty(false);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const first_name = form.first_name.trim();
    const last_name = form.last_name.trim();
    const email = form.email.trim();
    setForm((current) => ({ ...current, first_name, last_name, email }));
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
    if (!hasAssignment) {
      setConfirmEmpty(true);
      return;
    }
    await submitAssignment();
  }

  function startEdit(item) {
    setEditingId(item.id);
    setEditingInviteId(null);
    setForm({
      first_name: item.first_name,
      last_name: item.last_name,
      email: item.email,
      receive_all_beat_types: Boolean(item.receive_all_beat_types),
      beat_type_ids: item.receive_all_beat_types ? [] : [...(item.beat_type_ids || [])],
    });
    setEmailBlurred(false);
    setError("");
    setOk("");
  }

  function startEditInvite(item) {
    setEditingInviteId(item.id);
    setEditingId(null);
    setForm({
      first_name: item.first_name,
      last_name: item.last_name,
      email: item.email,
      receive_all_beat_types: Boolean(item.receive_all_beat_types),
      beat_type_ids: item.receive_all_beat_types ? [] : [...(item.beat_type_ids || [])],
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
        Envía una invitación con nombre, apellidos, correo y los tipos de Beat
        que va a recibir. Si no asignas ninguno, no verá Beats en Monitor. El
        admin del Hub sí ve todos los de la empresa. El Operator abre el
        vínculo, escribe el código y elige su contraseña. Hasta entonces no
        está activo en Monitor.
      </p>
      <form onSubmit={handleSubmit}>
        {editingId ? <p className="muted">Editando operator.</p> : null}
        {editingInviteId ? (
          <p className="muted">Editando invitación pendiente.</p>
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
            disabled={Boolean(editingInviteId)}
          />
        </div>
        <fieldset className="assignment">
          <legend>Beats que recibe</legend>
          <p className="hint">
            Marca los tipos que le corresponden. «Todos los tipos» incluye los
            que se den de alta después. Sin selección, no recibe nada.
          </p>
          <div className="assignment-options">
            <label>
              <input
                type="checkbox"
                checked={form.receive_all_beat_types}
                onChange={toggleAllTypes}
              />
              Todos los tipos
            </label>
            {types.map((type) => (
              <label
                key={type.id}
                className={form.receive_all_beat_types ? "is-disabled" : undefined}
              >
                <input
                  type="checkbox"
                  checked={
                    form.receive_all_beat_types ||
                    form.beat_type_ids.includes(type.id)
                  }
                  disabled={form.receive_all_beat_types}
                  onChange={() => toggleType(type.id)}
                />
                {type.name}
              </label>
            ))}
            {!types.length ? (
              <p className="muted">
                Aún no hay tipos. Créalos en Tipos para asignarlos uno a uno, o
                marca «Todos los tipos».
              </p>
            ) : null}
          </div>
        </fieldset>
        <div className="row">
          <button type="submit" disabled={!formOk || pending}>
            {pending
              ? editing
                ? "Guardando…"
                : "Enviando invitación…"
              : editingId
                ? "Guardar"
                : editingInviteId
                  ? "Guardar invitación"
                  : "Enviar invitación"}
          </button>
          {editing ? (
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
            <li key={item.id || item.email} className="list-item">
              <div>
                <strong>
                  {item.first_name} {item.last_name}
                </strong>
                <span className="muted"> · {item.email}</span>
                <span className="muted beat-when">
                  Invitación enviada · aún no activo en Monitor
                </span>
                <span className="muted beat-when">
                  {assignmentLabel(item, types)}
                </span>
              </div>
              <div className="list-actions">
                <button
                  type="button"
                  className="secondary"
                  onClick={() => startEditInvite(item)}
                >
                  Editar
                </button>
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
              <span className="muted beat-when">
                {assignmentLabel(item, types)}
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
      <ConfirmDialog
        open={confirmEmpty}
        eyebrow="Operators"
        title="¿Continuar sin tipos de Beat?"
        description="Sin tipos asignados, este Operator no recibirá Beats en Monitor ni por notificación. Puedes asignarlos después."
        acceptLabel={pending ? "Guardando…" : "Continuar"}
        pending={pending}
        onAccept={submitAssignment}
        onCancel={() => {
          if (!pending) setConfirmEmpty(false);
        }}
      />
    </section>
  );
}
