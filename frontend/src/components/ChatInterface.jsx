import React, { useState, useRef, useEffect } from 'react';
import { Button, Input, Card, List, Avatar, Typography, Space, Spin, Segmented, Tooltip, Modal, Popconfirm, Empty } from 'antd';
import { SendOutlined, CloseOutlined, RobotOutlined, BulbOutlined, FilePdfOutlined, FileExcelOutlined, ArrowsAltOutlined, ShrinkOutlined, FormOutlined, EyeOutlined, HistoryOutlined, PlusOutlined, DeleteOutlined, MessageOutlined } from '@ant-design/icons';
import { chatAPI } from '../services/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './ChatInterface.css';

const { Text, TextArea } = Typography;

const ChatInterface = ({ sessionId, data, visible, onClose, selectedRecordIds = [], isComparisonMode = false, onOpenPdf }) => {
    const [mode, setMode] = useState("excel"); // "excel" or "pdf"
    const [isExpanded, setIsExpanded] = useState(true);
    const [size, setSize] = useState({ width: 1000, height: 700 });
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

    // Conversation history state
    const [conversations, setConversations] = useState([]);
    const [currentConversationId, setCurrentConversationId] = useState(null);
    const [showHistory, setShowHistory] = useState(true);
    const [loadingConversations, setLoadingConversations] = useState(false);

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

    // Load conversations when component mounts or sessionId changes
    useEffect(() => {
        if (visible && sessionId) {
            loadConversations();
        }
    }, [visible, sessionId]);

    // Handle Expand Toggle
    useEffect(() => {
        if (isExpanded) {
            setSize({ width: 1000, height: 700 });
        } else {
            setSize({ width: 700, height: 600 });
        }
    }, [isExpanded]);

    // Load all conversations for this session
    const loadConversations = async () => {
        setLoadingConversations(true);
        try {
            const response = await chatAPI.getConversations(sessionId);
            setConversations(response.data.conversations || []);
        } catch (error) {
            console.error('Error loading conversations:', error);
        } finally {
            setLoadingConversations(false);
        }
    };

    // Start a new chat (clear current without creating conversation yet)
    const handleNewChat = () => {
        // Just clear the current conversation and reset to welcome state
        // Conversation will be created when user sends first message
        setCurrentConversationId(null);
        setMessages([{
            id: 'welcome',
            role: 'assistant',
            content: isComparisonMode
                ? 'Hello 👋\nHow can I help you analyze this comparison data today?'
                : 'Hello 👋\nHow can I help you analyze this data today?'
        }]);
    };

    // Switch to a different conversation
    const handleSwitchConversation = async (conversationId) => {
        setCurrentConversationId(conversationId);
        setLoading(true);
        try {
            const response = await chatAPI.getConversationMessages(conversationId);
            const msgs = response.data.messages || [];

            // Convert to UI format
            const formattedMsgs = msgs.map((msg, idx) => ({
                id: `msg-${idx}`,
                role: msg.role,
                content: msg.content
            }));

            setMessages(formattedMsgs.length > 0 ? formattedMsgs : [{
                id: 'welcome',
                role: 'assistant',
                content: isComparisonMode
                    ? 'Hello 👋\nHow can I help you analyze this comparison data today?'
                    : 'Hello 👋\nHow can I help you analyze this data today?'
            }]);
        } catch (error) {
            console.error('Error loading conversation:', error);
        } finally {
            setLoading(false);
        }
    };

    // Delete a conversation
    const handleDeleteConversation = async (conversationId) => {
        try {
            await chatAPI.deleteConversation(conversationId);

            // If deleting current conversation, reset
            if (conversationId === currentConversationId) {
                setCurrentConversationId(null);
                setMessages([{
                    id: 'welcome',
                    role: 'assistant',
                    content: isComparisonMode
                        ? 'Hello 👋\nHow can I help you analyze this comparison data today?'
                        : 'Hello 👋\nHow can I help you analyze this data today?'
                }]);
            }

            await loadConversations();
        } catch (error) {
            console.error('Error deleting conversation:', error);
        }
    };

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
            // Call API with conversation support
            const response = await chatAPI.sendMessage({
                session_id: sessionId,
                conversation_id: currentConversationId,
                message: messageText,
                mode: mode,
                instructions: instructions || null
            });

            // Update conversationId if it was auto-created
            if (response.data.conversation_id && !currentConversationId) {
                setCurrentConversationId(response.data.conversation_id);
            }

            // Add AI response
            const aiMsg = {
                id: Date.now() + 1,
                role: 'assistant',
                content: response.data.reply
            };
            setMessages(prev => [...prev, aiMsg]);

            // Reload conversations to update list
            await loadConversations();
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
                className="chat-card mb-4 rounded-2xl overflow-hidden flex flex-col relative"
                bodyStyle={{ padding: 0, display: 'flex', flexDirection: 'row', height: '100%' }}
                style={{
                    width: `${size.width}px`,
                    height: `${size.height}px`,
                    maxHeight: 'calc(100vh - 100px)',
                    animation: 'fadeIn 0.3s ease-out',
                    transition: isResizingRef.current ? 'none' : 'width 0.3s, height 0.3s'
                }}
            >
                {/* Resize Handle (Top-Left Corner) */}
                <div
                    className="chat-resize-handle absolute top-0 left-0 w-4 h-4 z-50 rounded-br"
                    onMouseDown={handleMouseDown}
                    style={{
                        background: 'linear-gradient(135deg, #93c5fd 50%, transparent 50%)'
                    }}
                    title="Resize"
                />

                {/* History Sidebar */}
                {showHistory && (
                    <div className="chat-sidebar w-64 flex flex-col" style={{ height: '100%' }}>
                        {/* Sidebar Header */}
                        <div className="chat-sidebar-header p-3">
                            <Button
                                type="primary"
                                icon={<PlusOutlined />}
                                onClick={handleNewChat}
                                block
                                className="chat-new-button mb-2"
                            >
                                New Chat
                            </Button>
                        </div>

                        {/* Conversations List */}
                        <div className="flex-1 overflow-y-auto">
                            {loadingConversations ? (
                                <div className="flex justify-center items-center h-32">
                                    <Spin size="small" />
                                </div>
                            ) : conversations.length === 0 ? (
                                <Empty
                                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                                    description="No conversations"
                                    className="mt-8"
                                />
                            ) : (
                                <List
                                    dataSource={conversations}
                                    renderItem={(conv) => (
                                        <div
                                            key={conv.id}
                                            className={`chat-conversation-item p-3 ${currentConversationId === conv.id ? 'chat-conversation-item-active' : ''
                                                }`}
                                            onClick={() => handleSwitchConversation(conv.id)}
                                        >
                                            <div className="flex justify-between items-start">
                                                <div className="flex-1 mr-2">
                                                    <div className="font-medium text-sm text-gray-800 truncate">
                                                        {conv.title || 'New Conversation'}
                                                    </div>
                                                    {conv.last_message && (
                                                        <div className="text-xs text-gray-500 truncate mt-1">
                                                            {conv.last_message}
                                                        </div>
                                                    )}
                                                    <div className="text-xs text-gray-400 mt-1">
                                                        {new Date(conv.updated_at).toLocaleDateString()}
                                                    </div>
                                                </div>
                                                <Popconfirm
                                                    title="Delete conversation?"
                                                    description="This will permanently delete all messages."
                                                    onConfirm={(e) => {
                                                        e.stopPropagation();
                                                        handleDeleteConversation(conv.id);
                                                    }}
                                                    onCancel={(e) => e.stopPropagation()}
                                                    okText="Delete"
                                                    cancelText="Cancel"
                                                >
                                                    <Button
                                                        type="text"
                                                        size="small"
                                                        icon={<DeleteOutlined />}
                                                        danger
                                                        onClick={(e) => e.stopPropagation()}
                                                        className="chat-delete-button"
                                                    />
                                                </Popconfirm>
                                            </div>
                                        </div>
                                    )}
                                />
                            )}
                        </div>
                    </div>
                )}

                {/* Main Chat Area */}
                <div className="chat-main-area flex-1 flex flex-col" style={{ height: '100%' }}>
                    {/* Header */}
                    <div className="chat-header p-4 flex justify-between items-center sticky top-0 z-10 select-none">
                        <div className="flex items-center gap-2">
                            <Tooltip title={showHistory ? "Hide History" : "Show History"}>
                                <Button
                                    type="text"
                                    size="small"
                                    icon={<HistoryOutlined />}
                                    onClick={() => setShowHistory(!showHistory)}
                                    className="chat-icon-button"
                                />
                            </Tooltip>
                            <Avatar
                                size="small"
                                icon={<RobotOutlined />}
                                style={{ backgroundColor: '#0EA5E9' }}
                            />
                        </div>
                        <Space>
                            {!isComparisonMode && (
                                <>
                                    <Tooltip title={mode === "pdf" ? "Chatting with PDF" : "Chatting with Excel Data"}>
                                        <Segmented
                                            value={mode}
                                            onChange={setMode}
                                            className="chat-segmented-control"
                                            options={[
                                                { label: 'Excel (Rules)', value: 'excel', icon: <FileExcelOutlined /> },
                                                { label: 'PDF (Full)', value: 'pdf', icon: <FilePdfOutlined /> },
                                            ]}
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
                                    className={instructions ? "chat-instruction-button-active" : "chat-icon-button"}
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
                                    className="chat-icon-button"
                                />
                            </Tooltip>
                            <Button
                                type="text"
                                size="small"
                                icon={<CloseOutlined />}
                                onClick={onClose}
                                className="chat-icon-button"
                            />
                        </Space>
                    </div>

                    {/* Messages Area */}
                    <div className="chat-messages-area flex-1 overflow-y-auto p-4">
                        <List
                            itemLayout="horizontal"
                            dataSource={messages}
                            split={false}
                            renderItem={(item) => (
                                <div className={`chat-message-wrapper mb-4 flex ${item.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                    <div className={`max-w-[85%] ${item.role === 'user' ? 'order-1' : 'order-2'}`}>
                                        <div
                                            className={item.role === 'user'
                                                ? 'chat-message-user'
                                                : 'chat-message-assistant'
                                            }
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
                                                        className="chat-suggestion-chip flex items-center gap-2 p-2 text-sm text-gray-600"
                                                        onClick={() => handleSendMessage(suggestion)}
                                                    >
                                                        <BulbOutlined style={{ color: '#3b82f6' }} />
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
                            <div className="chat-loading flex justify-start mb-4">
                                <div className="chat-message-assistant">
                                    <Spin size="small" />
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input Area */}
                    <div className="chat-input-container p-4">
                        <Input
                            placeholder="Ask anything..."
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            onPressEnter={() => handleSendMessage()}
                            suffix={
                                <Button
                                    type="text"
                                    icon={<SendOutlined />}
                                    onClick={() => handleSendMessage()}
                                    disabled={!inputValue.trim() || loading}
                                    className="chat-send-button"
                                />
                            }
                            className="chat-input-field py-2 px-4"
                        />
                        <div className="text-center mt-2">
                            <Text type="secondary" style={{ fontSize: '10px' }}>
                                AI chat can make mistakes. Double-check replies.
                            </Text>
                        </div>
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
                className="chat-modal"
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
