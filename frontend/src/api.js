function csrfToken() {
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

async function request(path, options = {}) {
  const headers = { Accept: "application/json", ...options.headers };
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    headers["X-CSRFToken"] = csrfToken();
  }
  const response = await fetch(path, {
    credentials: "same-origin",
    ...options,
    headers,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const firstField = Object.values(data).find(
      (value) => Array.isArray(value) && value.length,
    );
    const message =
      (typeof data.detail === "string" && data.detail) ||
      (Array.isArray(firstField) ? firstField[0] : "") ||
      "No se pudo completar la acción";
    const error = new Error(message);
    error.status = response.status;
    error.data = data;
    throw error;
  }
  return data;
}

export function fetchCsrf() {
  return request("/api/auth/csrf/");
}

export function fetchMe() {
  return request("/api/auth/me/");
}

export function login(username, password) {
  return request("/api/auth/login/", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function requestRegisterOtp(payload) {
  return request("/api/auth/register/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function confirmRegisterOtp(email, otp) {
  return request("/api/auth/register/verify/", {
    method: "POST",
    body: JSON.stringify({ email, otp }),
  });
}

export function fetchSalud() {
  return request("/api/salud/");
}

export function logout() {
  return request("/api/auth/logout/", { method: "POST", body: "{}" });
}

export function selectCompany(companyId) {
  return request("/api/auth/company/", {
    method: "POST",
    body: JSON.stringify({ company_id: companyId }),
  });
}

export function listCompanies() {
  return request("/api/companies/");
}

export function createCompany(name) {
  return request("/api/companies/", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function listOperators() {
  return request("/api/operators/");
}

export function createOperator(username, password) {
  return request("/api/operators/", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function listSystems() {
  return request("/api/systems/");
}

export function createSystem(name) {
  return request("/api/systems/", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function listBeatTypes() {
  return request("/api/beat-types/");
}

export function createBeatType(name) {
  return request("/api/beat-types/", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function listBeats() {
  return request("/api/beats/");
}

export function issueSystemJwt(systemId) {
  return request(`/api/systems/${systemId}/jwt/`, {
    method: "POST",
    body: "{}",
  });
}
