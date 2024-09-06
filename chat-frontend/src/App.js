import React, { useState, useEffect, useCallback, useRef } from 'react';
import './App.css';
import ChatWindow from './components/ChatWindow';
import SharedWorkspace from './components/SharedWorkspace';
import FolderView from './components/FolderView';

function App() {
  const [folderContent, setFolderContent] = useState([]);
  const [currentPath, setCurrentPath] = useState('/');

  const [messages, setMessages] = useState([]);
  const [isWorkspaceOpen, setIsWorkspaceOpen] = useState(false);
  const [agentActions, setAgentActions] = useState([]);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [userId, setUserId] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef(null);

  const setupWebSocket = useCallback((id) => {
    socketRef.current = new WebSocket(`ws://localhost:5000/ws-chat/${id}`);

    socketRef.current.onopen = () => {
      console.log('WebSocket connection established');
      setIsConnected(true);
    };

    socketRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('Received message from WebSocket:', data);
      if (data.content) {
        setMessages(prevMessages => [...prevMessages, { text: data.content, isUser: false }]);
      }
      if (data.type === 'execution_update' || data.type === 'actions') {
        setAgentActions(prevActions => [...prevActions, data]);
      }
    };

    socketRef.current.onclose = () => {
      console.log('WebSocket connection closed');
      setIsConnected(false);
      // Attempt to reconnect after a delay
      setTimeout(() => setupWebSocket(id), 3000);
    };
  }, []);

  useEffect(() => {
    if (userId) {
      setupWebSocket(userId);
    }

    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [userId, setupWebSocket]);

  useEffect(() => {
    const timeInterval = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timeInterval);
  }, []);

  const addMessage = useCallback(async (message, isUser) => {
    setMessages(prevMessages => [...prevMessages, { text: message, isUser }]);

    if (isUser) {
      try {
        const response = await fetch('http://localhost:5000/chat/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ message, user_id: userId || '' }),
        });

        if (!response.ok) {
          throw new Error('Failed to send message');
        }

        const data = await response.json();
        if (!userId && data.user_id) {
          setUserId(data.user_id);
          console.log('User ID set:', data.user_id);
        }
      } catch (error) {
        console.error('Error sending message:', error);
        setMessages(prevMessages => [...prevMessages, { text: 'Error: Failed to send message. Please try again.', isUser: false }]);
      }
    }
  }, [userId]);

  const clearChat = useCallback(() => {
    setMessages([]);
    setAgentActions([]);
  }, []);

  const toggleWorkspace = useCallback(() => {
    setIsWorkspaceOpen(prev => !prev);
  }, []);

  const formatTime = useCallback((date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }, []);

  const fetchFolderContent = useCallback(async (path) => {
    try {
      const response = await fetch(`http://localhost:5000/folder-content`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ path, user_id: userId }),
      });

      if (!response.ok) {
        throw new Error('Failed to fetch folder content');
      }

      const data = await response.json();
      setFolderContent(data.content);
      setCurrentPath(path);
    } catch (error) {
      console.error('Error fetching folder content:', error);
    }
  }, [userId]);

  useEffect(() => {
    if (userId) {
      fetchFolderContent('/');
    }
  }, [userId, fetchFolderContent]);

  const handleFileAction = useCallback(async (action, path, type) => {
    try {
      const response = await fetch(`http://localhost:5000/file-action`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action, path, type, user_id: userId }),
      });

      if (!response.ok) {
        throw new Error('Failed to perform file action');
      }

      // Refresh folder content after action
      fetchFolderContent(currentPath);

      // Add a message to the chat about the file action
      const actionMessage = `File ${action}: ${path}`;
      setMessages(prevMessages => [...prevMessages, { text: actionMessage, isUser: false }]);
    } catch (error) {
      console.error('Error performing file action:', error);
    }
  }, [userId, currentPath, fetchFolderContent]);

  return (
    <div className="App">
      <div className="app-container">
        <SharedWorkspace isOpen={isWorkspaceOpen} actions={agentActions} />
        <div className="main-interface">
          <div className="phone-container">
            <div className="phone-notch"></div>
            <div className="status-bar">
              <span>{formatTime(currentTime)}</span>
              <span className="connection-status">
                <i className="fas fa-signal"></i>
                <i className="fas fa-wifi"></i>
                <i className="fas fa-battery-full"></i>
                <span className={`connection-dot ${isConnected ? 'connected' : ''}`}></span>
              </span>
            </div>
            <ChatWindow messages={messages} addMessage={addMessage} />
            <div className="control-panel">
              <button className="control-btn toggle-workspace" onClick={toggleWorkspace} title="Toggle Agent Actions">
                {isWorkspaceOpen ? '《' : '》'}
              </button>
              <button className="control-btn clear-chat" onClick={clearChat} title="Clear Chat">
                <span className="clear-icon">×</span>
              </button>
              <FolderView />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;