import React, { createContext, useContext, useEffect, useState } from "react";
import { User } from "../types";
import { apiFetch, safeGetStorage, safeSetStorage, safeRemoveStorage } from "./api";

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  loading: true,
  login: () => {},
  logout: () => {},
  refreshUser: async () => {},
});

export const DEMO_USER: User = {
  user_id: "usr_caravan_01",
  email: "john@company.com",
  full_name: "John Doe",
  role: "CUSTOMER",
  organization_id: "org_01",
  organization_name: "Tech Solutions",
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(DEMO_USER);
  const [token, setToken] = useState<string | null>(() => safeGetStorage("caravan_token"));
  const [loading, setLoading] = useState(false);

  async function loadMe() {
    const savedToken = safeGetStorage("caravan_token");
    if (!savedToken) {
      setUser(DEMO_USER);
      setLoading(false);
      return;
    }
    try {
      const data = await apiFetch<any>("/api/v1/auth/me");
      setUser({
        user_id: data.user_id,
        email: data.email,
        full_name: data.email.split("@")[0],
        role: data.role,
        organization_id: data.organization_id,
        organization_name: data.organization?.name || "My Organization",
      });
    } catch {
      safeRemoveStorage("caravan_token");
      setToken(null);
      setUser(DEMO_USER);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadMe();
  }, []);

  const login = (newToken: string, newUser: User) => {
    safeSetStorage("caravan_token", newToken);
    setToken(newToken);
    setUser(newUser);
  };

  const logout = () => {
    safeRemoveStorage("caravan_token");
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        login,
        logout,
        refreshUser: loadMe,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
