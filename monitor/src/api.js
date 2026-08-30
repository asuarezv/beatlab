import Constants from "expo-constants";

/** Única fuente: `expo.extra.hubUrl` en app.json. */
export function hubUrl() {
  const extra = Constants.expoConfig?.extra || {};
  return (extra.hubUrl || "https://hub.nynusoft.com").replace(/\/$/, "");
}

export function monitorWsUrl(token) {
  const base = hubUrl().replace(/^http/, "ws");
  return `${base}/ws/monitor/?token=${encodeURIComponent(token)}`;
}

async function readJson(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message =
      (typeof data.detail === "string" && data.detail) ||
      "No se pudo completar la acción";
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  return data;
}

export function loginOperator(username, password) {
  return fetch(`${hubUrl()}/api/monitor/auth/login/`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ username, password }),
  }).then(readJson);
}

export function listOperatorBeats(token) {
  return fetch(`${hubUrl()}/api/monitor/beats/`, {
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${token}`,
    },
  }).then(readJson);
}
