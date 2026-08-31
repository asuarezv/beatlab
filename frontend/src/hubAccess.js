export const OPERATOR_HOME = "/monitoreo";

export const OPERATOR_NAV = [
  { to: "/monitoreo", end: true, label: "Monitoreo" },
  { to: "/perfil", label: "Perfil" },
];

export const ADMIN_NAV = [
  { to: "/", end: true, label: "Salud" },
  { to: "/systems", label: "Systems" },
  { to: "/operators", label: "Operators" },
  { to: "/tipos", label: "Tipos" },
  { to: "/beats", label: "Beats" },
  { to: "/glosario", label: "Glosario" },
  { to: "/perfil", label: "Perfil" },
];

export const ADMIN_ONLY_PATHS = [
  "/consumo",
  "/operators",
  "/systems",
  "/tipos",
  "/beats",
  "/glosario",
];

export function isOperatorRole(session) {
  return session?.role === "operator";
}

export function showAdminQuota(session) {
  return !isOperatorRole(session) && Boolean(session?.current_company?.trial_active);
}
