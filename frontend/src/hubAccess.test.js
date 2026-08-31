import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  ADMIN_NAV,
  ADMIN_ONLY_PATHS,
  OPERATOR_HOME,
  OPERATOR_NAV,
  isOperatorRole,
  showAdminQuota,
} from "./hubAccess.js";

describe("hubAccess", () => {
  it("operator nav is only Monitoreo and Perfil", () => {
    assert.deepEqual(
      OPERATOR_NAV.map((item) => item.label),
      ["Monitoreo", "Perfil"],
    );
    assert.equal(OPERATOR_HOME, "/monitoreo");
    for (const label of ["Salud", "Systems", "Operators", "Tipos", "Beats", "Glosario", "Consumo"]) {
      assert.equal(
        OPERATOR_NAV.some((item) => item.label === label),
        false,
        label,
      );
    }
  });

  it("admin-only paths redirect Operators away from Hub admin screens", () => {
    assert.deepEqual(ADMIN_ONLY_PATHS, [
      "/consumo",
      "/operators",
      "/systems",
      "/tipos",
      "/beats",
      "/glosario",
    ]);
    assert.equal(ADMIN_NAV.some((item) => item.to === "/beats"), true);
    assert.equal(OPERATOR_NAV.some((item) => item.to === "/beats"), false);
  });

  it("hides admin quota for Operator sessions", () => {
    const operator = {
      role: "operator",
      current_company: { trial_active: true, beats_remaining: 9000 },
    };
    const admin = {
      role: "admin",
      current_company: { trial_active: true, beats_remaining: 9000 },
    };
    assert.equal(isOperatorRole(operator), true);
    assert.equal(showAdminQuota(operator), false);
    assert.equal(showAdminQuota(admin), true);
    assert.equal(showAdminQuota({ role: "admin", current_company: {} }), false);
  });
});
