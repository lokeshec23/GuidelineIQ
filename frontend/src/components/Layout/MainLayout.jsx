import React, { useState } from "react";
import { Layout, Menu, Avatar, Dropdown, Badge, Button } from "antd";
import {
  FileTextOutlined,
  SwapOutlined,
  SettingOutlined,
  UserOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  BellOutlined,
} from "@ant-design/icons";
import { useAuth } from "../../context/AuthContext";
import { useNavigate, useLocation } from "react-router-dom";

const { Header, Sider, Content } = Layout;

// Base menu items
const menuItems = [
  {
    key: "/ingest",
    icon: <FileTextOutlined />,
    label: "Ingest Guideline",
  },
  {
    key: "/compare",
    icon: <SwapOutlined />,
    label: "Compare Guidelines",
  },
  {
    key: "/settings",
    icon: <SettingOutlined />,
    label: "Settings",
  },
];

const MainLayout = ({ children }) => {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  // User dropdown menu
  const userMenuItems = [
    {
      key: "profile",
      icon: <UserOutlined />,
      label: (
        <div>
          <div className="font-semibold">{user?.username}</div>
          <div className="text-xs text-gray-500">{user?.email}</div>
        </div>
      ),
      disabled: true,
    },
    { type: "divider" },
    {
      key: "logout",
      icon: <LogoutOutlined />,
      label: "Logout",
      danger: true,
      onClick: () => {
        logout();
        navigate("/login");
      },
    },
  ];

  // Show settings menu ONLY if user is admin
  const filteredMenuItems = menuItems.filter(
    (item) => item.key !== "/settings" || isAdmin
  );

  const handleMenuClick = ({ key }) => {
    navigate(key);
  };

  return (
    <Layout className="h-screen overflow-hidden font-sans">
      {/* HEADER */}
      <Header className="bg-white shadow-sm flex items-center justify-between px-6 fixed w-full z-10 h-16">
        {/* Left Side: Logo */}
        <div className="flex items-center gap-6">
          <img
            src="/gc_logo.svg"
            alt="Logo"
            className="h-10 cursor-pointer"
            onClick={() => navigate("/")}
          />
        </div>

        {/* Right Side: Actions & User Menu */}
        <div className="flex items-center gap-4">
          {/* Notification Icon */}
          <Badge count={3} size="small">
            <Avatar
              shape="circle"
              icon={<BellOutlined />}
              className="cursor-pointer bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors"
            />
          </Badge>

          {/* User Avatar & Dropdown */}
          <Dropdown
            menu={{ items: userMenuItems }}
            placement="bottomRight"
            trigger={["click"]}
          >
            <div className="cursor-pointer">
              <Avatar
                icon={<UserOutlined />}
                src={user?.avatarUrl}
                className="bg-blue-500 text-white hover:bg-blue-600 transition-colors"
              >
                {user?.username?.[0]?.toUpperCase()}
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
          className="bg-white border-r border-gray-200"
          width={240}
          theme="light"
        >
          <div className="flex justify-end p-4 border-b border-gray-200">
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed(!collapsed)}
              className="flex items-center justify-center hover:bg-gray-100 transition-colors"
            />
          </div>
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
            items={filteredMenuItems}
            onClick={handleMenuClick}
            className="h-full border-r-0"
          />
        </Sider>

        {/* MAIN CONTENT */}
        <Layout className="bg-gray-50">
          <Content className="overflow-y-auto h-full">
            <div className="p-6">{children}</div>
          </Content>
        </Layout>
      </Layout>
    </Layout>
  );
};

export default MainLayout;
