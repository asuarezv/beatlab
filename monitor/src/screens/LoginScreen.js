import { useRef, useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { StatusBar } from "expo-status-bar";
import { colors } from "../theme";
import { requestOperatorOtp, verifyOperatorOtp } from "../api";
import OtpInput from "../components/OtpInput";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function LoginScreen({ onLogin }) {
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [step, setStep] = useState("email");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const verifyingRef = useRef(false);

  async function handleRequest() {
    const nextEmail = email.trim();
    setEmail(nextEmail);
    if (!nextEmail) {
      setError("El correo es obligatorio.");
      return;
    }
    if (!EMAIL_RE.test(nextEmail)) {
      setError("El correo no es válido.");
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
      const data = await verifyOperatorOtp(email.trim(), next);
      onLogin({
        token: data.token,
        operator: data.operator,
        company: data.company,
      });
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
      <Text style={styles.eyebrow}>BeatLab</Text>
      <Text style={styles.title}>Monitor</Text>
      {step === "email" ? (
        <>
          <Text style={styles.lead}>
            Entra con el correo que te dio de alta el Hub. Te enviamos un
            código de 6 dígitos.
          </Text>
          <Text style={styles.label}>Correo</Text>
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
          {error ? <Text style={styles.error}>{error}</Text> : null}
          <Pressable
            style={[styles.button, busy && styles.disabled]}
            onPress={handleRequest}
            disabled={busy}
          >
            <Text style={styles.buttonText}>
              {busy ? "Enviando…" : "Enviar código"}
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
            style={[styles.button, (busy || otp.length !== 6) && styles.disabled]}
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
      <View style={{ height: 24 }} />
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flex: 1,
    backgroundColor: colors.bg,
    paddingHorizontal: 24,
    paddingTop: 72,
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
