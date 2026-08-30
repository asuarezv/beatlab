import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, View } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import LoginScreen from "./src/screens/LoginScreen";
import BeatsScreen from "./src/screens/BeatsScreen";
import { colors } from "./src/theme";

const SESSION_KEY = "beatlab.monitor.session";

export default function App() {
  const [session, setSession] = useState(undefined);

  useEffect(() => {
    AsyncStorage.getItem(SESSION_KEY)
      .then((raw) => {
        if (!raw) {
          setSession(null);
          return;
        }
        setSession(JSON.parse(raw));
      })
      .catch(() => setSession(null));
  }, []);

  const handleLogin = useCallback(async (next) => {
    await AsyncStorage.setItem(SESSION_KEY, JSON.stringify(next));
    setSession(next);
  }, []);

  const handleLogout = useCallback(async () => {
    await AsyncStorage.removeItem(SESSION_KEY);
    setSession(null);
  }, []);

  if (session === undefined) {
    return (
      <View
        style={{
          flex: 1,
          backgroundColor: colors.bg,
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <ActivityIndicator color={colors.accent} />
      </View>
    );
  }

  if (!session) {
    return <LoginScreen onLogin={handleLogin} />;
  }

  return <BeatsScreen session={session} onLogout={handleLogout} />;
}
