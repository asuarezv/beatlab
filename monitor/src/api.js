import Constants from "expo-constants";

export function defaultHubUrl() {
  const extra = Constants.expoConfig?.extra || {};
  return (extra.hubUrl || "https://hub.nynusoft.com").replace(/\/$/, "");
}

export function monitorWsUrl(hubUrl, token) {
  const base = hubUrl.replace(/\/$/, "").replace(/^http/, "ws");
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

export function loginOperator(hubUrl, username, password) {
  return fetch(`${hubUrl.replace(/\/$/, "")}/api/monitor/auth/login/`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ username, password }),
  }).then(readJson);
}

export function listOperatorBeats(hubUrl, token) {
  return fetch(`${hubUrl.replace(/\/$/, "")}/api/monitor/beats/`, {
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${token}`,
    },
  }).then(readJson);
}
