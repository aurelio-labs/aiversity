import React, { useState } from 'react';
import './InputArea.css';

const InputArea = ({ onSend }) => {
  const [message, setMessage] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim()) {
      onSend(message);
      setMessage('');
    }
  };

  return (
    <form className="input-area" onSubmit={handleSubmit}>
      <input
        type="text"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Type a message..."
      />
      <button type="submit" aria-label="Send message">
        <span className="send-icon">➤</span>
      </button>
    </form>
  );
};

export default InputArea;