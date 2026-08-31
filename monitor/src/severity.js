export const SEVERITY_LABELS = {
  info: "Info",
  aviso: "Aviso",
  alerta: "Alerta",
  critica: "Crítica",
};

export const SEVERITY_COLORS = {
  info: "#6ee7ff",
  aviso: "#f5c16c",
  alerta: "#ff9f6e",
  critica: "#ff6b6b",
};

export const TYPE_ICON_MAP = {
  pulse: "pulse-outline",
  alert: "warning-outline",
  check: "checkmark-circle-outline",
  error: "close-circle-outline",
  sync: "sync-outline",
  cloud: "cloud-outline",
  server: "server-outline",
  shield: "shield-outline",
  bell: "notifications-outline",
  activity: "analytics-outline",
};

export const SEVERITY_ICON_MAP = {
  info: "information-circle",
  aviso: "warning",
  alerta: "alert-circle",
  critica: "flash",
};

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
  const key = item?.beat_type_icon || item?.resolved_icon || item?.icon || "pulse";
  return TYPE_ICON_MAP[key] || TYPE_ICON_MAP.pulse;
}

export function severityIconName(value) {
  return SEVERITY_ICON_MAP[value] || SEVERITY_ICON_MAP.aviso;
}

export function typeColor(index) {
  return TYPE_PALETTE[index % TYPE_PALETTE.length];
}
