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
    const storedUser = sessionStorage.getItem("user");
    const token = sessionStorage.getItem("access_token");

    if (storedUser && token) {
      const parsedUser = JSON.parse(storedUser);
      setUser(parsedUser);
      setIsAdmin(parsedUser?.role === "admin");
    }
    setLoading(false);
  }, []);

  const login = async (email, password) => {
    try {
      const response = await authAPI.login({ email, password });
      const { access_token, refresh_token, user } = response.data;

      sessionStorage.setItem("access_token", access_token);
      sessionStorage.setItem("refresh_token", refresh_token);
      sessionStorage.setItem("user", JSON.stringify(user));

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
    setUser(null);
    setIsAdmin(false);
    showToast.info("Logged out successfully");
  };

  return (
    <AuthContext.Provider
      value={{ user, loading, login, register, logout, isAdmin }}
    >
      {children}
    </AuthContext.Provider>
  );
};
