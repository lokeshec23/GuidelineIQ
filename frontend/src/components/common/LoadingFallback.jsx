import { Spin, Skeleton } from 'antd';

const LoadingFallback = () => {
    return (
        <div className="min-h-screen p-8 flex flex-col gap-8">
            <div className="flex justify-between items-center">
                <Skeleton.Input active size="large" style={{ width: 200 }} />
                <div className="flex gap-4">
                    <Skeleton.Avatar active size="small" shape="circle" />
                    <Skeleton.Avatar active size="small" shape="circle" />
                </div>
            </div>
            <div className="flex-1 space-y-10">
                <Skeleton active paragraph={{ rows: 10 }} />
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {[...Array(3)].map((_, i) => (
                        <Skeleton key={i} active avatar paragraph={{ rows: 3 }} />
                    ))}
                </div>
            </div>
            <div className="flex justify-center py-4">
                <Spin size="large" tip="Loading application..." />
            </div>
        </div>
    );
};

export default LoadingFallback;
