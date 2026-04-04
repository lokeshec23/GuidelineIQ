// src/pages/Auth/LoginPage.jsx

import React, { useState } from "react";
import { Form, Input, Button, Card, Typography, Checkbox } from "antd";
import { UserOutlined, LockOutlined, LoginOutlined } from "@ant-design/icons";
import { useAuth } from "../../context/AuthContext";
import { useNavigate, Link } from "react-router-dom";
import { API_BASE_URL } from "../../services/api";

const { Title, Text } = Typography;

// Logo component now uses the image from the public folder
const Logo = () => (
  <div className="text-center mb-6">
    {/* Assumes your logo is named 'loandna-logo.png' in the public folder */}
    <img
      src="/loandna_logo.png"
      alt="LoanDNA Logo"
      className="h-10 mx-auto" // Adjust height (h-10) as needed
    />
  </div>
);

const LoginPage = () => {
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (values) => {
    setLoading(true);
    const success = await login(values.username, values.password, values.remember); // Pass remember value
    setLoading(false);

    if (success) {
      navigate("/ingest");
    }
  };

  const handleMicrosoftLogin = () => {
    // Redirect to backend endpoint that initiates SAML flow
    window.location.href = `${API_BASE_URL}/auth/ValidateAzureAD`;
  };

  const handleFormError = (errorInfo) => {
    // Show toast for first validation error
    if (errorInfo.errorFields && errorInfo.errorFields.length > 0) {
      const firstError = errorInfo.errorFields[0];
      if (firstError.errors && firstError.errors.length > 0) {
        // Don't show toast for validation errors - Ant Design shows them inline
        // This is just for tracking if needed
      }
    }
  };

  return (
    <div className="auth-background">
      <Card className="w-full max-w-sm shadow-2xl rounded-xl p-4">
        <Logo />
        <div className="text-center mb-6">
          <Title level={3} className="!font-poppins text-gray-700">
            Log In
          </Title>
        </div>

        <Form
          form={form}
          name="login"
          layout="vertical"
          onFinish={handleSubmit}
          onFinishFailed={handleFormError}
          autoComplete="off"
        >
          <Form.Item
            label="Email"
            name="username"
            rules={[{ required: true, message: "Please enter your email!" }]}
          >
            <Input
              prefix={
                <UserOutlined className="site-form-item-icon text-gray-400" />
              }
              placeholder="Enter your email"
              size="large"
            />
          </Form.Item>

          <Form.Item
            label="Password"
            name="password"
            rules={[{ required: true, message: "Please enter your password!" }]}
          >
            <Input.Password
              prefix={
                <LockOutlined className="site-form-item-icon text-gray-400" />
              }
              placeholder="Enter your password"
              size="large"
            />
          </Form.Item>

          <Form.Item>
            <div className="flex justify-between items-center">
              <Form.Item name="remember" valuePropName="checked" noStyle>
                <Checkbox>Remember me</Checkbox>
              </Form.Item>
              <Link to="/forgot-password" className="text-blue-600 hover:text-blue-700 text-sm">
                Forgot password?
              </Link>
            </div>
          </Form.Item>

          {/* CAPTCHA section is now removed */}

          <Form.Item className="mt-6">
            <Button
              type="primary"
              htmlType="submit"
              icon={<LoginOutlined />}
              loading={loading}
              size="large"
              block
              className="font-semibold"
            >
              Login
            </Button>
          </Form.Item>

          <div className="relative my-8">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-200"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white text-gray-500 uppercase tracking-widest text-[10px] font-bold">
                OR LOG IN WITH
              </span>
            </div>
          </div>

          <Button
            block
            size="large"
            icon={<img src="/Microsoft_logo.png" alt="Microsoft" style={{ width: 18, marginRight: 8 }} />}
            onClick={handleMicrosoftLogin}
            className="flex items-center justify-center border-gray-300 hover:border-blue-500 hover:text-blue-600 transition-all font-medium rounded-lg h-[45px]"
          >
            Microsoft
          </Button>

          <div className="text-center mt-4">
            <Text type="secondary">
              Don't have an account?{" "}
              <Link
                to="/register"
                className="font-semibold text-blue-600 hover:underline"
              >
                Register now
              </Link>
            </Text>
          </div>
        </Form>
      </Card>
    </div>
  );
};

export default LoginPage;
