import { useRef } from "react";
import { StyleSheet, TextInput, View } from "react-native";
import { colors } from "../theme";

const LENGTH = 6;

function onlyDigits(value) {
  return String(value ?? "").replace(/\D/g, "");
}

export default function OtpInput({
  value,
  onChange,
  onComplete,
  disabled = false,
  invalid = false,
}) {
  const inputsRef = useRef([]);
  const digits = Array.from({ length: LENGTH }, (_, index) => value[index] ?? "");

  function focusAt(index) {
    const next = Math.max(0, Math.min(LENGTH - 1, index));
    inputsRef.current[next]?.focus();
  }

  function applyDigits(nextDigits) {
    const next = onlyDigits(nextDigits.join("")).slice(0, LENGTH);
    onChange(next);
    if (next.length === LENGTH && next !== value) {
      onComplete?.(next);
    }
    return next;
  }

  function handleChange(index, rawValue) {
    const raw = onlyDigits(rawValue);
    if (!raw) {
      const next = [...digits];
      next[index] = "";
      applyDigits(next);
      return;
    }
    if (raw.length > 1) {
      const next = [...digits];
      raw.split("").forEach((digit, offset) => {
        if (index + offset < LENGTH) {
          next[index + offset] = digit;
        }
      });
      const filled = applyDigits(next);
      focusAt(Math.min(filled.length, LENGTH) - 1);
      return;
    }
    const next = [...digits];
    next[index] = raw;
    applyDigits(next);
    if (index < LENGTH - 1) {
      focusAt(index + 1);
    }
  }

  function handleKeyPress(index, event) {
    if (event.nativeEvent.key !== "Backspace") {
      return;
    }
    if (digits[index]) {
      const next = [...digits];
      next[index] = "";
      applyDigits(next);
      return;
    }
    if (index > 0) {
      const next = [...digits];
      next[index - 1] = "";
      applyDigits(next);
      focusAt(index - 1);
    }
  }

  return (
    <View style={styles.row} accessibilityLabel="Código de verificación de 6 dígitos">
      {digits.map((digit, index) => (
        <TextInput
          key={index}
          ref={(el) => {
            inputsRef.current[index] = el;
          }}
          style={[styles.box, invalid && styles.invalid]}
          value={digit}
          onChangeText={(text) => handleChange(index, text)}
          onKeyPress={(event) => handleKeyPress(index, event)}
          keyboardType="number-pad"
          inputMode="numeric"
          textContentType={index === 0 ? "oneTimeCode" : "none"}
          autoComplete={index === 0 ? "one-time-code" : "off"}
          maxLength={index === 0 ? LENGTH : 1}
          editable={!disabled}
          selectTextOnFocus
          autoFocus={index === 0}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 8,
  },
  box: {
    flex: 1,
    minWidth: 0,
    backgroundColor: "#0b1017",
    borderColor: colors.line,
    borderWidth: 1,
    borderRadius: 8,
    color: colors.text,
    fontSize: 22,
    fontWeight: "700",
    textAlign: "center",
    paddingVertical: 12,
  },
  invalid: {
    borderColor: colors.danger,
  },
});
