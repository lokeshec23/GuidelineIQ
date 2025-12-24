import React from 'react';
import { Spin } from 'antd';

const LoadingFallback = () => {
    return (
        <div className="min-h-screen flex items-center justify-center">
            <Spin size="large" tip="Loading..." />
        </div>
    );
};

export default LoadingFallback;
