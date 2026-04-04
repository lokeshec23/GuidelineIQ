// src/pages/Auth/ForgotPasswordPage.jsx

import React, { useState } from "react";
import { Form, Input, Button, Card, Typography, Alert, Steps } from "antd";
import {
    MailOutlined,
    LockOutlined,
    CheckCircleOutlined,
    ArrowLeftOutlined,
    SafetyOutlined,
} from "@ant-design/icons";
import { useNavigate, Link } from "react-router-dom";
import { authAPI } from "../../services/api";

const { Title, Text } = Typography;

// Logo component - same as LoginPage
const Logo = () => (
    <div className="text-center mb-6">
        <img
            src="/gc_logo.svg"
            alt="GuidelineIQ Logo"
            className="h-[36px] mx-auto"
        />
    </div>
);

const ForgotPasswordPage = () => {
    const [currentStep, setCurrentStep] = useState(0); // 0: email, 1: reset password
    const [loading, setLoading] = useState(false);
    const [email, setEmail] = useState("");
    const [emailError, setEmailError] = useState("");
    const [successMessage, setSuccessMessage] = useState("");
    const [emailForm] = Form.useForm();
    const [resetForm] = Form.useForm();
    const navigate = useNavigate();

    // Step 1: Check if email exists
    const handleEmailSubmit = async (values) => {
        setLoading(true);
        setEmailError("");

        try {
            await authAPI.forgotPasswordCheck({ email: values.email });
            setEmail(values.email);
            setCurrentStep(1);
        } catch (error) {
            const status = error.response?.status;
            if (status === 404) {
                setEmailError("This email is not registered. Please check your email or register a new account.");
            } else if (error.message === "Network Error") {
                setEmailError("Network error. Please check your connection.");
            } else {
                setEmailError(
                    error.response?.data?.detail || "Something went wrong. Please try again."
                );
            }
        } finally {
            setLoading(false);
        }
    };

    // Step 2: Reset password
    const handlePasswordReset = async (values) => {
        setLoading(true);
        setEmailError("");

        try {
            await authAPI.resetPassword({
                email: email,
                new_password: values.new_password,
                confirm_password: values.confirm_password,
            });

            setSuccessMessage("Password updated successfully! Redirecting to login...");

            // Navigate to login after 2 seconds
            setTimeout(() => {
                navigate("/login");
            }, 2000);
        } catch (error) {
            const status = error.response?.status;
            if (status === 400) {
                setEmailError(error.response?.data?.detail || "Passwords do not match.");
            } else if (status === 404) {
                setEmailError("Email not registered. Please try again.");
                setCurrentStep(0);
            } else {
                setEmailError(
                    error.response?.data?.detail || "Failed to update password. Please try again."
                );
            }
        } finally {
            setLoading(false);
        }
    };

    // Go back to email step
    const handleBack = () => {
        setCurrentStep(0);
        setEmailError("");
        setSuccessMessage("");
        resetForm.resetFields();
    };

    return (
        <div className="auth-background">
            <div className="circle circle-left"></div>
            <div className="circle circle-right"></div>
            <div className="bottom-curve"></div>
            <Card className="w-full max-w-sm shadow-2xl rounded-xl login-card">
                <Logo />
                <div className="text-center mb-4">
                    <Title level={3} className="!font-poppins text-gray-700">
                        {currentStep === 0 ? "Forgot Password" : "Reset Password"}
                    </Title>
                    <Text type="secondary" className="text-sm">
                        {currentStep === 0
                            ? "Enter your registered email to reset your password"
                            : `Resetting password for ${email}`}
                    </Text>
                </div>

                {/* Progress Steps */}
                <Steps
                    current={currentStep}
                    size="small"
                    className="mb-6"
                    items={[
                        {
                            title: "Verify Email",
                            icon: <MailOutlined />,
                        },
                        {
                            title: "New Password",
                            icon: <SafetyOutlined />,
                        },
                    ]}
                />

                <div style={{ margin: '25px 0px' }}>

                    {/* Error Alert */}
                    {emailError && (
                        <Alert
                            message={emailError}
                            type="error"
                            showIcon
                            closable
                            onClose={() => setEmailError("")}
                            className="mb-4"
                        />
                    )}

                    {/* Success Alert */}
                    {successMessage && (
                        <Alert
                            message={successMessage}
                            type="success"
                            showIcon
                            icon={<CheckCircleOutlined />}
                            className="mb-4"
                        />
                    )}
                </div>
                <div style={{ margin: '25px 0px' }}>
                    {/* Step 1: Email Verification */}
                    {currentStep === 0 && (
                        <Form
                            form={emailForm}
                            name="forgot-password-email"
                            layout="vertical"
                            onFinish={handleEmailSubmit}
                            autoComplete="off"
                        >
                            <Form.Item
                                label="Email Address"
                                name="email"
                                rules={[
                                    { required: true, message: "Please enter your email!" },
                                    { type: "email", message: "Please enter a valid email!" },
                                ]}
                            >
                                <Input
                                    prefix={<MailOutlined className="site-form-item-icon text-gray-400" />}
                                    placeholder="Enter your registered email"
                                    size="large"
                                />
                            </Form.Item>

                            <Form.Item className="mt-6">
                                <Button
                                    type="primary"
                                    htmlType="submit"
                                    loading={loading}
                                    size="large"
                                    block
                                    className="font-semibold"
                                >
                                    Verify Email
                                </Button>
                            </Form.Item>
                        </Form>
                    )}

                    {/* Step 2: Reset Password */}
                    {currentStep === 1 && !successMessage && (
                        <Form
                            form={resetForm}
                            name="reset-password"
                            layout="vertical"
                            onFinish={handlePasswordReset}
                            autoComplete="off"
                        >
                            <Form.Item
                                label="New Password"
                                name="new_password"
                                rules={[
                                    { required: true, message: "Please enter your new password!" },
                                    { min: 6, message: "Password must be at least 6 characters!" },
                                    { max: 16, message: "Password must be at most 16 characters!" },
                                ]}
                            >
                                <Input.Password
                                    prefix={<LockOutlined className="site-form-item-icon text-gray-400" />}
                                    placeholder="Enter new password"
                                    size="large"
                                />
                            </Form.Item>

                            <Form.Item
                                label="Confirm Password"
                                name="confirm_password"
                                dependencies={["new_password"]}
                                rules={[
                                    { required: true, message: "Please confirm your new password!" },
                                    ({ getFieldValue }) => ({
                                        validator(_, value) {
                                            if (!value || getFieldValue("new_password") === value) {
                                                return Promise.resolve();
                                            }
                                            return Promise.reject(
                                                new Error("Passwords do not match!")
                                            );
                                        },
                                    }),
                                ]}
                            >
                                <Input.Password
                                    prefix={<LockOutlined className="site-form-item-icon text-gray-400" />}
                                    placeholder="Confirm new password"
                                    size="large"
                                />
                            </Form.Item>

                            <Form.Item className="mt-6">
                                <div className="flex gap-3">
                                    <Button
                                        size="large"
                                        onClick={handleBack}
                                        icon={<ArrowLeftOutlined />}
                                        className="flex-shrink-0"
                                    >
                                        Back
                                    </Button>
                                    <Button
                                        type="primary"
                                        htmlType="submit"
                                        loading={loading}
                                        size="large"
                                        block
                                        className="font-semibold"
                                        icon={<CheckCircleOutlined />}
                                    >
                                        Update Password
                                    </Button>
                                </div>
                            </Form.Item>
                        </Form>
                    )}
                </div>

                <div className="text-center mt-4">
                    <Text type="secondary">
                        Remember your password?{" "}
                        <Link
                            to="/login"
                            className="font-semibold text-blue-600 hover:underline"
                        >
                            Back to Login
                        </Link>
                    </Text>
                </div>
            </Card>
        </div>
    );
};

export default ForgotPasswordPage;
