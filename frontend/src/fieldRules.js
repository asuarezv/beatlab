export const COMPANY_NAME_ERROR =
  "El nombre de la empresa solo puede incluir letras, números, espacios y los símbolos & y -.";

export const USERNAME_ERROR =
  "El usuario solo puede incluir letras y números, sin espacios ni símbolos.";

const COMPANY_NAME_RE = /^[\p{L}\p{N} &-]+$/u;
const USERNAME_RE = /^[A-Za-z0-9]+$/;

export function isValidCompanyName(name) {
  return COMPANY_NAME_RE.test(name);
}

export function isValidUsername(username) {
  return USERNAME_RE.test(username);
}
