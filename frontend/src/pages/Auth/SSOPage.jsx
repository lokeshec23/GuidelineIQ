import React, { useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { authAPI } from '../../services/api';
import { Spin, Typography } from 'antd';
import { showToast } from '../../utils/toast';

const { Title, Text } = Typography;

const SSOPage = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const { ssoLogin } = useAuth();

    useEffect(() => {
        const token = searchParams.get('token');

        if (!token) {
            showToast.error("Missing SSO token. Please try logging in again.");
            navigate('/login');
            return;
        }

        const performExchange = async () => {
            try {
                const response = await authAPI.ssoExchange(token);
                if (response.data) {
                    const success = await ssoLogin(response.data);
                    if (success) {
                        navigate('/dashboard');
                    } else {
                        navigate('/login');
                    }
                }
            } catch (error) {
                console.error("SSO Exchange Error:", error);
                const errorDetail = error.response?.data?.detail || "Authentication failed. Your account might not be registered in the system.";
                showToast.error(errorDetail);
                navigate('/login');
            }
        };

        performExchange();
    }, [searchParams, navigate, ssoLogin]);

    return (
        <div style={{ 
            height: '100vh', 
            display: 'flex', 
            flexDirection: 'column', 
            justifyContent: 'center', 
            alignItems: 'center',
            background: '#f0f2f5' 
        }}>
            <Spin size="large" />
            <div style={{ marginTop: 24, textAlign: 'center' }}>
                <Title level={4}>Authenticating with Microsoft...</Title>
                <Text type="secondary">Please wait while we set up your session.</Text>
            </div>
        </div>
    );
};

export default SSOPage;
