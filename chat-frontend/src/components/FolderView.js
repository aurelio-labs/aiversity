import React, { useState, useEffect, useRef } from 'react';
import './FolderView.css';

const FolderView = () => {
  const IRIS_ROOT = '/Users/rob/Github/MSC/aiversity/aiversity_workspaces/Iris-5000/';
  const [isOpen, setIsOpen] = useState(false);
  const [currentPath, setCurrentPath] = useState('');
  const [folderContent, setFolderContent] = useState([]);
  const [newItems, setNewItems] = useState([]);
  const [selectedItems, setSelectedItems] = useState([]);
  const [editingFile, setEditingFile] = useState(null);
  const [fileContent, setFileContent] = useState('');
  const folderContentRef = useRef(null);
  const wsRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      fetchFolderContent(currentPath);
      setupWebSocket();
    }
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [isOpen, currentPath]);

  const setupWebSocket = () => {
    wsRef.current = new WebSocket('ws://localhost:5000/ws-folder-updates');
    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'file_change') {
        if (data.change_type === 'file_added' || data.change_type === 'file_deleted') {
          setNewItems(prev => [...prev, data.file]);
          setTimeout(() => {
            setNewItems(prev => prev.filter(item => item !== data.file));
            fetchFolderContent(currentPath);
          }, 3000); // Remove highlight after 3 seconds
        }
      }
    };
  };

  const fetchFolderContent = async (path) => {
    try {
      const fullPath = IRIS_ROOT + path;
      const response = await fetch(`http://localhost:5000/folder-content/?path=${encodeURIComponent(fullPath)}`);
      if (!response.ok) {
        throw new Error('Failed to fetch folder content');
      }
      const data = await response.json();
      setFolderContent(data.content);
      setCurrentPath(path);
    } catch (error) {
      console.error('Error fetching folder content:', error);
    }
  };

  const fetchFileContent = async (fileName) => {
    try {
      const fullPath = IRIS_ROOT + currentPath + fileName;
      const response = await fetch(`http://localhost:5000/file-content/?path=${encodeURIComponent(fullPath)}`);
      if (!response.ok) {
        throw new Error('Failed to fetch file content');
      }
      const data = await response.json();
      return data.content;
    } catch (error) {
      console.error('Error fetching file content:', error);
      return '';
    }
  };

  const handleItemClick = (item) => {
    if (item.type === 'folder') {
      setCurrentPath(prevPath => {
        if (item.name === '..') {
          const parts = prevPath.split('/').filter(Boolean);
          parts.pop();
          return parts.length ? `${parts.join('/')}/` : '';
        } else {
          return `${prevPath}${item.name}/`;
        }
      });
    } else {
      handleAction('view', item);
    }
  };

  const handleAction = async (action, file) => {
    if (action === 'view' || action === 'edit') {
      try {
        const content = await fetchFileContent(file.name);
        setEditingFile({ ...file, content });
        setFileContent(content);
      } catch (error) {
        console.error('Error fetching file content:', error);
      }
    } else if (action === 'delete') {
      // Implement delete functionality
      console.log('Delete functionality not implemented yet');
    }
  };

  const handleSaveFile = async () => {
    if (!editingFile) return;

    try {
      const fullPath = IRIS_ROOT + currentPath + editingFile.name;
      const response = await fetch('http://localhost:5000/save-file/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          path: fullPath,
          content: fileContent,
        }),
      });
      if (!response.ok) {
        throw new Error('Failed to save file');
      }
      setEditingFile(null);
      fetchFolderContent(currentPath);
    } catch (error) {
      console.error('Error saving file:', error);
    }
  };

  const renderFileItem = (item, index) => (
    <div
      id={`file-item-${item.name}`}
      key={index}
      className={`file-item ${newItems.includes(item.name) ? 'new-item' : ''} ${
        selectedItems.includes(item) ? 'selected' : ''
      }`}
      onClick={() => handleItemClick(item)}
      style={{animationDelay: `${index * 0.05}s`}}
    >
      <div className="file-icon">
        {item.type === 'folder' ? '📁' : '📄'}
      </div>
      <div className="file-name">{item.name}</div>
    </div>
  );

  const renderBreadcrumbs = () => {
    const parts = currentPath.split('/').filter(Boolean);
    return (
      <div className="breadcrumbs">
        <span onClick={() => setCurrentPath('')}>Iris-5000</span>
        {parts.map((part, index) => (
          <React.Fragment key={index}>
            <span className="separator">/</span>
            <span onClick={() => setCurrentPath(parts.slice(0, index + 1).join('/') + '/')}>
              {part}
            </span>
          </React.Fragment>
        ))}
      </div>
    );
  };

  return (
    <>
      <div className="folder-container">
        <button className={`folder-icon ${isOpen ? 'spin' : ''}`} onClick={() => setIsOpen(!isOpen)}>
          📁
        </button>
      </div>
      <div className={`folder-view-overlay ${isOpen ? 'open' : ''}`}>
        <div className="folder-view">
          <div className="folder-header">
            {renderBreadcrumbs()}
            <button className="close-folder" onClick={() => setIsOpen(false)}>✕</button>
          </div>
          <div
            ref={folderContentRef}
            className="folder-content"
          >
            {currentPath !== '' && renderFileItem({ name: '..', type: 'folder' }, 'up')}
            {folderContent.map((item, index) => renderFileItem(item, index))}
          </div>
        </div>
      </div>
      <div className={`file-editor-overlay ${editingFile ? 'open' : ''}`}>
        <div className="file-editor">
          <h2>{editingFile?.name}</h2>
          <textarea
            value={fileContent}
            onChange={(e) => setFileContent(e.target.value)}
          ></textarea>
          <div className="editor-actions">
            <button onClick={handleSaveFile}>Save</button>
            <button onClick={() => setEditingFile(null)}>Cancel</button>
          </div>
        </div>
      </div>
    </>
  );
};

export default FolderView;