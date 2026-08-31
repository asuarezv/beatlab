import { View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { colors } from "../theme";
import {
  severityColor,
  severityIconName,
  severityLabel,
  typeIconName,
} from "../severity";

export function BeatMarks({ item }) {
  const typeName = item.beat_type_name || "Tipo";
  const sev = item.severity || "aviso";
  const sevText = item.severity_label || severityLabel(sev);
  return (
    <View
      accessible
      accessibilityRole="image"
      accessibilityLabel={`${typeName}, severidad ${sevText}`}
      style={{ flexDirection: "row", alignItems: "center", gap: 6 }}
    >
      <Ionicons
        name={typeIconName(item)}
        size={20}
        color={colors.accent}
        accessibilityLabel={`Tipo ${typeName}`}
      />
      <Ionicons
        name={severityIconName(sev)}
        size={20}
        color={severityColor(sev)}
        accessibilityLabel={`Severidad ${sevText}`}
      />
    </View>
  );
}
