import React, { useState } from "react";
import { Layout, Menu, Avatar, Dropdown, Button, Switch } from "antd";
import {
  FileTextOutlined,
  SwapOutlined,
  SettingOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  BellOutlined,
  LockOutlined,
  AppstoreOutlined,
  MessageOutlined,
  LikeOutlined,
  BulbOutlined,
  BulbFilled,
  ArrowRightOutlined,
  EditOutlined,
  TeamOutlined,
  SlidersOutlined,
} from "@ant-design/icons";
import { useAuth } from "../../context/AuthContext";
import { useTheme } from "../../context/ThemeContext";
import { useNavigate, useLocation } from "react-router-dom";

const { Header, Sider, Content } = Layout;

const MainLayout = ({ children }) => {
  const { user, logout, isAdmin } = useAuth();
  const { isDarkMode, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);

  // Detect mobile viewport
  React.useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= 768);
      if (window.innerWidth > 768) {
        setMobileDrawerOpen(false);
      }
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const handleLogout = React.useCallback(() => {
    logout();
    navigate("/login");
  }, [logout, navigate]);

  // User Profile Dropdown - Memoized to prevent re-renders
  const userProfileCard = React.useMemo(() => (
    <div className="bg-[var(--bg-surface)] rounded-2xl shadow-2xl w-72 overflow-hidden border border-[var(--color-border)] font-sans mt-2 animate-in fade-in slide-in-from-top-2 duration-300">
      <div className="h-24 bg-gradient-to-br from-[var(--color-accent)] to-[#4f46e5] relative overflow-hidden opacity-90">
        <div className="absolute -top-4 -right-4 w-24 h-24 bg-white/10 rounded-full blur-xl"></div>
        <div className="absolute top-4 right-12 w-8 h-8 bg-white/5 rounded-full blur-lg"></div>
      </div>
      <div className="px-6 pb-5">
        <div className="relative -mt-12 mb-4 flex justify-center">
          <div className="p-1.5 bg-[var(--bg-surface)] rounded-full shadow-md">
            <Avatar
              size={84}
              className="bg-[var(--bg-base)] text-[var(--text-primary)] text-4xl font-normal flex items-center justify-center border-2 border-[var(--bg-surface)]"
              src={user?.avatarUrl}
            >
              {user?.username?.[0]?.toUpperCase() || "M"}
            </Avatar>
          </div>
        </div>
        <div className="text-center mb-6">
          <h3 className="font-bold text-xl text-[var(--text-primary)] m-0 tracking-tight">
            {user?.username || "Admin"}
          </h3>
          <div className="flex items-center justify-center gap-1.5 text-[var(--text-secondary)] text-sm mt-1 font-medium bg-[var(--bg-base)] w-fit mx-auto px-3 py-0.5 rounded-full border border-[var(--color-border)]">
            <LockOutlined className="text-xs" />
            <span>{isAdmin ? "Admin" : "User"}</span>
          </div>
        </div>
        <div className="pt-4 border-t border-[var(--color-border)]">
          <Button
            type="text"
            icon={<LogoutOutlined />}
            onClick={handleLogout}
            className="w-full h-11 text-[var(--text-secondary)] flex items-center justify-center px-4 hover:bg-red-500/10 hover:text-red-500 font-semibold rounded-xl transition-all duration-200 border border-transparent hover:border-red-500/20"
          >
            Logout
          </Button>
        </div>
      </div>
    </div>
  ), [user, isAdmin, handleLogout]);

  // Menu Items Construction - Memoized
  const menuItems = React.useMemo(() => {
    const baseItems = [
      {
        key: "/dashboard",
        icon: <AppstoreOutlined />,
        label: "Dashboard",
      },
      {
        key: "/ingest",
        icon: <FileTextOutlined />,
        label: "Ingest Guidelines",
      },
      {
        key: "/compare",
        icon: <SwapOutlined />,
        label: "Compare Guidelines",
      },
      {
        key: "/ingestion-prompt",
        icon: <EditOutlined />,
        label: "Ingestion Prompt",
      },
      {
        key: "/comparison-prompt",
        icon: <EditOutlined />,
        label: "Comparison Prompt",
      },
      {
        key: "/config-parameters",
        icon: <SlidersOutlined />,
        label: "Config Parameters",
      },
      {
        key: "/management",
        icon: <TeamOutlined />,
        label: "Management",
      },
      // {
      //   key: "/settings",
      //   icon: <SettingOutlined />,
      //   label: "Settings",
      // },

    ];

    const accessibleItems = baseItems.filter(
      (item) => {
        if (item.key === "/ingestion-prompt" || item.key === "/comparison-prompt") {
          return false;
        }
        if ((item.key === "/management" || item.key === "/config-parameters") && !isAdmin) {
          return false;
        }
        return item.key !== "/settings" || isAdmin;
      }
    );


    return accessibleItems.map((item) => {
      const isActive = location.pathname === item.key;

      return {
        key: item.key,
        label: (
          <span className={`ml-1 transition-all duration-200 ${isActive ? "font-semibold text-[var(--color-accent)]" : "text-[var(--text-secondary)] hover:text-[var(--text-primary)]"}`}>
            {item.label}
          </span>
        ),
        icon: React.cloneElement(item.icon, { 
          style: { 
            fontSize: "20px",
            color: isActive ? "var(--color-accent)" : "var(--text-secondary)"
          } 
        }),
        className: `menu-item-refined ${isActive ? "menu-item-active" : ""}`,
      };
    });
  }, [isAdmin, location.pathname, collapsed]);

  return (
    <Layout className="h-screen overflow-hidden font-sans bg-base text-text-primary">
      {/* HEADER */}
      <Header
        className="bg-surface shadow-sm flex items-center justify-between px-6 fixed w-full z-20 border-b border-gray-200 dark:border-gray-800"
        style={{ paddingInline: "24px", height: "56px" }}
      >
        <div className="flex items-center gap-3">
          {isMobile && (
            <Button
              type="text"
              icon={<MenuUnfoldOutlined style={{ fontSize: "20px" }} />}
              onClick={() => setMobileDrawerOpen(true)}
              className="text-gray-600 hover:text-gray-900"
            />
          )}
          <div
            className="cursor-pointer flex items-center justify-center"
            onClick={() => navigate("/")}
          >
            <img
              src={isDarkMode ? "/GuidelineIQ Dark logo.svg" : "/gc_logo.svg"}
              alt="Logo"
              className="h-10 w-44 object-contain object-left"
            />
          </div>
        </div>

        <div className="flex items-center gap-5">
          <Switch
            checked={isDarkMode}
            onChange={toggleTheme}
            checkedChildren={<BulbFilled className="text-yellow-400" />}
            unCheckedChildren={<BulbOutlined className="text-white" />}
            className="theme-switch mt-1"
          />

          {/* <Badge count={3} size="small" offset={[-2, 2]} color="#1890ff">
            <Button
              type="text"
              shape="circle"
              icon={<BellOutlined style={{ fontSize: "18px" }} />}
              className="text-gray-500 hover:text-gray-700 flex items-center justify-center"
            />
          </Badge> */}

          <Dropdown
            popupRender={() => userProfileCard}
            placement="bottomRight"
            trigger={["click"]}
          >
            <div className="cursor-pointer hover:opacity-80 transition-opacity">
              <Avatar
                size={40}
                src={user?.avatarUrl}
                className="bg-gray-200 text-gray-600 border-2 border-white shadow-sm"
              >
                {user?.username?.[0]?.toUpperCase() || "M"}
              </Avatar>
            </div>
          </Dropdown>
        </div>
      </Header>

      <Layout style={{ marginTop: "56px", height: "calc(100vh - 56px)" }}>
        {/* SIDEBAR */}
        <Sider
          collapsible
          collapsed={collapsed}
          onCollapse={setCollapsed}
          trigger={null}
          width={260}
          collapsedWidth={80}
          style={{
            position: "fixed",
            left: isMobile ? (mobileDrawerOpen ? 0 : "-100%") : 0,
            top: "56px",
            height: "calc(100vh - 56px)",
            zIndex: isMobile ? 1000 : 10,
            background: "var(--bg-surface)",
            transition: "all 0.3s cubic-bezier(0.2, 0, 0, 1)",
          }}
          className="border-r border-gray-200 dark:border-gray-800 h-full flex flex-col justify-between sidebar-refined"
        >
          <div className="flex flex-col h-full bg-surface pb-6">
            {/* Collapse Toggle */}
            <div className="flex items-center justify-end p-4 h-14 mb-2">
              {!collapsed && !isMobile && (
                <span className="text-[var(--text-secondary)] text-xs mr-3 uppercase tracking-[0.1em] font-bold opacity-80">
                  Collapse
                </span>
              )}
              {!isMobile && (
                <Button
                  type="text"
                  size="small"
                  className="text-[var(--text-secondary)] hover:text-[var(--color-accent)] border border-[var(--color-border)] bg-[var(--bg-base)] shadow-sm hover:shadow-md transition-all duration-300"
                  icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                  onClick={() => setCollapsed(!collapsed)}
                />
              )}
              {isMobile && (
                <Button
                  type="text"
                  size="small"
                  className="text-gray-400 hover:text-gray-600 border border-gray-300 bg-white shadow-sm"
                  icon={<MenuFoldOutlined />}
                  onClick={() => setMobileDrawerOpen(false)}
                />
              )}
            </div>

            {/* Menu Items */}
            <div className="flex-grow overflow-y-auto custom-scrollbar px-1">
              <Menu
                mode="inline"
                inlineCollapsed={collapsed}
                selectedKeys={[location.pathname]}
                items={menuItems}
                onClick={({ key }) => navigate(key)}
                style={{ background: "transparent", borderRight: 0 }}
              />
            </div>

            {/* Footer Buttons */}
            {/* <div
              className={`p-4 border-t border-gray-200 bg-[#f9fafb] ${collapsed ? "px-2" : "px-4"
                }`}
            >
              <div
                className={`flex ${collapsed ? "flex-col gap-4 items-center" : "flex-row gap-3"
                  }`}
              >
                <Button
                  className={`flex items-center justify-center text-gray-500 border-gray-300 bg-white shadow-sm hover:border-blue-400 hover:text-blue-500 ${collapsed ? "w-10 h-10 rounded-full p-0" : "flex-1"
                    }`}
                  icon={<MessageOutlined />}
                >
                  {!collapsed && "Support"}
                </Button>
                <Button
                  className={`flex items-center justify-center text-gray-500 border-gray-300 bg-white shadow-sm hover:border-blue-400 hover:text-blue-500 ${collapsed ? "w-10 h-10 rounded-full p-0" : "flex-1"
                    }`}
                  icon={<LikeOutlined />}
                >
                  {!collapsed && "Feedback"}
                </Button>
              </div>
            </div> */}
          </div>
        </Sider>

        {/* Mobile Overlay */}
        {isMobile && mobileDrawerOpen && (
          <div
            className="fixed inset-0 bg-black bg-opacity-50 z-999"
            style={{ top: "56px" }}
            onClick={() => setMobileDrawerOpen(false)}
          />
        )}

        {/* MAIN CONTENT */}
        <Layout
          className="bg-base transition-all duration-300 ease-in-out"
          style={{
            marginLeft: isMobile ? 0 : (collapsed ? "80px" : "260px"),
            width: isMobile ? "100vw" : (collapsed ? "calc(100vw - 80px)" : "calc(100vw - 260px)")
          }}
        >
          <Content className="h-full overflow-y-auto p-8 bg-base">
            {children}
          </Content>
        </Layout>
      </Layout>
    </Layout>
  );
};

export default MainLayout;
