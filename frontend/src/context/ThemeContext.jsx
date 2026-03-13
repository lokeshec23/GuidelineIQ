import React, { createContext, useContext, useState, useEffect } from 'react';
import { ConfigProvider, theme } from 'antd';

const ThemeContext = createContext();

export const ThemeProvider = ({ children }) => {
  const [isDarkMode, setIsDarkMode] = useState(() => {
    return localStorage.getItem("theme") === "dark";
  });

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add("dark");
      localStorage.setItem("theme", "dark");
    } else {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("theme", "light");
    }
  }, [isDarkMode]);

  const toggleTheme = () => {
    if (!document.startViewTransition) {
      setIsDarkMode(prev => !prev);
      return;
    }
    document.startViewTransition(() => {
      setIsDarkMode(prev => !prev);
    });
  };

  // Map our premium colors to Ant Design tokens
  // Light mode: base is FAFAFA, surface is FFFFFF
  // Dark mode: base is 0B0E14, surface is 151921
  const antdTheme = {
    algorithm: isDarkMode ? theme.darkAlgorithm : theme.defaultAlgorithm,
    token: {
      colorPrimary: isDarkMode ? '#3B82F6' : '#2563EB',
      colorSuccess: '#10B981',
      colorBgBase: isDarkMode ? '#0F172A' : '#FAFAFA', // Deep slate base (no more pure black)
      colorBgContainer: isDarkMode ? '#1E293B' : '#FFFFFF', // Elevated surface
      colorBgElevated: isDarkMode ? '#334155' : '#FFFFFF', // Tooltips/dropdowns
      colorBgLayout: isDarkMode ? '#0F172A' : '#FAFAFA',
      colorTextBase: isDarkMode ? '#F8FAFC' : '#1E293B',
      fontFamily: '"Inter", "Jura", sans-serif',
      colorBorder: isDarkMode ? '#334155' : '#E2E8F0', // Visible subtle borders
      colorBorderSecondary: isDarkMode ? '#1E293B' : '#F1F5F9',
    },
    components: {
      Layout: {
        bodyBg: isDarkMode ? '#0F172A' : '#FAFAFA',
        headerBg: isDarkMode ? '#1E293B' : '#FFFFFF',
        siderBg: isDarkMode ? '#1E293B' : '#FAFAFA', // Align sidebar with header for unity
      },
      Table: {
        headerBg: isDarkMode ? '#334155' : '#F8FAFC', // slightly lighter for table headers
        headerColor: isDarkMode ? '#F8FAFC' : '#1E293B',
        rowHoverBg: isDarkMode ? '#334155' : '#F1F5F9',
        borderColor: isDarkMode ? '#334155' : '#E2E8F0',
      },
      Card: {
        colorBgContainer: isDarkMode ? '#1E293B' : '#FFFFFF',
        colorBorderSecondary: isDarkMode ? '#334155' : '#E2E8F0',
      }
    }
  };

  return (
    <ThemeContext.Provider value={{ isDarkMode, toggleTheme }}>
      <ConfigProvider theme={antdTheme}>
        {children}
      </ConfigProvider>
    </ThemeContext.Provider>
  );
};

export const useTheme = () => useContext(ThemeContext);
