import { useRef, useState } from "react";
import {
  Image,
  KeyboardAvoidingView,
  Linking,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
} from "react-native";
import { StatusBar } from "expo-status-bar";
import { colors } from "../theme";
import {
  loginOperatorPassword,
  recoverAccountUrl,
  requestOperatorOtp,
  verifyOperatorOtp,
} from "../api";
import OtpInput from "../components/OtpInput";
import PasswordField from "../components/PasswordField";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const USERNAME_RE = /^[A-Za-z0-9]+$/;

export default function LoginScreen({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [otp, setOtp] = useState("");
  const [step, setStep] = useState("email");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const verifyingRef = useRef(false);

  function applySession(data) {
    onLogin({
      token: data.token,
      operator: data.operator,
      company: data.company,
    });
  }

  function validEmail(nextEmail, { forOtp = false } = {}) {
    if (!nextEmail) {
      setError("El correo es obligatorio.");
      return false;
    }
    if (EMAIL_RE.test(nextEmail)) {
      return true;
    }
    if (!forOtp && USERNAME_RE.test(nextEmail)) {
      return true;
    }
    setError(forOtp ? "El correo no es válido." : "El correo o el usuario no es válido.");
    return false;
  }

  async function handlePasswordLogin() {
    const nextEmail = email.trim();
    const nextPassword = password.trim();
    setEmail(nextEmail);
    setPassword(nextPassword);
    if (!validEmail(nextEmail)) {
      return;
    }
    if (!nextPassword) {
      setError("El correo y la contraseña son obligatorios.");
      return;
    }
    setError("");
    setBusy(true);
    try {
      applySession(await loginOperatorPassword(nextEmail, nextPassword));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleRequest() {
    const nextEmail = email.trim();
    setEmail(nextEmail);
    if (!validEmail(nextEmail, { forOtp: true })) {
      return;
    }
    setError("");
    setBusy(true);
    try {
      await requestOperatorOtp(nextEmail);
      setOtp("");
      setStep("otp");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function verifyOtp(code) {
    const next = String(code ?? otp).replace(/\D/g, "");
    setOtp(next);
    if (next.length !== 6) {
      setError("Escribe el código de 6 dígitos que te enviamos.");
      return;
    }
    if (verifyingRef.current) {
      return;
    }
    verifyingRef.current = true;
    setError("");
    setBusy(true);
    try {
      applySession(await verifyOperatorOtp(email.trim(), next));
    } catch (err) {
      setError(err.message);
    } finally {
      verifyingRef.current = false;
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
        <Image
          source={require("../assets/nynusoft-logo.png")}
          style={styles.logo}
          resizeMode="contain"
          accessibilityLabel="NynuSoft"
        />
        <Text style={styles.eyebrow}>BeatLab</Text>
        <Text style={styles.title}>Monitor</Text>
        {step === "email" ? (
          <>
            <Text style={styles.lead}>
              Entra con tu correo y contraseña, o te enviamos un código de 6
              dígitos.
            </Text>
            <Text style={styles.label}>Correo o usuario</Text>
            <TextInput
              style={styles.input}
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="email-address"
              autoComplete="email"
              textContentType="emailAddress"
            />
            <Text style={styles.label}>Contraseña</Text>
            <PasswordField
              value={password}
              onChangeText={setPassword}
              visible={showPassword}
              onToggle={() => setShowPassword((value) => !value)}
              autoComplete="password"
              textContentType="password"
            />
            {error ? <Text style={styles.error}>{error}</Text> : null}
            <Pressable
              style={[styles.button, busy && styles.disabled]}
              onPress={handlePasswordLogin}
              disabled={busy}
            >
              <Text style={styles.buttonText}>
                {busy ? "Entrando…" : "Entrar"}
              </Text>
            </Pressable>
            <Pressable
              style={styles.back}
              disabled={busy}
              onPress={() => Linking.openURL(recoverAccountUrl())}
            >
              <Text style={styles.backText}>Recuperar cuenta</Text>
            </Pressable>
            <Pressable
              style={styles.back}
              disabled={busy}
              onPress={handleRequest}
            >
              <Text style={styles.backText}>
                {busy ? "Enviando…" : "Entrar con un código"}
              </Text>
            </Pressable>
          </>
        ) : (
          <>
            <Text style={styles.lead}>
              Enviamos un código a <Text style={styles.strong}>{email}</Text>.
            </Text>
            <Text style={styles.label}>Código</Text>
            <OtpInput
              value={otp}
              onChange={(next) => {
                setOtp(next);
                if (error) setError("");
              }}
              onComplete={verifyOtp}
              disabled={busy}
              invalid={Boolean(error)}
            />
            {error ? <Text style={styles.error}>{error}</Text> : null}
            <Pressable
              style={[
                styles.button,
                (busy || otp.length !== 6) && styles.disabled,
              ]}
              onPress={() => verifyOtp(otp)}
              disabled={busy || otp.length !== 6}
            >
              <Text style={styles.buttonText}>
                {busy ? "Verificando…" : "Entrar"}
              </Text>
            </Pressable>
            <Pressable
              style={styles.back}
              disabled={busy}
              onPress={() => {
                setOtp("");
                setError("");
                setStep("email");
              }}
            >
              <Text style={styles.backText}>Volver</Text>
            </Pressable>
          </>
        )}
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
    paddingTop: 72,
    paddingBottom: 32,
  },
  logo: {
    width: 174,
    height: 36,
    marginBottom: 28,
  },
  eyebrow: {
    color: colors.accent,
    letterSpacing: 2.4,
    textTransform: "uppercase",
    fontSize: 12,
    marginBottom: 6,
  },
  title: {
    color: colors.text,
    fontSize: 32,
    fontWeight: "700",
    marginBottom: 8,
  },
  lead: {
    color: colors.muted,
    fontSize: 15,
    lineHeight: 22,
    marginBottom: 28,
  },
  strong: {
    color: colors.text,
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
  error: {
    color: colors.danger,
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
  back: {
    marginTop: 18,
    alignItems: "center",
  },
  backText: {
    color: colors.accent,
    fontWeight: "600",
  },
});
