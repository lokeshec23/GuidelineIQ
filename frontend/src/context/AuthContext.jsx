import React, { createContext, useState, useContext, useEffect } from "react";
import { authAPI } from "../services/api";
import { message } from "antd";

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
      message.success("Login successful!");
      return true;
    } catch (error) {
      message.error(error.response?.data?.detail || "Login failed");
      return false;
    }
  };

  const register = async (username, email, password) => {
    try {
      await authAPI.register({ username, email, password, role: "user" });
      message.success("Registration successful! Please login.");
      return true;
    } catch (error) {
      message.error(error.response?.data?.detail || "Registration failed");
      return false;
    }
  };

  const logout = () => {
    sessionStorage.removeItem("access_token");
    sessionStorage.removeItem("refresh_token");
    sessionStorage.removeItem("user");
    setUser(null);
    setIsAdmin(false);
    message.info("Logged out successfully");
  };

  return (
    <AuthContext.Provider
      value={{ user, loading, login, register, logout, isAdmin }}
    >
      {children}
    </AuthContext.Provider>
  );
};
