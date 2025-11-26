import React, { useState, useRef, useEffect } from 'react';
import { Button, Input, Card, List, Avatar, Typography, Space, Spin, Switch, Tooltip } from 'antd';
import { SendOutlined, CloseOutlined, RobotOutlined, BulbOutlined, FilePdfOutlined, FileExcelOutlined } from '@ant-design/icons';
import { chatAPI } from '../services/api';

const { Text } = Typography;

const ChatInterface = ({ sessionId, data, visible, onClose, selectedRecordIds = [] }) => {
    const [mode, setMode] = useState("excel"); // "excel" or "pdf"
    const [messages, setMessages] = useState([
        {
            id: 'welcome',
            role: 'assistant',
            content: 'Hello 👋\nHow can I help you analyze this data today?',
            suggestions: [
                'Summarize this data',
                'Find key insights',
                'Identify any anomalies'
            ]
        }
    ]);
    const [inputValue, setInputValue] = useState('');
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        if (visible) {
            scrollToBottom();
        }
    }, [messages, visible]);

    const handleSendMessage = async (text) => {
        const messageText = text || inputValue.trim();
        if (!messageText) return;

        // Add user message
        const userMsg = {
            id: Date.now(),
            role: 'user',
            content: messageText
        };
        setMessages(prev => [...prev, userMsg]);
        setInputValue('');
        setLoading(true);

        try {
            // Call API
            const response = await chatAPI.sendMessage({
                session_id: sessionId,
                message: messageText,
                history: messages.map(m => ({ role: m.role, content: m.content })), // Send history
                mode: mode, // "pdf" or "excel"
                context_ids: selectedRecordIds // Send selected IDs
            });

            // Add AI response
            const aiMsg = {
                id: Date.now() + 1,
                role: 'assistant',
                content: response.data.reply
            };
            setMessages(prev => [...prev, aiMsg]);
        } catch (error) {
            console.error('Chat error:', error);
            const errorMsg = {
                id: Date.now() + 1,
                role: 'assistant',
                content: 'Sorry, I encountered an error processing your request. Please try again.'
            };
            setMessages(prev => [...prev, errorMsg]);
        } finally {
            setLoading(false);
        }
    };

    if (!visible) return null;

    return (
        <div className="fixed bottom-6 right-6 z-[1050] flex flex-col items-end">
            {/* Chat Window */}
            <Card
                className="mb-4 w-[380px] shadow-xl border-0 rounded-2xl overflow-hidden flex flex-col"
                bodyStyle={{ padding: 0, display: 'flex', flexDirection: 'column', height: '500px' }}
                style={{ animation: 'fadeInUp 0.3s ease-out' }}
            >
                {/* Header */}
                <div className="p-4 border-b flex justify-between items-center bg-white sticky top-0 z-10">
                    <div className="flex items-center gap-2">
                        <Avatar
                            size="small"
                            icon={<RobotOutlined />}
                            style={{ backgroundColor: '#0EA5E9' }}
                        />
                        {/* <Text strong>Kodee</Text> */}
                    </div>
                    <Space>
                        <Tooltip title={mode === "pdf" ? "Chatting with PDF" : "Chatting with Excel Data"}>
                            <Switch
                                checkedChildren={<FilePdfOutlined />}
                                unCheckedChildren={<FileExcelOutlined />}
                                checked={mode === "pdf"}
                                onChange={(checked) => setMode(checked ? "pdf" : "excel")}
                            />
                        </Tooltip>
                        <Button
                            type="text"
                            size="small"
                            icon={<CloseOutlined />}
                            onClick={onClose}
                        />
                    </Space>
                </div>

                {/* Messages Area */}
                <div className="flex-1 overflow-y-auto p-4 bg-gray-50">
                    <List
                        itemLayout="horizontal"
                        dataSource={messages}
                        split={false}
                        renderItem={(item) => (
                            <div className={`mb-4 flex ${item.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                <div className={`max-w-[85%] ${item.role === 'user' ? 'order-1' : 'order-2'}`}>
                                    <div
                                        className={`p-3 rounded-2xl ${item.role === 'user'
                                            ? 'bg-[#0EA5E9] text-white rounded-tr-none'
                                            : 'bg-white border border-gray-100 shadow-sm rounded-tl-none'
                                            }`}
                                    >
                                        <Text className={item.role === 'user' ? 'text-white' : 'text-gray-800'}>
                                            {item.content}
                                        </Text>
                                    </div>

                                    {/* Suggestions Chips */}
                                    {item.suggestions && (
                                        <div className="mt-3 flex flex-col gap-2">
                                            {item.suggestions.map((suggestion, idx) => (
                                                <div
                                                    key={idx}
                                                    className="flex items-center gap-2 p-2 bg-white border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors text-sm text-gray-600"
                                                    onClick={() => handleSendMessage(suggestion)}
                                                >
                                                    <BulbOutlined className="text-[#0EA5E9]" />
                                                    {suggestion}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}
                    />
                    {loading && (
                        <div className="flex justify-start mb-4">
                            <div className="bg-white p-3 rounded-2xl rounded-tl-none border border-gray-100 shadow-sm">
                                <Spin size="small" />
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* Input Area */}
                <div className="p-4 bg-white border-t">
                    <Input
                        placeholder="Ask Kodee anything..."
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onPressEnter={() => handleSendMessage()}
                        suffix={
                            <Button
                                type="text"
                                icon={<SendOutlined />}
                                onClick={() => handleSendMessage()}
                                disabled={!inputValue.trim() || loading}
                                className={inputValue.trim() ? "text-[#0EA5E9]" : "text-gray-300"}
                            />
                        }
                        className="rounded-full py-2 px-4 bg-gray-50 border-gray-200 hover:bg-white focus:bg-white"
                    />
                    <div className="text-center mt-2">
                        <Text type="secondary" style={{ fontSize: '10px' }}>
                            Kodee can make mistakes. Double-check replies.
                        </Text>
                    </div>
                </div>
            </Card>

            <style jsx>{`
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
        </div>
    );
};

export default ChatInterface;
