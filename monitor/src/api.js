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

function detailMessage(data) {
  const detail = data?.detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  if (Array.isArray(detail) && typeof detail[0] === "string" && detail[0].trim()) {
    return detail[0];
  }
  return "";
}

function messageFromFailure(response, data) {
  const fromApi = detailMessage(data);
  if (fromApi) {
    return fromApi;
  }
  const status = response.status;
  if (status === 401 || status === 403) {
    return "No se pudo verificar el acceso.";
  }
  if (status === 404) {
    return "No se encontró el servicio de login en el Hub (404).";
  }
  if (status === 502 || status === 503 || status === 504) {
    return "El Hub no está disponible. Intenta de nuevo.";
  }
  if (status >= 500) {
    return "Error interno del Hub. Intenta de nuevo.";
  }
  if (status) {
    return `No se pudo completar la acción (${status}).`;
  }
  return "No se pudo completar la acción";
}

async function readJson(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(messageFromFailure(response, data));
    error.status = response.status;
    throw error;
  }
  return data;
}

function contactHubError() {
  return new Error("No se pudo contactar el Hub.");
}

export function requestOperatorOtp(email) {
  return fetch(`${hubUrl()}/api/monitor/auth/request-otp/`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email }),
  })
    .catch(() => {
      throw contactHubError();
    })
    .then(readJson);
}

export function verifyOperatorOtp(email, otp) {
  return fetch(`${hubUrl()}/api/monitor/auth/verify-otp/`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, otp }),
  })
    .catch(() => {
      throw contactHubError();
    })
    .then(readJson);
}

export function loginOperatorPassword(email, password) {
  return fetch(`${hubUrl()}/api/monitor/auth/login/`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  })
    .catch(() => {
      throw contactHubError();
    })
    .then(readJson);
}

export function fetchOperatorMe(token) {
  return fetch(`${hubUrl()}/api/monitor/auth/me/`, {
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${token}`,
    },
  })
    .catch(() => {
      throw contactHubError();
    })
    .then(readJson);
}

export function setOperatorPassword(token, payload) {
  return fetch(`${hubUrl()}/api/monitor/auth/password/`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  })
    .catch(() => {
      throw contactHubError();
    })
    .then(readJson);
}

export function listOperatorBeats(token) {
  return fetch(`${hubUrl()}/api/monitor/beats/`, {
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${token}`,
    },
  })
    .catch(() => {
      throw contactHubError();
    })
    .then(readJson);
}
