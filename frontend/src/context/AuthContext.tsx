import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

interface AuthContextValue {
  token: string | null;
  email: string | null;
  login: (token: string, email: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("pulse_token"));
  const [email, setEmail] = useState<string | null>(() => localStorage.getItem("pulse_email"));

  const login = (newToken: string, newEmail: string) => {
    localStorage.setItem("pulse_token", newToken);
    localStorage.setItem("pulse_email", newEmail);
    setToken(newToken);
    setEmail(newEmail);
  };

  const logout = () => {
    localStorage.removeItem("pulse_token");
    localStorage.removeItem("pulse_email");
    setToken(null);
    setEmail(null);
  };

  const value = useMemo(() => ({ token, email, login, logout }), [token, email]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
