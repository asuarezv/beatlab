import { useEffect, useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
} from "react-native";
import { StatusBar } from "expo-status-bar";
import { colors } from "../theme";
import { fetchOperatorMe, setOperatorPassword } from "../api";
import PasswordField from "../components/PasswordField";

export default function ProfileScreen({ session, onBack, onSession, onLogout }) {
  const [hasPassword, setHasPassword] = useState(
    Boolean(session.operator?.has_password),
  );
  const [currentPassword, setCurrentPassword] = useState("");
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [showCurrent, setShowCurrent] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showPassword2, setShowPassword2] = useState(false);
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [busy, setBusy] = useState(false);

  const pass = password.trim();
  const pass2 = password2.trim();
  const mismatch = Boolean(pass) && Boolean(pass2) && pass !== pass2;
  const canSubmit =
    Boolean(pass) &&
    pass.length >= 8 &&
    Boolean(pass2) &&
    pass === pass2 &&
    (!hasPassword || Boolean(currentPassword.trim()));

  useEffect(() => {
    let cancelled = false;
    fetchOperatorMe(session.token)
      .then((data) => {
        if (cancelled) return;
        setHasPassword(Boolean(data.operator?.has_password));
      })
      .catch((err) => {
        if (err.status === 401) {
          onLogout();
          return;
        }
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [session.token, onLogout]);

  async function handleSubmit() {
    const nextCurrent = currentPassword.trim();
    const nextPassword = password.trim();
    const nextPassword2 = password2.trim();
    setCurrentPassword(nextCurrent);
    setPassword(nextPassword);
    setPassword2(nextPassword2);
    if (!nextPassword || !nextPassword2) {
      setError("La contraseña nueva y la confirmación son obligatorias.");
      setOk("");
      return;
    }
    if (nextPassword !== nextPassword2) {
      setError("Las contraseñas no coinciden.");
      setOk("");
      return;
    }
    if (hasPassword && !nextCurrent) {
      setError("La contraseña actual y la nueva son obligatorias.");
      setOk("");
      return;
    }
    setError("");
    setOk("");
    setBusy(true);
    try {
      const payload = {
        password: nextPassword,
        password2: nextPassword2,
      };
      if (hasPassword) {
        payload.current_password = nextCurrent;
      }
      const data = await setOperatorPassword(session.token, payload);
      setHasPassword(true);
      setCurrentPassword("");
      setPassword("");
      setPassword2("");
      setOk(data.detail || "Contraseña actualizada.");
      onSession({
        ...session,
        operator: { ...session.operator, has_password: true },
      });
    } catch (err) {
      if (err.status === 401) {
        onLogout();
        return;
      }
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.wrap}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <StatusBar style="light" />
      <ScrollView
        contentContainerStyle={styles.scroll}
        keyboardShouldPersistTaps="handled"
      >
        <Pressable onPress={onBack} style={styles.back}>
          <Text style={styles.backText}>Volver</Text>
        </Pressable>
        <Text style={styles.eyebrow}>Monitor</Text>
        <Text style={styles.title}>Perfil</Text>
        <Text style={styles.lead}>
          {session.operator?.display_name}
          {session.operator?.email ? ` · ${session.operator.email}` : ""}
        </Text>
        <Text style={styles.section}>
          {hasPassword ? "Cambiar contraseña" : "Crear contraseña"}
        </Text>
        <Text style={styles.hint}>
          {hasPassword
            ? "Escribe la actual, la nueva y confírmala. Mínimo 8 caracteres."
            : "Aún no tienes contraseña. Defínela para entrar sin código. Mínimo 8 caracteres."}
        </Text>
        {hasPassword ? (
          <>
            <Text style={styles.label}>Contraseña actual</Text>
            <PasswordField
              value={currentPassword}
              onChangeText={setCurrentPassword}
              visible={showCurrent}
              onToggle={() => setShowCurrent((value) => !value)}
              autoComplete="password"
              textContentType="password"
            />
          </>
        ) : null}
        <Text style={styles.label}>Nueva contraseña</Text>
        <PasswordField
          value={password}
          onChangeText={setPassword}
          visible={showPassword}
          onToggle={() => setShowPassword((value) => !value)}
          invalid={mismatch}
          autoComplete="password-new"
          textContentType="newPassword"
        />
        <Text style={styles.label}>Confirmar contraseña</Text>
        <PasswordField
          value={password2}
          onChangeText={setPassword2}
          visible={showPassword2}
          onToggle={() => setShowPassword2((value) => !value)}
          invalid={mismatch}
          autoComplete="password-new"
          textContentType="newPassword"
        />
        {mismatch ? (
          <Text style={styles.error}>Las contraseñas no coinciden.</Text>
        ) : null}
        {error ? <Text style={styles.error}>{error}</Text> : null}
        {ok ? <Text style={styles.ok}>{ok}</Text> : null}
        <Pressable
          style={[styles.button, (!canSubmit || busy) && styles.disabled]}
          onPress={handleSubmit}
          disabled={!canSubmit || busy}
        >
          <Text style={styles.buttonText}>
            {busy
              ? "Guardando…"
              : hasPassword
                ? "Cambiar contraseña"
                : "Crear contraseña"}
          </Text>
        </Pressable>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flex: 1,
    backgroundColor: colors.bg,
  },
  scroll: {
    paddingHorizontal: 24,
    paddingTop: 56,
    paddingBottom: 40,
  },
  back: {
    alignSelf: "flex-start",
    marginBottom: 18,
  },
  backText: {
    color: colors.accent,
    fontWeight: "600",
  },
  eyebrow: {
    color: colors.accent,
    letterSpacing: 2.2,
    textTransform: "uppercase",
    fontSize: 11,
    marginBottom: 4,
  },
  title: {
    color: colors.text,
    fontSize: 28,
    fontWeight: "700",
  },
  lead: {
    color: colors.muted,
    marginTop: 8,
    marginBottom: 28,
  },
  section: {
    color: colors.text,
    fontSize: 18,
    fontWeight: "600",
    marginBottom: 8,
  },
  hint: {
    color: colors.muted,
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 16,
  },
  label: {
    color: colors.muted,
    marginBottom: 6,
    marginTop: 10,
  },
  error: {
    color: colors.danger,
    marginTop: 12,
  },
  ok: {
    color: colors.accent,
    marginTop: 12,
  },
  button: {
    marginTop: 22,
    backgroundColor: colors.accent,
    borderRadius: 8,
    paddingVertical: 14,
    alignItems: "center",
  },
  disabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: "#042028",
    fontWeight: "700",
    fontSize: 16,
  },
});
