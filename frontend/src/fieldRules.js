export const COMPANY_NAME_ERROR =
  "El nombre de la empresa solo puede incluir letras, números, espacios y los símbolos & y -.";

export const USERNAME_ERROR =
  "El usuario solo puede incluir letras y números, sin espacios ni símbolos.";

export const EMAIL_ERROR = "El correo no es válido.";

const COMPANY_NAME_RE = /^[\p{L}\p{N} &-]+$/u;
const USERNAME_RE = /^[A-Za-z0-9]+$/;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function isValidCompanyName(name) {
  return COMPANY_NAME_RE.test(name);
}

export function sanitizeUsername(value) {
  return String(value ?? "").replace(/\s/g, "");
}

export function isValidUsername(username) {
  return USERNAME_RE.test(username);
}

export function isValidEmail(email) {
  return EMAIL_RE.test(email);
}
