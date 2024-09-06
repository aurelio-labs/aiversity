import React, { useEffect, useState } from 'react';
import './MessageBubble.css';

const MessageBubble = ({ message, isUser }) => {
  const [opacity, setOpacity] = useState(0);
  const [transform, setTransform] = useState('translateY(20px)');

  useEffect(() => {
    // Start the animation after a short delay
    const timer = setTimeout(() => {
      setOpacity(1);
      setTransform('translateY(0)');
    }, 50);

    return () => clearTimeout(timer);
  }, []);

  // Format the message to preserve newlines and spacing
  const formattedMessage = message.split('\n').map((line, index) => (
    <React.Fragment key={index}>
      {line}
      {index < message.split('\n').length - 1 && <br />}
    </React.Fragment>
  ));

  return (
    <div 
      className={`message-bubble ${isUser ? 'user' : 'bot'}`}
      style={{
        opacity: opacity,
        transform: transform,
        transition: 'opacity 0.5s ease, transform 0.5s ease'
      }}
    >
      <pre>{formattedMessage}</pre>
    </div>
  );
};

export default MessageBubble;