import React, { useState } from "react";
import { Layout, Menu, Avatar, Dropdown, Badge, Button } from "antd";
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
  ArrowRightOutlined,
  EditOutlined,
} from "@ant-design/icons";
import { useAuth } from "../../context/AuthContext";
import { useNavigate, useLocation } from "react-router-dom";

const { Header, Sider, Content } = Layout;

const MainLayout = ({ children }) => {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  const handleLogout = React.useCallback(() => {
    logout();
    navigate("/login");
  }, [logout, navigate]);

  // User Profile Dropdown - Memoized to prevent re-renders
  const userProfileCard = React.useMemo(() => (
    <div className="bg-white rounded-xl shadow-lg w-72 overflow-hidden border border-gray-100 font-sans mt-2">
      <div className="h-20 bg-sky-50 relative overflow-hidden">
        <div className="absolute -top-2 -right-2 w-16 h-16 bg-sky-100 rounded-full opacity-50"></div>
        <div className="absolute top-2 right-8 w-4 h-4 bg-sky-200 rounded-full opacity-50"></div>
      </div>
      <div className="px-6 pb-4">
        <div className="relative -mt-10 mb-3 flex justify-center">
          <div className="p-1 bg-white rounded-full">
            <Avatar
              size={72}
              className="bg-gray-100 text-gray-700 text-3xl font-normal flex items-center justify-center shadow-sm"
              src={user?.avatarUrl}
            >
              {user?.username?.[0]?.toUpperCase() || "M"}
            </Avatar>
          </div>
        </div>
        <div className="text-center mb-6">
          <h3 className="font-semibold text-lg text-gray-900 m-0">
            {user?.username || "Michael Brown"}
          </h3>
          <div className="flex items-center justify-center gap-1 text-gray-500 text-sm mt-1">
            <LockOutlined className="text-xs" />
            <span>{isAdmin ? "Admin" : "User"}</span>
          </div>
        </div>
        <div className="pt-2 border-t border-gray-100">
          <Button
            type="text"
            danger
            icon={<LogoutOutlined />}
            onClick={handleLogout}
            className="w-full text-left flex items-center justify-start px-2 hover:bg-red-50 font-medium"
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
        key: "/settings",
        icon: <SettingOutlined />,
        label: "Settings",
      },
    ];

    const accessibleItems = baseItems.filter(
      (item) => item.key !== "/settings" && item.key !== "/ingestion-prompt" && item.key !== "/comparison-prompt" || isAdmin
    );

    return accessibleItems.map((item) => {
      const isActive = location.pathname === item.key;

      return {
        key: item.key,
        label: (
          <div className="flex items-center justify-between w-full">
            <span className={isActive ? "font-medium text-gray-900" : ""}>
              {item.label}
            </span>
            {isActive && !collapsed && (
              <ArrowRightOutlined
                className="text-[#1890ff]"
                style={{ fontSize: "12px" }}
              />
            )}
          </div>
        ),
        icon: (
          <div
            className={`flex items-center justify-center w-8 h-8 rounded-full transition-colors duration-200 bg-gray-200 text-gray-500 group-hover:bg-gray-300`}
          >
            {React.cloneElement(item.icon, { style: { fontSize: "15px" } })}
          </div>
        ),
        className: `mb-2 mx-3 rounded-lg transition-all duration-200 ${isActive
          ? "bg-white shadow-sm border border-gray-100"
          : "bg-transparent hover:bg-gray-200/50 text-gray-600"
          }`,
      };
    });
  }, [isAdmin, location.pathname, collapsed]);

  return (
    <Layout className="h-screen overflow-hidden font-sans bg-white">
      {/* HEADER */}
      <Header
        className="bg-white shadow-sm flex items-center justify-between px-6 fixed w-full z-20 h-16 border-b border-gray-200"
        style={{ paddingInline: "24px" }}
      >
        <div className="flex items-center">
          <div
            className="cursor-pointer flex items-center justify-center"
            onClick={() => navigate("/")}
          >
            <img
              src="/gc_logo.svg"
              alt="Logo"
              className="h-15 object-contain"
            />
          </div>
        </div>

        <div className="flex items-center gap-5">
          {/* <Badge count={3} size="small" offset={[-2, 2]} color="#1890ff">
            <Button
              type="text"
              shape="circle"
              icon={<BellOutlined style={{ fontSize: "18px" }} />}
              className="text-gray-500 hover:text-gray-700 flex items-center justify-center"
            />
          </Badge> */}

          <Dropdown
            dropdownRender={() => userProfileCard}
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

      <Layout className="mt-16 h-[calc(100vh-64px)]">
        {/* SIDEBAR */}
        <Sider
          collapsible
          collapsed={collapsed}
          onCollapse={setCollapsed}
          trigger={null}
          width={260}
          style={{
            position: "fixed",
            left: 0,
            height: "calc(100vh - 64px)",
            zIndex: 10,
            background: "#f9fafb",
          }}
          className="border-r border-gray-200 h-full flex flex-col justify-between"
        >
          <div className="flex flex-col h-full bg-[#f9fafb] pb-6">
            {/* Collapse Toggle */}
            <div className="flex items-center justify-end p-4 h-14 mb-2">
              {!collapsed && (
                <span className="text-gray-400 text-xs mr-2 uppercase tracking-wider font-medium">
                  Collapse
                </span>
              )}
              <Button
                type="text"
                size="small"
                className="text-gray-400 hover:text-gray-600 border border-gray-300 bg-white shadow-sm"
                icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                onClick={() => setCollapsed(!collapsed)}
              />
            </div>

            {/* Menu Items */}
            <div className="flex-grow overflow-y-auto custom-scrollbar px-1">
              <Menu
                mode="inline"
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

        {/* MAIN CONTENT */}
        <Layout
          className="bg-white transition-all duration-200 ease-in-out"
          style={{ marginLeft: collapsed ? 80 : 260 }}
        >
          <Content className="h-full overflow-y-auto p-8 bg-white">
            {children}
          </Content>
        </Layout>
      </Layout>
    </Layout>
  );
};

export default MainLayout;
