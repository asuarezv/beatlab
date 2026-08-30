import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, View } from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import LoginScreen from "./src/screens/LoginScreen";
import BeatsScreen from "./src/screens/BeatsScreen";
import ProfileScreen from "./src/screens/ProfileScreen";
import { colors } from "./src/theme";

const SESSION_KEY = "beatlab.monitor.session";

export default function App() {
  const [session, setSession] = useState(undefined);
  const [screen, setScreen] = useState("beats");

  useEffect(() => {
    AsyncStorage.getItem(SESSION_KEY)
      .then((raw) => {
        if (!raw) {
          setSession(null);
          return;
        }
        const parsed = JSON.parse(raw);
        delete parsed.hubUrl;
        setSession(parsed);
        AsyncStorage.setItem(SESSION_KEY, JSON.stringify(parsed));
      })
      .catch(() => setSession(null));
  }, []);

  const persistSession = useCallback(async (next) => {
    const rest = { ...next };
    delete rest.hubUrl;
    await AsyncStorage.setItem(SESSION_KEY, JSON.stringify(rest));
    setSession(rest);
  }, []);

  const handleLogin = useCallback(
    async (next) => {
      await persistSession(next);
      setScreen("beats");
    },
    [persistSession],
  );

  const handleLogout = useCallback(async () => {
    await AsyncStorage.removeItem(SESSION_KEY);
    setSession(null);
    setScreen("beats");
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

  if (screen === "profile") {
    return (
      <ProfileScreen
        session={session}
        onBack={() => setScreen("beats")}
        onSession={persistSession}
        onLogout={handleLogout}
      />
    );
  }

  return (
    <BeatsScreen
      session={session}
      onLogout={handleLogout}
      onProfile={() => setScreen("profile")}
    />
  );
}
