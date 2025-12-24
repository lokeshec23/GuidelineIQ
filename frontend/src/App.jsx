import React, { Suspense, lazy } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import MainLayout from "./components/Layout/MainLayout";
import { PromptProvider } from "./context/PromptContext";
import { Spin } from "antd";
import { Toaster } from 'react-hot-toast';
import LoadingFallback from "./components/common/LoadingFallback";

// Lazy load page components
const LoginPage = lazy(() => import("./pages/Auth/LoginPage"));
const RegisterPage = lazy(() => import("./pages/Auth/RegisterPage"));
const DashboardPage = lazy(() => import("./pages/Dashboard/DashboardPage"));
const IngestPage = lazy(() => import("./pages/Ingest/IngestPage"));
const ComparePage = lazy(() => import("./pages/Compare/ComparePage"));
const SettingsPage = lazy(() => import("./pages/Settings/SettingsPage"));
const PromptsPage = lazy(() => import("./pages/Prompts/PromptsPage"));
const IngestionPromptPage = lazy(() => import("./pages/Prompts/IngestionPromptPage"));
const ComparisonPromptPage = lazy(() => import("./pages/Prompts/ComparisonPromptPage"));

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return <LoadingFallback />;
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
    return <LoadingFallback />;
  }

  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};

function AppRoutes() {
  return (
    <Suspense fallback={<LoadingFallback />}>
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
    </Suspense>
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
