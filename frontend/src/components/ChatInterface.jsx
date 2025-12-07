import React, { useState, useRef, useEffect } from 'react';
import { Button, Input, Card, List, Avatar, Typography, Space, Spin, Switch, Tooltip, Modal } from 'antd';
import { SendOutlined, CloseOutlined, RobotOutlined, BulbOutlined, FilePdfOutlined, FileExcelOutlined, ArrowsAltOutlined, ShrinkOutlined, FormOutlined, EyeOutlined } from '@ant-design/icons';
import { chatAPI } from '../services/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const { Text, TextArea } = Typography;

const ChatInterface = ({ sessionId, data, visible, onClose, selectedRecordIds = [], isComparisonMode = false, onOpenPdf }) => {
    const [mode, setMode] = useState("excel"); // "excel" or "pdf"
    const [isExpanded, setIsExpanded] = useState(false);
    const [size, setSize] = useState({ width: 450, height: 600 });
    const [messages, setMessages] = useState([
        {
            id: 'welcome',
            role: 'assistant',
            content: isComparisonMode
                ? 'Hello 👋\nHow can I help you analyze this comparison data today?'
                : 'Hello 👋\nHow can I help you analyze this data today?'
        }
    ]);
    const [inputValue, setInputValue] = useState('');
    const [loading, setLoading] = useState(false);
    const [instructions, setInstructions] = useState('');
    const [isInstructionModalOpen, setIsInstructionModalOpen] = useState(false);
    const [tempInstructions, setTempInstructions] = useState('');

    const messagesEndRef = useRef(null);
    const isResizingRef = useRef(false);
    const startPosRef = useRef({ x: 0, y: 0 });
    const startSizeRef = useRef({ width: 0, height: 0 });

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        if (visible) {
            scrollToBottom();
        }
    }, [messages, visible]);

    // Handle Expand Toggle
    useEffect(() => {
        if (isExpanded) {
            setSize({ width: 800, height: 700 });
        } else {
            setSize({ width: 450, height: 600 });
        }
    }, [isExpanded]);

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
            // Call API with session-based endpoint
            const response = await chatAPI.sendMessage({
                session_id: sessionId,
                message: messageText,
                mode: mode, // "pdf" or "excel"
                instructions: instructions || null
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
                content: `Sorry, I encountered an error: ${error.response?.data?.detail || error.message}`
            };
            setMessages(prev => [...prev, errorMsg]);
        } finally {
            setLoading(false);
        }
    };

    // Resize Handlers
    const handleMouseDown = (e) => {
        isResizingRef.current = true;
        startPosRef.current = { x: e.clientX, y: e.clientY };
        startSizeRef.current = { width: size.width, height: size.height };
        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
        e.preventDefault(); // Prevent text selection
    };

    const handleMouseMove = (e) => {
        if (!isResizingRef.current) return;

        const deltaX = startPosRef.current.x - e.clientX; // Dragging left increases width
        const deltaY = startPosRef.current.y - e.clientY; // Dragging up increases height

        setSize({
            width: Math.max(300, Math.min(1000, startSizeRef.current.width + deltaX)),
            height: Math.max(400, Math.min(window.innerHeight - 100, startSizeRef.current.height + deltaY))
        });
    };

    const handleMouseUp = () => {
        isResizingRef.current = false;
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
    };

    const openInstructionModal = () => {
        setTempInstructions(instructions);
        setIsInstructionModalOpen(true);
    };

    const saveInstructions = () => {
        setInstructions(tempInstructions);
        setIsInstructionModalOpen(false);
    };

    if (!visible) return null;

    return (
        <div className="fixed bottom-6 right-6 z-[1050] flex flex-col items-end">
            {/* Chat Window */}
            <Card
                className="mb-4 shadow-xl border-0 rounded-2xl overflow-hidden flex flex-col relative"
                bodyStyle={{ padding: 0, display: 'flex', flexDirection: 'column', height: '100%' }}
                style={{
                    width: `${size.width}px`,
                    height: `${size.height}px`,
                    maxHeight: 'calc(100vh - 100px)', // Prevent going off-screen
                    animation: 'fadeInUp 0.3s ease-out',
                    transition: isResizingRef.current ? 'none' : 'width 0.3s, height 0.3s'
                }}
            >
                {/* Resize Handle (Top-Left Corner) */}
                <div
                    className="absolute top-0 left-0 w-4 h-4 cursor-nw-resize z-50 hover:bg-gray-200 rounded-br"
                    onMouseDown={handleMouseDown}
                    style={{
                        background: 'linear-gradient(135deg, #ccc 50%, transparent 50%)',
                        opacity: 0.5
                    }}
                    title="Resize"
                />

                {/* Header */}
                <div className="p-4 border-b flex justify-between items-center bg-white sticky top-0 z-10 select-none">
                    <div className="flex items-center gap-2 pl-4"> {/* Added padding-left to avoid overlap with resize handle */}
                        <Avatar
                            size="small"
                            icon={<RobotOutlined />}
                            style={{ backgroundColor: '#0EA5E9' }}
                        />
                        {/* <Text strong className="text-gray-700">Kodee</Text> */}
                    </div>
                    <Space>
                        {!isComparisonMode && (
                            <>
                                <Tooltip title={mode === "pdf" ? "Chatting with PDF" : "Chatting with Excel Data"}>
                                    <Switch
                                        checkedChildren={<FilePdfOutlined />}
                                        unCheckedChildren={<FileExcelOutlined />}
                                        checked={mode === "pdf"}
                                        onChange={(checked) => setMode(checked ? "pdf" : "excel")}
                                    />
                                </Tooltip>
                                {mode === "pdf" && sessionId && (
                                    <Tooltip title="View PDF">
                                        <Button
                                            type="primary"
                                            size="small"
                                            icon={<EyeOutlined />}
                                            onClick={() => onOpenPdf && onOpenPdf()}
                                        >
                                            Open PDF
                                        </Button>
                                    </Tooltip>
                                )}
                            </>
                        )}
                        <Tooltip title="Set Instructions">
                            <Button
                                type={instructions ? "primary" : "text"}
                                size="small"
                                icon={<FormOutlined />}
                                onClick={openInstructionModal}
                            >
                                Instruction
                            </Button>
                        </Tooltip>
                        <Tooltip title={isExpanded ? "Collapse" : "Expand"}>
                            <Button
                                type="text"
                                size="small"
                                icon={isExpanded ? <ShrinkOutlined /> : <ArrowsAltOutlined />}
                                onClick={() => setIsExpanded(!isExpanded)}
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
                                        <div className={`markdown-content ${item.role === 'user' ? 'text-white' : 'text-gray-800'}`}>
                                            <ReactMarkdown
                                                remarkPlugins={[remarkGfm]}
                                                components={{
                                                    p: ({ node, ...props }) => <p className="mb-2 last:mb-0" {...props} />,
                                                    ul: ({ node, ...props }) => <ul className="list-disc pl-4 mb-2" {...props} />,
                                                    ol: ({ node, ...props }) => <ol className="list-decimal pl-4 mb-2" {...props} />,
                                                    li: ({ node, ...props }) => <li className="mb-1" {...props} />,
                                                    a: ({ node, ...props }) => <a className="text-blue-500 hover:underline" target="_blank" rel="noopener noreferrer" {...props} />,
                                                    code: ({ node, inline, className, children, ...props }) => {
                                                        const match = /language-(\w+)/.exec(className || '')
                                                        return !inline && match ? (
                                                            <div className="bg-gray-800 rounded p-2 my-2 overflow-x-auto">
                                                                <code className={className} {...props}>
                                                                    {children}
                                                                </code>
                                                            </div>
                                                        ) : (
                                                            <code className="bg-gray-100 px-1 rounded text-sm font-mono text-red-500" {...props}>
                                                                {children}
                                                            </code>
                                                        )
                                                    }
                                                }}
                                            >
                                                {item.content}
                                            </ReactMarkdown>
                                        </div>
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
                        placeholder="Ask  anything..."
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
                            AI chat can make mistakes. Double-check replies.
                        </Text>
                    </div>
                </div>
            </Card>



            {/* Instruction Modal */}
            <Modal
                title="Set Chat Instructions"
                open={isInstructionModalOpen}
                onOk={saveInstructions}
                onCancel={() => setIsInstructionModalOpen(false)}
                okText="Save"
                cancelText="Close"
                zIndex={2000}
            >
                <p className="mb-2 text-gray-600">
                    Provide specific instructions for the AI (e.g., "Reply in 2 lines", "Format as a list").
                    These instructions will be applied to every message until you clear them.
                </p>
                <Input.TextArea
                    rows={4}
                    value={tempInstructions}
                    onChange={(e) => setTempInstructions(e.target.value)}
                    placeholder="Enter instructions here..."
                />
            </Modal>

            <style jsx>{`
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
        </div >
    );
};

export default ChatInterface;
