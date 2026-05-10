import React from 'react';
import './Input.css';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Input: React.FC<InputProps> = ({
  label,
  error,
  leftIcon,
  rightIcon,
  className = '',
  ...props
}) => {
  return (
    <div className={`mt-input-wrapper ${className}`}>
      {label && <label className="mt-input-label">{label}</label>}
      <div className={`mt-input-container ${error ? 'mt-input-error' : ''}`}>
        {leftIcon && <span className="mt-input-icon-left">{leftIcon}</span>}
        <input className="mt-input-field" {...props} />
        {rightIcon && <span className="mt-input-icon-right">{rightIcon}</span>}
      </div>
      {error && <span className="mt-input-error-text">{error}</span>}
    </div>
  );
};
