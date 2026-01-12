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

      // Show success message
      showToast.success("Login successful! Welcome back.");

      // Show info if remember me is enabled
      // if (rememberMe) {
      //   showToast.info("You'll stay logged in on this device.", { duration: 2000 });
      // }

      return true;
    } catch (error) {
      // Handle specific error cases
      const status = error.response?.status;
      const errorDetail = error.response?.data?.detail;

      if (status === 401) {
        showToast.error("Invalid email or password. Please try again.");
      } else if (status === 403) {
        showToast.error("Your account has been disabled. Please contact support.");
      } else if (status === 404) {
        showToast.error("Account not found. Please check your email or register.");
      } else if (status === 400) {
        showToast.error(errorDetail || "Invalid login credentials format.");
      } else if (status >= 500) {
        showToast.error("Server error. Please try again later.");
      } else if (error.message === "Network Error") {
        showToast.error("Network error. Please check your connection.");
      } else if (!error.response) {
        showToast.error("Unable to connect to server. Please try again.");
      }
      // For other errors, the API interceptor will handle it

      return false;
    }
  };

  const register = async (username, email, password) => {
    try {
      await authAPI.register({ username, email, password, role: "user" });
      showToast.success("Registration successful! Redirecting to login...", { duration: 2000 });
      return true;
    } catch (error) {
      // Handle specific error cases
      const status = error.response?.status;
      const errorDetail = error.response?.data?.detail;

      if (status === 409) {
        // Conflict - email or username already exists
        if (errorDetail?.toLowerCase().includes("email")) {
          showToast.error("This email is already registered. Please login instead.");
        } else if (errorDetail?.toLowerCase().includes("username")) {
          showToast.error("This username is already taken. Please choose another.");
        } else {
          showToast.error("Email or username already exists. Please try different credentials.");
        }
      } else if (status === 400) {
        // Validation error
        showToast.error(errorDetail || "Invalid registration data. Please check your inputs.");
      } else if (status >= 500) {
        showToast.error("Server error. Please try again later.");
      } else if (error.message === "Network Error") {
        showToast.error("Network error. Please check your connection.");
      } else if (!error.response) {
        showToast.error("Unable to connect to server. Please try again.");
      }
      // For other errors, the API interceptor will handle it

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
