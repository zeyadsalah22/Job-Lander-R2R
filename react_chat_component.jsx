// React Component for Streaming Chat
import React, { useState, useEffect, useRef } from 'react';

const ChatBot = ({ userId }) => {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef(null);

  // Auto scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Initialize chat session
  const initializeChat = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`/api/chatbot/initialize/${userId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setSessionId(data.session_id);
        setIsInitialized(true);
        
        // Add welcome message
        setMessages([{
          id: Date.now(),
          type: 'bot',
          content: 'Hello! I\'m your job application assistant. I can help you with questions about your applications, companies, and interview progress. What would you like to know?',
          timestamp: new Date().toISOString()
        }]);
      } else {
        throw new Error('Failed to initialize chat');
      }
    } catch (error) {
      console.error('Error initializing chat:', error);
      alert('Failed to initialize chat. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  // Send message with streaming response
  const sendMessage = async () => {
    if (!inputMessage.trim() || !sessionId || isStreaming) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputMessage.trim(),
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsStreaming(true);

    // Create bot message placeholder
    const botMessageId = Date.now() + 1;
    const botMessage = {
      id: botMessageId,
      type: 'bot',
      content: '',
      timestamp: new Date().toISOString(),
      isComplete: false
    };

    setMessages(prev => [...prev, botMessage]);

    try {
      const response = await fetch('/api/chatbot/send-message', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sessionId: sessionId,
          message: userMessage.content
        })
      });

      if (!response.ok) {
        throw new Error('Failed to send message');
      }

      // Handle streaming response
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (data.type === 'content') {
                // Update bot message content
                setMessages(prev => prev.map(msg => 
                  msg.id === botMessageId 
                    ? { ...msg, content: msg.content + data.data }
                    : msg
                ));
              } else if (data.type === 'metadata' && data.is_final) {
                // Mark message as complete
                setMessages(prev => prev.map(msg => 
                  msg.id === botMessageId 
                    ? { ...msg, isComplete: true }
                    : msg
                ));
              } else if (data.type === 'error') {
                // Handle error
                setMessages(prev => prev.map(msg => 
                  msg.id === botMessageId 
                    ? { ...msg, content: data.data, isComplete: true, isError: true }
                    : msg
                ));
              }
            } catch (e) {
              console.error('Error parsing streaming data:', e);
            }
          }
        }
      }
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => prev.map(msg => 
        msg.id === botMessageId 
          ? { ...msg, content: 'Sorry, there was an error processing your message. Please try again.', isComplete: true, isError: true }
          : msg
      ));
    } finally {
      setIsStreaming(false);
    }
  };

  // Close chat session
  const closeChat = async () => {
    if (!sessionId) return;

    try {
      await fetch('/api/chatbot/close-chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ sessionId })
      });

      // Reset state
      setSessionId(null);
      setIsInitialized(false);
      setMessages([]);
    } catch (error) {
      console.error('Error closing chat:', error);
    }
  };

  // Handle Enter key press
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  if (!isInitialized) {
    return (
      <div className="chat-container">
        <div className="chat-header">
          <h3>Job Application Assistant</h3>
        </div>
        <div className="chat-body">
          <div className="welcome-screen">
            <h4>Welcome to your personal job application assistant!</h4>
            <p>I can help you with questions about your job applications, companies you've applied to, interview status, and more.</p>
            <button 
              onClick={initializeChat} 
              disabled={isLoading}
              className="btn btn-primary"
            >
              {isLoading ? 'Initializing...' : 'Start Chat'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h3>Job Application Assistant</h3>
        <button onClick={closeChat} className="btn btn-secondary btn-sm">
          Close Chat
        </button>
      </div>
      
      <div className="chat-messages">
        {messages.map((message) => (
          <div 
            key={message.id} 
            className={`message ${message.type} ${message.isError ? 'error' : ''}`}
          >
            <div className="message-content">
              {message.content}
              {message.type === 'bot' && !message.isComplete && (
                <span className="typing-indicator">●●●</span>
              )}
            </div>
            <div className="message-timestamp">
              {new Date(message.timestamp).toLocaleTimeString()}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input">
        <div className="input-group">
          <textarea
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask me about your job applications..."
            disabled={isStreaming}
            rows="2"
            className="form-control"
          />
          <button 
            onClick={sendMessage}
            disabled={!inputMessage.trim() || isStreaming}
            className="btn btn-primary"
          >
            {isStreaming ? 'Sending...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatBot; 