import React from 'react';
import './Card.css';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  padding?: 'none' | 'sm' | 'md' | 'lg';
  variant?: 'glass' | 'surface' | 'elevated' | 'outline';
  onClick?: () => void;
  style?: React.CSSProperties;
}

export const Card: React.FC<CardProps> = ({
  children,
  className = '',
  padding = 'md',
  variant = 'surface',
  onClick,
  style,
}) => {
  const paddingClass = `card-padding-${padding}`;
  const variantClass = `card-variant-${variant}`;
  const interactiveClass = onClick ? 'card-interactive' : '';

  return (
    <div 
      className={`card ${paddingClass} ${variantClass} ${interactiveClass} ${className}`}
      onClick={onClick}
      style={style}
    >
      {children}
    </div>
  );
};

export const CardHeader: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className = '' }) => (
  <div className={`card-header ${className}`}>{children}</div>
);

export const CardContent: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className = '' }) => (
  <div className={`card-content ${className}`}>{children}</div>
);

export const CardFooter: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className = '' }) => (
  <div className={`card-footer ${className}`}>{children}</div>
);
