import { useEffect, useState } from "react";
import {
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { StatusBar } from "expo-status-bar";
import { colors } from "../theme";
import { listOperatorBeats, monitorWsUrl } from "../api";

function formatWhen(value) {
  if (!value) return "";
  try {
    return new Date(value).toLocaleString("es-MX");
  } catch {
    return String(value);
  }
}

export default function BeatsScreen({ session, onLogout, onProfile }) {
  const [items, setItems] = useState([]);
  const [live, setLive] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    listOperatorBeats(session.token)
      .then((data) => {
        if (!cancelled) setItems(Array.isArray(data) ? data : []);
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

  useEffect(() => {
    let closed = false;
    let socket;
    let retry;

    function connect() {
      if (closed) return;
      socket = new WebSocket(monitorWsUrl(session.token));
      socket.onopen = () => setLive(true);
      socket.onmessage = (event) => {
        let data;
        try {
          data = JSON.parse(event.data);
        } catch {
          return;
        }
        if (data.type === "beat" && data.beat) {
          setItems((prev) => {
            if (prev.some((item) => item.id === data.beat.id)) return prev;
            return [data.beat, ...prev];
          });
        }
      };
      socket.onerror = () => {};
      socket.onclose = () => {
        setLive(false);
        if (!closed) retry = setTimeout(connect, 3000);
      };
    }

    connect();
    return () => {
      closed = true;
      clearTimeout(retry);
      if (socket) socket.close();
    };
  }, [session.token]);

  return (
    <View style={styles.wrap}>
      <StatusBar style="light" />
      <View style={styles.top}>
        <View style={styles.brand}>
          <Text style={styles.eyebrow}>Monitor</Text>
          <Text style={styles.title} numberOfLines={1}>
            {session.company?.name || "Hub"}
          </Text>
          <Text style={styles.muted} numberOfLines={1}>
            {session.operator?.display_name} · {live ? "en vivo" : "reconectando"}
          </Text>
        </View>
        <View style={styles.actions}>
          <Pressable
            onPress={onProfile}
            accessibilityRole="button"
            accessibilityLabel="Perfil"
            hitSlop={8}
            style={styles.iconBtn}
          >
            <Ionicons
              name="person-circle-outline"
              size={26}
              color={colors.accent}
            />
          </Pressable>
          <Pressable
            onPress={onLogout}
            accessibilityRole="button"
            accessibilityLabel="Salir"
            hitSlop={8}
            style={styles.iconBtn}
          >
            <Ionicons name="log-out-outline" size={26} color={colors.accent} />
          </Pressable>
        </View>
      </View>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <FlatList
        data={items}
        keyExtractor={(item) => String(item.id)}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          <Text style={styles.empty}>Aún no hay Beats.</Text>
        }
        renderItem={({ item }) => (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>{item.title}</Text>
            <Text style={styles.muted}>
              {item.system_name} · {item.beat_type_name}
            </Text>
            <Text style={styles.when}>{formatWhen(item.created_at)}</Text>
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flex: 1,
    backgroundColor: colors.bg,
    paddingTop: 56,
  },
  top: {
    paddingHorizontal: 20,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: 12,
  },
  eyebrow: {
    color: colors.accent,
    letterSpacing: 2.2,
    textTransform: "uppercase",
    fontSize: 11,
    marginBottom: 4,
  },
  brand: {
    flex: 1,
    minWidth: 0,
  },
  title: {
    color: colors.text,
    fontSize: 24,
    fontWeight: "700",
  },
  muted: {
    color: colors.muted,
    marginTop: 4,
  },
  actions: {
    flexDirection: "row",
    alignItems: "center",
    flexShrink: 0,
    gap: 2,
  },
  iconBtn: {
    width: 40,
    height: 40,
    alignItems: "center",
    justifyContent: "center",
  },
  error: {
    color: colors.danger,
    paddingHorizontal: 20,
    marginTop: 12,
  },
  list: {
    padding: 20,
    gap: 12,
    flexGrow: 1,
  },
  empty: {
    color: colors.muted,
    marginTop: 24,
  },
  card: {
    backgroundColor: colors.card,
    borderColor: colors.line,
    borderWidth: 1,
    borderRadius: 14,
    padding: 16,
  },
  cardTitle: {
    color: colors.text,
    fontSize: 17,
    fontWeight: "600",
    marginBottom: 6,
  },
  when: {
    color: colors.muted,
    marginTop: 8,
    fontSize: 12,
  },
});
