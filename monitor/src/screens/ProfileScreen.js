import { useEffect, useRef, useState } from "react";
import {
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { StatusBar } from "expo-status-bar";
import { colors } from "../theme";
import {
  fetchOperatorMe,
  setOperatorPassword,
  updateOperatorProfile,
  verifyOperatorEmailChange,
} from "../api";
import OtpInput from "../components/OtpInput";
import PasswordField from "../components/PasswordField";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function ProfileScreen({ session, onBack, onSession, onLogout }) {
  const [firstName, setFirstName] = useState(session.operator?.first_name || "");
  const [lastName, setLastName] = useState(session.operator?.last_name || "");
  const [email, setEmail] = useState(session.operator?.email || "");
  const [profileError, setProfileError] = useState("");
  const [profileOk, setProfileOk] = useState("");
  const [profileBusy, setProfileBusy] = useState(false);
  const [step, setStep] = useState("form");
  const [pendingEmail, setPendingEmail] = useState("");
  const [otp, setOtp] = useState("");
  const verifyingRef = useRef(false);

  const [hasPassword, setHasPassword] = useState(
    Boolean(session.operator?.has_password),
  );
  const [currentPassword, setCurrentPassword] = useState("");
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [showCurrent, setShowCurrent] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showPassword2, setShowPassword2] = useState(false);
  const [passError, setPassError] = useState("");
  const [passBusy, setPassBusy] = useState(false);
  const [passwordChanged, setPasswordChanged] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);

  const first = firstName.trim();
  const last = lastName.trim();
  const nextEmail = email.trim();
  const savedEmail = (session.operator?.email || "").trim();
  const emailChanged = nextEmail.toLowerCase() !== savedEmail.toLowerCase();
  const emailInvalid = Boolean(nextEmail) && !EMAIL_RE.test(nextEmail);
  const canSaveProfile =
    Boolean(first) && Boolean(last) && Boolean(nextEmail) && EMAIL_RE.test(nextEmail);

  const pass = password.trim();
  const pass2 = password2.trim();
  const mismatch = Boolean(pass) && Boolean(pass2) && pass !== pass2;
  const canSubmitPassword =
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
        setFirstName(data.operator?.first_name || "");
        setLastName(data.operator?.last_name || "");
        setEmail(data.operator?.email || "");
      })
      .catch((err) => {
        if (err.status === 401) {
          onLogout();
          return;
        }
        if (!cancelled) setProfileError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [session.token, onLogout]);

  async function handleProfileSave() {
    const nextFirst = firstName.trim();
    const nextLast = lastName.trim();
    const nextMail = email.trim();
    setFirstName(nextFirst);
    setLastName(nextLast);
    setEmail(nextMail);
    if (!nextFirst || !nextLast || !nextMail) {
      setProfileOk("");
      setProfileError("El nombre, los apellidos y el correo son obligatorios.");
      return;
    }
    if (!EMAIL_RE.test(nextMail)) {
      setProfileOk("");
      setProfileError("El correo no es válido.");
      return;
    }
    setProfileError("");
    setProfileOk("");
    setProfileBusy(true);
    try {
      const data = await updateOperatorProfile(session.token, {
        first_name: nextFirst,
        last_name: nextLast,
        email: nextMail,
      });
      onSession({
        ...session,
        operator: { ...session.operator, ...data.operator },
      });
      if (data.pending_email) {
        setPendingEmail(data.pending_email);
        setEmail(data.pending_email);
        setOtp("");
        setStep("otp");
        return;
      }
      setProfileOk(data.detail || "Datos actualizados.");
    } catch (err) {
      if (err.status === 401) {
        onLogout();
        return;
      }
      setProfileError(err.message);
    } finally {
      setProfileBusy(false);
    }
  }

  async function verifyEmailOtp(code) {
    const next = String(code ?? otp).replace(/\D/g, "");
    setOtp(next);
    if (next.length !== 6) {
      setProfileError("Escribe el código de 6 dígitos que enviamos.");
      return;
    }
    if (verifyingRef.current) {
      return;
    }
    verifyingRef.current = true;
    setProfileError("");
    setProfileOk("");
    setProfileBusy(true);
    try {
      const data = await verifyOperatorEmailChange(
        session.token,
        pendingEmail,
        next,
      );
      onSession({
        ...session,
        operator: { ...session.operator, ...data.operator },
      });
      setEmail(data.operator?.email || pendingEmail);
      setPendingEmail("");
      setOtp("");
      setStep("form");
      setProfileOk(data.detail || "Datos actualizados.");
    } catch (err) {
      if (err.status === 401) {
        onLogout();
        return;
      }
      setProfileError(err.message);
    } finally {
      verifyingRef.current = false;
      setProfileBusy(false);
    }
  }

  async function handleResendEmailOtp() {
    setProfileError("");
    setProfileOk("");
    setProfileBusy(true);
    try {
      const data = await updateOperatorProfile(session.token, {
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        email: pendingEmail,
      });
      onSession({
        ...session,
        operator: { ...session.operator, ...data.operator },
      });
      if (data.pending_email) {
        setPendingEmail(data.pending_email);
        setOtp("");
      }
    } catch (err) {
      if (err.status === 401) {
        onLogout();
        return;
      }
      setProfileError(err.message);
    } finally {
      setProfileBusy(false);
    }
  }

  async function handlePasswordSubmit() {
    if (!canSubmitPassword) return;
    const nextCurrent = currentPassword.trim();
    const nextPassword = password.trim();
    const nextPassword2 = password2.trim();
    setCurrentPassword(nextCurrent);
    setPassword(nextPassword);
    setPassword2(nextPassword2);
    setPassError("");
    setPassBusy(true);
    try {
      const payload = {
        password: nextPassword,
        password2: nextPassword2,
      };
      if (hasPassword) {
        payload.current_password = nextCurrent;
      }
      await setOperatorPassword(session.token, payload);
      setCurrentPassword("");
      setPassword("");
      setPassword2("");
      setPasswordChanged(true);
    } catch (err) {
      if (err.status === 401) {
        onLogout();
        return;
      }
      setPassError(err.message);
    } finally {
      setPassBusy(false);
    }
  }

  async function handleAcceptLogout() {
    if (loggingOut) return;
    setLoggingOut(true);
    await onLogout();
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
        <Text style={styles.section}>Datos de la cuenta</Text>
        {step === "otp" ? (
          <>
            <Text style={styles.hint}>
              Enviamos un código a{" "}
              <Text style={styles.strong}>{pendingEmail}</Text>. El correo no
              cambia hasta que el código sea correcto.
            </Text>
            <Text style={styles.label}>Código</Text>
            <OtpInput
              value={otp}
              onChange={(next) => {
                setOtp(next);
                if (profileError) setProfileError("");
              }}
              onComplete={verifyEmailOtp}
              disabled={profileBusy}
              invalid={Boolean(profileError)}
            />
            {profileError ? <Text style={styles.error}>{profileError}</Text> : null}
            <Pressable
              style={[
                styles.button,
                (profileBusy || otp.length !== 6) && styles.disabled,
              ]}
              onPress={() => verifyEmailOtp(otp)}
              disabled={profileBusy || otp.length !== 6}
            >
              <Text style={styles.buttonText}>
                {profileBusy ? "Verificando…" : "Confirmar correo"}
              </Text>
            </Pressable>
            <Pressable
              style={styles.linkRow}
              disabled={profileBusy}
              onPress={handleResendEmailOtp}
            >
              <Text style={styles.linkText}>Reenviar código</Text>
            </Pressable>
            <Pressable
              style={styles.linkRow}
              disabled={profileBusy}
              onPress={() => {
                setOtp("");
                setProfileError("");
                setStep("form");
              }}
            >
              <Text style={styles.linkText}>Volver</Text>
            </Pressable>
          </>
        ) : (
          <>
            <Text style={styles.hint}>
              El nombre y los apellidos se guardan al momento. El correo nuevo
              se confirma con un código.
            </Text>
            <Text style={styles.label}>Nombre</Text>
            <TextInput
              style={styles.input}
              value={firstName}
              onChangeText={setFirstName}
              autoCapitalize="words"
              autoComplete="given-name"
              textContentType="givenName"
            />
            <Text style={styles.label}>Apellidos</Text>
            <TextInput
              style={styles.input}
              value={lastName}
              onChangeText={setLastName}
              autoCapitalize="words"
              autoComplete="family-name"
              textContentType="familyName"
            />
            <Text style={styles.label}>Correo</Text>
            <TextInput
              style={[styles.input, emailInvalid && styles.invalid]}
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="email-address"
              autoComplete="email"
              textContentType="emailAddress"
            />
            {profileError ? <Text style={styles.error}>{profileError}</Text> : null}
            {profileOk ? <Text style={styles.ok}>{profileOk}</Text> : null}
            <Pressable
              style={[
                styles.button,
                (!canSaveProfile || profileBusy) && styles.disabled,
              ]}
              onPress={handleProfileSave}
              disabled={!canSaveProfile || profileBusy}
            >
              <Text style={styles.buttonText}>
                {profileBusy
                  ? emailChanged
                    ? "Enviando código…"
                    : "Guardando…"
                  : emailChanged
                    ? "Enviar código"
                    : "Guardar datos"}
              </Text>
            </Pressable>
          </>
        )}
        <Text style={[styles.section, styles.sectionGap]}>
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
        {passError ? <Text style={styles.error}>{passError}</Text> : null}
        <Pressable
          style={[
            styles.button,
            (!canSubmitPassword || passBusy) && styles.disabled,
          ]}
          onPress={handlePasswordSubmit}
          disabled={!canSubmitPassword || passBusy}
        >
          <Text style={styles.buttonText}>
            {passBusy
              ? "Guardando…"
              : hasPassword
                ? "Actualizar contraseña"
                : "Crear contraseña"}
          </Text>
        </Pressable>
      </ScrollView>
      <Modal
        visible={passwordChanged}
        transparent
        animationType="fade"
        onRequestClose={handleAcceptLogout}
      >
        <View style={styles.modalBackdrop}>
          <View
            style={styles.modalCard}
            accessibilityRole="alert"
            accessibilityViewIsModal
          >
            <Text style={styles.modalEyebrow}>Perfil</Text>
            <Text style={styles.modalTitle}>Contraseña actualizada</Text>
            <Text style={styles.modalBody}>
              La contraseña se cambió. Inicia sesión de nuevo.
            </Text>
            <Pressable
              style={[styles.button, styles.modalButton, loggingOut && styles.disabled]}
              onPress={handleAcceptLogout}
              disabled={loggingOut}
            >
              <Text style={styles.buttonText}>
                {loggingOut ? "Saliendo…" : "Aceptar"}
              </Text>
            </Pressable>
          </View>
        </View>
      </Modal>
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
  sectionGap: {
    marginTop: 32,
  },
  hint: {
    color: colors.muted,
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 16,
  },
  strong: {
    color: colors.text,
    fontWeight: "600",
  },
  linkRow: {
    marginTop: 16,
    alignItems: "center",
  },
  linkText: {
    color: colors.accent,
    fontWeight: "600",
  },
  label: {
    color: colors.muted,
    marginBottom: 6,
    marginTop: 10,
  },
  input: {
    backgroundColor: "#0b1017",
    borderColor: colors.line,
    borderWidth: 1,
    borderRadius: 8,
    color: colors.text,
    paddingHorizontal: 12,
    paddingVertical: 12,
  },
  invalid: {
    borderColor: colors.danger,
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
  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(0, 0, 0, 0.62)",
    justifyContent: "center",
    paddingHorizontal: 24,
  },
  modalCard: {
    backgroundColor: colors.card,
    borderColor: colors.line,
    borderWidth: 1,
    borderRadius: 14,
    padding: 22,
  },
  modalEyebrow: {
    color: colors.accent,
    letterSpacing: 2.2,
    textTransform: "uppercase",
    fontSize: 11,
    marginBottom: 6,
  },
  modalTitle: {
    color: colors.text,
    fontSize: 22,
    fontWeight: "700",
  },
  modalBody: {
    color: colors.muted,
    fontSize: 15,
    lineHeight: 22,
    marginTop: 10,
  },
  modalButton: {
    marginTop: 20,
  },
});
