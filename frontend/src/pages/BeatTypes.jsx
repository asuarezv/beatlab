import { useEffect, useState } from "react";
import { SeverityBadge, TypeIcon } from "../components/BeatIcons.jsx";
import { createBeatType, listBeatTypes, updateBeatType } from "../api.js";
import { SEVERITIES, TYPE_ICONS, typeIconName } from "../severity.js";

const EMPTY = { name: "", severity: "aviso", icon: "pulse" };

export default function BeatTypes() {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState("");

  async function refresh() {
    setItems(await listBeatTypes());
  }

  useEffect(() => {
    refresh().catch((err) => setError(err.message));
  }, []);

  function startEdit(item) {
    setEditingId(item.id);
    setForm({
      name: item.name,
      severity: item.severity || "aviso",
      icon: typeIconName(item),
    });
    setError("");
  }

  function resetForm() {
    setEditingId(null);
    setForm(EMPTY);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    try {
      const payload = {
        name: form.name.trim(),
        severity: form.severity,
        icon: form.icon,
      };
      if (editingId) {
        await updateBeatType(editingId, payload);
      } else {
        await createBeatType(payload);
      }
      resetForm();
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section>
      <h2>Tipos de Beat</h2>
      <form className="row type-form" onSubmit={handleSubmit}>
        <input
          placeholder="alerta, error, estado…"
          value={form.name}
          onChange={(e) => setForm((current) => ({ ...current, name: e.target.value }))}
          required
        />
        <select
          value={form.severity}
          onChange={(e) =>
            setForm((current) => ({ ...current, severity: e.target.value }))
          }
          aria-label="Severidad"
        >
          {SEVERITIES.map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
        </select>
        <select
          value={form.icon}
          onChange={(e) => setForm((current) => ({ ...current, icon: e.target.value }))}
          aria-label="Icono del tipo"
        >
          {TYPE_ICONS.map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
        </select>
        <button type="submit">{editingId ? "Guardar" : "Dar de alta"}</button>
        {editingId ? (
          <button type="button" className="secondary" onClick={resetForm}>
            Cancelar
          </button>
        ) : null}
      </form>
      {error ? <p className="error">{error}</p> : null}
      <ul className="list">
        {items.map((item) => (
          <li key={item.id} className="list-item">
            <span className="type-row">
              <TypeIcon
                name={typeIconName(item)}
                label={`Tipo ${item.name}`}
              />
              <strong>{item.name}</strong>
              <span className="muted">{item.slug}</span>
              <SeverityBadge severity={item.severity} label={item.severity_label} />
            </span>
            <span className="list-actions">
              <button type="button" className="secondary" onClick={() => startEdit(item)}>
                Editar
              </button>
            </span>
          </li>
        ))}
        {!items.length ? <li className="muted">Aún no hay tipos.</li> : null}
      </ul>
    </section>
  );
}
