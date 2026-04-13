import React from 'react';
import { Skeleton, Space, Card } from 'antd';

export const TableSkeleton = ({ rows = 5, columns = 5, showHeader = true }) => {
    return (
        <div className="w-full space-y-4">
            {showHeader && (
                <div className="flex justify-between items-center mb-4">
                    <Skeleton.Input active size="large" style={{ width: 200 }} />
                    <Skeleton.Button active size="large" />
                </div>
            )}
            <div className="border border-gray-100 rounded-xl overflow-hidden bg-white shadow-sm">
                <table className="w-full border-collapse">
                    <thead>
                        <tr className="bg-gray-50/50">
                            {[...Array(columns)].map((_, i) => (
                                <th key={i} className="p-4 border-b border-gray-100 text-left">
                                    <Skeleton.Input active size="small" style={{ width: '80%' }} />
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {[...Array(rows)].map((_, i) => (
                            <tr key={i} className="border-b border-gray-50 last:border-0">
                                {[...Array(columns)].map((_, j) => (
                                    <td key={j} className="p-4">
                                        <Skeleton.Input active size="small" block />
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export const FormSkeleton = ({ items = 4 }) => {
    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {[...Array(items)].map((_, i) => (
                    <div key={i} className="space-y-2">
                        <Skeleton.Input active size="small" style={{ width: 100 }} />
                        <Skeleton.Input active size="large" block />
                    </div>
                ))}
            </div>
            <div className="flex justify-end gap-4 mt-8">
                <Skeleton.Button active size="large" style={{ width: 120 }} />
                <Skeleton.Button active size="large" style={{ width: 150 }} />
            </div>
        </div>
    );
};

export const CardSkeleton = ({ count = 3 }) => {
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(count)].map((_, i) => (
                <Card key={i} className="shadow-sm border-gray-100">
                    <Skeleton active avatar paragraph={{ rows: 3 }} />
                </Card>
            ))}
        </div>
    );
};

export const DashboardSkeleton = () => {
    return (
        <div className="p-6 space-y-8 h-full overflow-hidden">
            <div className="flex justify-between items-center">
                <Skeleton.Input active size="large" style={{ width: 250 }} />
                <Skeleton.Button active size="large" style={{ width: 120 }} />
            </div>
            <div className="space-y-4">
                <div className="flex gap-4 border-b border-gray-100 pb-2">
                    <Skeleton.Button active size="small" style={{ width: 100 }} />
                    <Skeleton.Button active size="small" style={{ width: 100 }} />
                </div>
                <TableSkeleton rows={8} columns={6} />
            </div>
        </div>
    );
};

export const IngestSkeleton = () => {
    return (
        <div className="p-8 max-w-[1200px] mx-auto space-y-10">
            <Skeleton.Input active size="large" style={{ width: 300, marginBottom: 20 }} />
            <div className="space-y-8">
                <FormSkeleton items={6} />
                <div className="border-2 border-dashed border-gray-100 rounded-lg p-12 flex flex-col items-center gap-4">
                    <Skeleton.Avatar active size={64} shape="square" />
                    <Skeleton.Input active size="large" style={{ width: 200 }} />
                    <Skeleton.Input active size="small" style={{ width: 150 }} />
                </div>
            </div>
        </div>
    );
};

export const CompareSkeleton = () => {
    return (
        <div className="p-8 max-w-[1400px] mx-auto space-y-10">
            <Skeleton.Input active size="large" style={{ width: 250, marginBottom: 20 }} />
            <div className="space-y-8">
                <FormSkeleton items={2} />
                <div className="space-y-4">
                    <div className="flex justify-between">
                        <Skeleton.Input active size="small" style={{ width: 200 }} />
                        <Skeleton.Input active size="large" style={{ width: 300 }} />
                    </div>
                    <TableSkeleton rows={3} columns={5} />
                </div>
                <div className="relative py-8">
                    <div className="absolute inset-0 flex items-center">
                        <div className="w-full border-t border-gray-100"></div>
                    </div>
                    <div className="relative flex justify-center">
                        <Skeleton.Button active size="small" style={{ width: 60 }} />
                    </div>
                </div>
                <div className="border-2 border-dashed border-gray-100 rounded-lg p-12 flex flex-col items-center gap-4">
                    <Skeleton.Avatar active size={64} shape="square" />
                    <Skeleton.Input active size="large" style={{ width: 200 }} />
                </div>
            </div>
        </div>
    );
};

export const PromptsSkeleton = () => {
    return (
        <div className="px-8 py-6 space-y-6">
            <div className="space-y-2">
                <Skeleton.Input active size="large" style={{ width: 250 }} />
                <Skeleton.Input active size="small" style={{ width: 400 }} />
            </div>

            <Card className="shadow-sm border-gray-200 p-6">
                <div className="space-y-8">
                    <div className="flex gap-4 border-b border-gray-100 pb-2">
                        <Skeleton.Button active size="small" style={{ width: 120 }} />
                        <Skeleton.Button active size="small" style={{ width: 120 }} />
                    </div>

                    <div className="space-y-6">
                        <div className="space-y-2">
                            <Skeleton.Input active size="small" style={{ width: 120 }} />
                            <Skeleton.Input active block style={{ height: 150 }} />
                        </div>
                        <div className="space-y-2">
                            <Skeleton.Input active size="small" style={{ width: 120 }} />
                            <Skeleton.Input active block style={{ height: 250 }} />
                        </div>
                    </div>

                    <div className="flex justify-end gap-3 mt-6">
                        <Skeleton.Button active size="large" style={{ width: 150 }} />
                        <Skeleton.Button active size="large" style={{ width: 130 }} />
                    </div>
                </div>
            </Card>
        </div>
    );
};

export const SettingsSkeleton = () => {
    return (
        <div className="max-w-screen-2xl mx-auto px-4 md:px-8 space-y-10">
            <div className="space-y-6">
                {[...Array(3)].map((_, i) => (
                    <Card key={i} className="shadow-sm">
                        <div className="flex flex-col gap-6">
                            <Skeleton.Input active size="large" style={{ width: 300, marginBottom: 20 }} />
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <FormSkeleton items={2} />
                            </div>
                        </div>
                    </Card>
                ))}
            </div>
            <div className="flex justify-end gap-3">
                <Skeleton.Button active size="large" style={{ width: 100 }} />
                <Skeleton.Button active size="large" style={{ width: 150 }} />
            </div>
        </div>
    );
};
