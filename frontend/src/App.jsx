import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import MainLayout from "./components/Layout/MainLayout";
import LoginPage from "./pages/Auth/LoginPage";
import RegisterPage from "./pages/Auth/RegisterPage";
import DashboardPage from "./pages/Dashboard/DashboardPage";
import IngestPage from "./pages/Ingest/IngestPage";
import ComparePage from "./pages/Compare/ComparePage";
import SettingsPage from "./pages/Settings/SettingsPage";
import PromptsPage from "./pages/Prompts/PromptsPage";
import IngestionPromptPage from "./pages/Prompts/IngestionPromptPage";
import ComparisonPromptPage from "./pages/Prompts/ComparisonPromptPage";
import { PromptProvider } from "./context/PromptContext";
import { Spin } from "antd";
import { Toaster } from 'react-hot-toast';

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Spin size="large" tip="Loading..." />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <MainLayout>{children}</MainLayout>;
};

// Public Route Component (redirect if logged in)
const PublicRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Spin size="large" tip="Loading..." />
      </div>
    );
  }

  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};

function AppRoutes() {
  return (
    <Routes>
      {/* Public Routes */}
      <Route
        path="/login"
        element={
          <PublicRoute>
            <LoginPage />
          </PublicRoute>
        }
      />
      <Route
        path="/register"
        element={
          <PublicRoute>
            <RegisterPage />
          </PublicRoute>
        }
      />

      {/* Protected Routes */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/ingest"
        element={
          <ProtectedRoute>
            <IngestPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/compare"
        element={
          <ProtectedRoute>
            <ComparePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <SettingsPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/prompts"
        element={
          <ProtectedRoute>
            <PromptsPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/ingestion-prompt"
        element={
          <ProtectedRoute>
            <IngestionPromptPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/comparison-prompt"
        element={
          <ProtectedRoute>
            <ComparisonPromptPage />
          </ProtectedRoute>
        }
      />

      {/* Redirect root to dashboard */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />

      {/* 404 */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <PromptProvider>
          <AppRoutes />
          <Toaster
            position="bottom-right"
            reverseOrder={false}
            gutter={8}
            containerStyle={{
              bottom: 20,
              right: 20,
            }}
            toastOptions={{
              // Default options for all toasts
              duration: 3000,
              style: {
                borderRadius: '8px',
                background: '#333',
                color: '#fff',
                padding: '12px 16px',
                fontSize: '14px',
                maxWidth: '500px',
              },
              // Specific options for success toasts
              success: {
                duration: 3000,
                iconTheme: {
                  primary: '#10b981',
                  secondary: '#fff',
                },
              },
              // Specific options for error toasts
              error: {
                duration: 4000,
                iconTheme: {
                  primary: '#ef4444',
                  secondary: '#fff',
                },
              },
            }}
          />
        </PromptProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
