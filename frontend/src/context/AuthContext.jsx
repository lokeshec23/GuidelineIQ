import React, { createContext, useState, useContext, useEffect } from "react";
import { authAPI } from "../services/api";
import { showToast } from "../utils/toast";

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    // Check if user is logged in
    // Check sessionStorage first (current session), then localStorage (remembered session)
    let storedUser = sessionStorage.getItem("user");
    let token = sessionStorage.getItem("access_token");

    if (!storedUser || !token) {
      storedUser = localStorage.getItem("user");
      token = localStorage.getItem("access_token");
    }

    if (storedUser && token) {
      const parsedUser = JSON.parse(storedUser);
      setUser(parsedUser);
      setIsAdmin(parsedUser?.role === "admin");
    }
    setLoading(false);
  }, []);

  const login = async (email, password, rememberMe = false) => {
    try {
      const response = await authAPI.login({ email, password, remember_me: rememberMe });
      const { access_token, refresh_token, user } = response.data;

      const storage = rememberMe ? localStorage : sessionStorage;

      storage.setItem("access_token", access_token);
      storage.setItem("refresh_token", refresh_token);
      storage.setItem("user", JSON.stringify(user));

      setUser(user);
      setIsAdmin(user?.role === "admin");
      showToast.success("Login successful!");
      return true;
    } catch (error) {
      // Error toast is handled by API interceptor
      return false;
    }
  };

  const register = async (username, email, password) => {
    try {
      await authAPI.register({ username, email, password, role: "user" });
      showToast.success("Registration successful! Please login.");
      return true;
    } catch (error) {
      // Error toast is handled by API interceptor
      return false;
    }
  };

  const logout = () => {
    sessionStorage.removeItem("access_token");
    sessionStorage.removeItem("refresh_token");
    sessionStorage.removeItem("user");

    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
    setUser(null);
    setIsAdmin(false);
    showToast.info("Logged out successfully");
  };

  const value = React.useMemo(() => ({
    user,
    loading,
    login,
    register,
    logout,
    isAdmin
  }), [user, loading, isAdmin]);

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
