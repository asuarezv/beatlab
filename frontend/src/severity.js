export const SEVERITIES = [
  { value: "info", label: "Info" },
  { value: "aviso", label: "Aviso" },
  { value: "alerta", label: "Alerta" },
  { value: "critica", label: "Crítica" },
];

export const SEVERITY_LABELS = Object.fromEntries(
  SEVERITIES.map((item) => [item.value, item.label]),
);

export const SEVERITY_COLORS = {
  info: "#6ee7ff",
  aviso: "#f5c16c",
  alerta: "#ff9f6e",
  critica: "#ff6b6b",
};

export const TYPE_ICONS = [
  { value: "pulse", label: "Pulso" },
  { value: "alert", label: "Alerta" },
  { value: "check", label: "Ok" },
  { value: "error", label: "Error" },
  { value: "sync", label: "Sincronía" },
  { value: "cloud", label: "Nube" },
  { value: "server", label: "Servidor" },
  { value: "shield", label: "Escudo" },
  { value: "bell", label: "Aviso" },
  { value: "activity", label: "Actividad" },
];

export const TYPE_PALETTE = [
  "#6ee7ff",
  "#7dd3fc",
  "#a5b4fc",
  "#67e8f9",
  "#93c5fd",
  "#c4b5fd",
  "#5eead4",
  "#f5c16c",
  "#ff9f6e",
  "#ff6b6b",
];

export function severityLabel(value) {
  return SEVERITY_LABELS[value] || value || "Aviso";
}

export function severityColor(value) {
  return SEVERITY_COLORS[value] || SEVERITY_COLORS.aviso;
}

export function typeIconName(item) {
  return item?.beat_type_icon || item?.resolved_icon || item?.icon || "pulse";
}

export function typeColor(index) {
  return TYPE_PALETTE[index % TYPE_PALETTE.length];
}
