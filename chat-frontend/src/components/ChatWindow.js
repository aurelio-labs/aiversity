import React, { useState, useEffect, useRef } from 'react';
import './ChatWindow.css';
import MessageBubble from './MessageBubble';
import InputArea from './InputArea';
import TypingIndicator from './TypingIndicator';

const ChatWindow = ({ messages, addMessage }) => {
  const [isTyping, setIsTyping] = useState(false);
  const [timeoutId, setTimeoutId] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
    
    // If a new message is received, clear the typing indicator and timeout
    if (messages.length > 0 && !messages[messages.length - 1].isUser) {
      setIsTyping(false);
      if (timeoutId) {
        clearTimeout(timeoutId);
        setTimeoutId(null);
      }
    }
  }, [messages, timeoutId]);

  const handleSend = async (message) => {
    await addMessage(message, true);
    setIsTyping(true);
    
    // Set a timeout to hide the typing indicator if no response is received
    const newTimeoutId = setTimeout(() => {
      setIsTyping(false);
      addMessage("Sorry, I didn't receive a response. Please try again.", false);
    }, 100000); // 10 seconds timeout

    setTimeoutId(newTimeoutId);
  };

  return (
    <div className="chat-window">
      <div className="messages-container">
        {messages.map((msg, index) => (
          <div key={index} className={`message-row ${msg.isUser ? 'user' : 'bot'}`}>
            <MessageBubble message={msg.text} isUser={msg.isUser} />
          </div>
        ))}
        {isTyping && (
          <div className="message-row bot">
            <TypingIndicator />
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <InputArea onSend={handleSend} />
    </div>
  );
};

export default ChatWindow;