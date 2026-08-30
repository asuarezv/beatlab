import { Pressable, StyleSheet, TextInput, View } from "react-native";
import { colors } from "../theme";

function EyeIcon({ off, color }) {
  return (
    <View style={iconStyles.box} accessibilityElementsHidden>
      <View style={[iconStyles.lid, { borderColor: color }]}>
        <View style={[iconStyles.pupil, { backgroundColor: color }]} />
      </View>
      {off ? (
        <View style={[iconStyles.slash, { backgroundColor: color }]} />
      ) : null}
    </View>
  );
}

export default function PasswordField({
  value,
  onChangeText,
  visible,
  onToggle,
  invalid = false,
  autoComplete = "password",
  textContentType = "password",
  placeholder,
}) {
  return (
    <View style={[styles.wrap, invalid && styles.invalid]}>
      <TextInput
        style={styles.input}
        value={value}
        onChangeText={onChangeText}
        autoCapitalize="none"
        autoCorrect={false}
        secureTextEntry={!visible}
        autoComplete={autoComplete}
        textContentType={textContentType}
        placeholder={placeholder}
        placeholderTextColor={colors.muted}
      />
      <Pressable
        onPress={onToggle}
        style={styles.toggle}
        accessibilityRole="button"
        accessibilityLabel={visible ? "Ocultar contraseña" : "Mostrar contraseña"}
      >
        <EyeIcon off={visible} color={colors.muted} />
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#0b1017",
    borderColor: colors.line,
    borderWidth: 1,
    borderRadius: 8,
  },
  invalid: {
    borderColor: colors.danger,
  },
  input: {
    flex: 1,
    color: colors.text,
    paddingHorizontal: 12,
    paddingVertical: 12,
  },
  toggle: {
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
});

const iconStyles = StyleSheet.create({
  box: {
    width: 22,
    height: 22,
    alignItems: "center",
    justifyContent: "center",
  },
  lid: {
    width: 18,
    height: 11,
    borderRadius: 9,
    borderWidth: 1.6,
    alignItems: "center",
    justifyContent: "center",
  },
  pupil: {
    width: 5,
    height: 5,
    borderRadius: 3,
  },
  slash: {
    position: "absolute",
    width: 20,
    height: 1.6,
    transform: [{ rotate: "-32deg" }],
  },
});
