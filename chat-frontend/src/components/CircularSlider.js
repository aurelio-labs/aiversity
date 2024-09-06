import React, { useState, useRef, useEffect } from 'react';

const CircularSlider = ({ value, onChange }) => {
  const [isDragging, setIsDragging] = useState(false);
  const sliderRef = useRef(null);

  const handleMouseDown = () => setIsDragging(true);
  const handleMouseUp = () => setIsDragging(false);

  const handleMouseMove = (event) => {
    if (!isDragging) return;

    const slider = sliderRef.current;
    const rect = slider.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;

    const angle = Math.atan2(event.clientY - centerY, event.clientX - centerX);
    let newValue = ((angle + Math.PI) / (2 * Math.PI)) * 100;

    // Adjust the range to start from the top
    newValue = (newValue + 25) % 100;

    onChange(newValue);
  };

  useEffect(() => {
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging]);

  const rotation = (value / 100) * 360;

  return (
    <div
      ref={sliderRef}
      onMouseDown={handleMouseDown}
      style={{
        width: '100px',
        height: '100px',
        borderRadius: '50%',
        border: '2px solid #CC785C',
        position: 'relative',
        cursor: 'pointer'
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: '0',
          left: '50%',
          width: '2px',
          height: '50%',
          background: '#CC785C',
          transformOrigin: 'bottom',
          transform: `translateX(-50%) rotate(${rotation}deg)`
        }}
      />
    </div>
  );
};

export default CircularSlider;