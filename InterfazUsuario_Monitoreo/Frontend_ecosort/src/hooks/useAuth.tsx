import React, { createContext, useContext, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';

interface AuthContextType {
  token: string | null;
  login: (token: string, cb: () => void) => void;
  logout: (cb: () => void) => void;
}

const AuthContext = createContext<AuthContextType>(null!);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(localStorage.getItem('ecosort_token'));

  const login = (newToken: string, callback: () => void) => {
    setToken(newToken);
    localStorage.setItem('ecosort_token', newToken);
    callback();
  };

  const logout = (callback: () => void) => {
    setToken(null);
    localStorage.removeItem('ecosort_token');
    callback();
  };

  const value = { token, login, logout };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const auth = useAuth();
  const location = useLocation();

  if (!auth.token) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
} 