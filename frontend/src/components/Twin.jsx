import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User } from 'lucide-react';

export default function Twin() {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [sessionId, setSessionId] = useState('');
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const sendMessage = async () => {
        if (!input.trim() || isLoading) return;

        const userMessage = {
            id: Date.now().toString(),
            role: 'user',
            content: input,
            timestamp: new Date(),
        };

        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);

        try {
            const response = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: input,
                    session_id: sessionId || undefined,
                }),
            });

            if (!response.ok) throw new Error('Failed');

            const data = await response.json();

            if (!sessionId) setSessionId(data.session_id);

            const assistantMessage = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: data.response,
                timestamp: new Date(),
            };

            setMessages(prev => [...prev, assistantMessage]);
        } catch (err) {
            setMessages(prev => [
                ...prev,
                {
                    id: Date.now().toString(),
                    role: 'assistant',
                    content: 'Error connecting to server.',
                    timestamp: new Date(),
                },
            ]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            sendMessage();
        }
    };

    return (
        <div className="chat-container">
            {/* Header */}
            <div className="chat-header">
                <Bot size={20} />
                <div>
                    <h2>AI Assistant</h2>
                    <p>Ask anything</p>
                </div>
            </div>

            {/* Messages */}
            <div className="chat-body">
                {messages.length === 0 && (
                    <div className="empty">
                        <Bot size={40} />
                        <p>Start chatting...</p>
                    </div>
                )}

                {messages.map(msg => (
                    <div
                        key={msg.id}
                        className={`message ${msg.role}`}
                    >
                        {msg.role === 'assistant' && <Bot size={18} />}
                        <div className="bubble">
                            <p>{msg.content}</p>
                            <span>{msg.timestamp.toLocaleTimeString()}</span>
                        </div>
                        {msg.role === 'user' && <User size={18} />}
                    </div>
                ))}

                {isLoading && (
                    <div className="message assistant">
                        <Bot size={18} />
                        <div className="bubble typing">Typing...</div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="chat-input">
                <input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyPress}
                    placeholder="Type a message..."
                />
                <button onClick={sendMessage}>
                    <Send size={18} />
                </button>
            </div>
        </div>
    );
}