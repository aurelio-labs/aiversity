import React, { useEffect, useRef, useState } from 'react';
import './SharedWorkspace.css';

const SharedWorkspace = ({ isOpen, actions }) => {
  const actionFeedRef = useRef(null);
  const [highlightedAction, setHighlightedAction] = useState(null);

  useEffect(() => {
    if (actionFeedRef.current) {
      actionFeedRef.current.scrollTop = actionFeedRef.current.scrollHeight;
    }
    if (actions.length > 0) {
      setHighlightedAction(actions.length - 1);
      setTimeout(() => setHighlightedAction(null), 2000);
    }
  }, [actions]);

  const formatAction = (action, index) => {
    if (typeof action === 'string') {
      try {
        const parsedAction = JSON.parse(action);
        return formatParsedAction(parsedAction, index);
      } catch (error) {
        console.error('Error parsing action:', error);
        return action;
      }
    } else if (action.type === 'execution_update') {
      return formatAction(action.data, index);
    }
    return JSON.stringify(action);
  };

  const formatParsedAction = (parsedAction, index) => {
    const { action, params } = parsedAction;
    const isHighlighted = index === highlightedAction;
    let icon, description;

    switch (action) {
      case 'run_command':
        icon = '🖥️';
        description = `Ran command: ${params.command}`;
        break;
      case 'view_file_contents':
        icon = '📄';
        description = `Viewed file: ${params.file_path}`;
        break;
      case 'edit_file_contents':
        icon = '✏️';
        description = `Edited file: ${params.file_path}`;
        break;
      case 'create_new_file':
        icon = '📝';
        description = `Created new file: ${params.file_path}`;
        break;
      case 'run_python_file':
        icon = '🐍';
        description = `Ran Python file: ${params.file_path}`;
        break;
      case 'perplexity_search':
        icon = '🔍';
        description = `Searched: ${params.query}`;
        break;
      case 'send_message_to_student':
        icon = '➡️';
        description = `Sent message to student`;
        break;
      case 'send_niacl_message':
        icon = '📨';
        description = `Sent NIACL message to: ${params.receiver}`;
        break;
      case 'visualize_image':
        icon = '🖼️';
        description = `Visualized image: ${params.file_path}`;
        break;
      case 'delegate_and_execute_task':
        icon = '📋';
        description = `Delegated task: ${params.task_name}`;
        break;
      case 'declare_complete':
        icon = '✅';
        description = `Declared task complete`;
        break;
      default:
        icon = '❓';
        description = `${action}: ${JSON.stringify(params)}`;
    }

    return (
      <div key={index} className={`action-entry ${isHighlighted ? 'highlighted' : ''}`}>
        <span className="action-icon">{icon}</span>
        <span className="action-text">{description}</span>
      </div>
    );
  };

  return (
    <div className={`shared-workspace ${isOpen ? 'open' : ''}`}>
      <h2>Agent Actions</h2>
      <div className="action-feed" ref={actionFeedRef}>
        {actions.map((action, index) => formatAction(action, index))}
      </div>
    </div>
  );
};

export default SharedWorkspace;