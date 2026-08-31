import { StyleSheet, Text, View } from "react-native";
import { colors } from "../theme";
import { SEVERITY_COLORS, typeColor } from "../severity";

function maxOf(rows, key) {
  return Math.max(1, ...rows.map((row) => Number(row[key] || 0)));
}

function BarList({ rows, valueKey, colorFor }) {
  const max = maxOf(rows, valueKey);
  return (
    <View style={styles.bars}>
      {rows.map((row, index) => {
        const value = Number(row[valueKey] || 0);
        const width = `${Math.max(4, Math.round((value / max) * 100))}%`;
        return (
          <View key={row.key || row.name} style={styles.barRow}>
            <Text style={styles.barLabel} numberOfLines={1}>
              {row.name}
            </Text>
            <View style={styles.barTrack}>
              <View
                style={[
                  styles.barFill,
                  { width, backgroundColor: colorFor(row, index) },
                ]}
              />
            </View>
            <Text style={styles.barValue}>{value}</Text>
          </View>
        );
      })}
    </View>
  );
}

function Stack({ rows, colorFor }) {
  const total = rows.reduce((sum, row) => sum + Number(row.value || 0), 0);
  if (!total) return null;
  return (
    <View>
      <View style={styles.stack}>
        {rows.map((row, index) => (
          <View
            key={row.key || row.name}
            style={{
              flex: Number(row.value || 0),
              backgroundColor: colorFor(row, index),
              minWidth: 4,
            }}
          />
        ))}
      </View>
      <View style={styles.legend}>
        {rows.map((row, index) => (
          <Text key={row.key || row.name} style={styles.legendItem}>
            <Text style={{ color: colorFor(row, index) }}>● </Text>
            {row.name} {row.value}
          </Text>
        ))}
      </View>
    </View>
  );
}

export default function BeatCharts({ stats }) {
  const total = Number(stats?.beats_total || 0);
  if (!total) {
    return <Text style={styles.empty}>Aún no hay Beats</Text>;
  }

  const byType = (stats.by_type || []).map((row, index) => ({
    key: String(row.id),
    name: row.name,
    value: row.consumed,
    color: typeColor(index),
  }));
  const bySeverity = (stats.by_severity || [])
    .filter((row) => row.consumed > 0)
    .map((row) => ({
      key: row.severity,
      name: row.label,
      value: row.consumed,
      color: SEVERITY_COLORS[row.severity] || colors.muted,
    }));
  const days = (stats.by_day || []).map((row) => ({
    key: row.date,
    name: String(row.date).slice(8),
    value: row.total,
  }));
  const dayMax = maxOf(days, "value");

  return (
    <View style={styles.wrap}>
      <View style={styles.card}>
        <Text style={styles.eyebrow}>Volumen por tipo</Text>
        <BarList
          rows={byType.map((row) => ({ ...row, consumed: row.value }))}
          valueKey="consumed"
          colorFor={(row) => row.color}
        />
      </View>
      <View style={styles.card}>
        <Text style={styles.eyebrow}>Beats en el tiempo</Text>
        <View style={styles.timeline}>
          {days.map((row) => (
            <View key={row.key} style={styles.dayCol}>
              <View style={styles.dayTrack}>
                <View
                  style={[
                    styles.dayFill,
                    {
                      height: `${Math.max(6, Math.round((row.value / dayMax) * 100))}%`,
                    },
                  ]}
                />
              </View>
              <Text style={styles.dayLabel}>{row.name}</Text>
            </View>
          ))}
        </View>
      </View>
      <View style={styles.card}>
        <Text style={styles.eyebrow}>Distribución por tipo</Text>
        <Stack rows={byType.filter((row) => row.value > 0)} colorFor={(row) => row.color} />
      </View>
      <View style={styles.card}>
        <Text style={styles.eyebrow}>Distribución por severidad</Text>
        <Stack rows={bySeverity} colorFor={(row) => row.color} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    gap: 12,
    marginBottom: 8,
  },
  empty: {
    color: colors.muted,
    marginBottom: 8,
  },
  card: {
    backgroundColor: colors.card,
    borderColor: colors.line,
    borderWidth: 1,
    borderRadius: 14,
    padding: 14,
    gap: 10,
  },
  eyebrow: {
    color: colors.accent,
    letterSpacing: 1.6,
    textTransform: "uppercase",
    fontSize: 11,
  },
  bars: {
    gap: 8,
  },
  barRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  barLabel: {
    color: colors.text,
    width: 78,
    fontSize: 12,
  },
  barTrack: {
    flex: 1,
    height: 8,
    borderRadius: 99,
    backgroundColor: colors.bg,
    overflow: "hidden",
  },
  barFill: {
    height: 8,
    borderRadius: 99,
  },
  barValue: {
    color: colors.muted,
    width: 28,
    textAlign: "right",
    fontSize: 12,
  },
  stack: {
    flexDirection: "row",
    height: 14,
    borderRadius: 99,
    overflow: "hidden",
    backgroundColor: colors.bg,
  },
  legend: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
    marginTop: 8,
  },
  legendItem: {
    color: colors.muted,
    fontSize: 12,
  },
  timeline: {
    flexDirection: "row",
    alignItems: "flex-end",
    height: 92,
    gap: 3,
  },
  dayCol: {
    flex: 1,
    alignItems: "center",
    height: "100%",
  },
  dayTrack: {
    flex: 1,
    width: "100%",
    justifyContent: "flex-end",
    backgroundColor: colors.bg,
    borderRadius: 4,
    overflow: "hidden",
  },
  dayFill: {
    width: "100%",
    backgroundColor: colors.accent,
    borderRadius: 4,
  },
  dayLabel: {
    color: colors.muted,
    fontSize: 9,
    marginTop: 4,
  },
});
