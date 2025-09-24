import React from 'react';
import './Header.css';

const Header = () => {
  return (
    <header className="app-header">
      <div className="logo-container">
        <img
          src="https://sinarmastechnology.com/wp-content/uploads/2024/06/Sinarmas-Technology-Logo-1.png"
          alt="Sinarmas Technology Logo"
          className="logo-image"
        />
      </div>
      <nav className="header-nav">
        <a href="#dashboard">Dashboard</a>
        <a href="#companies">Companies</a>
        <a href="#reports">Reports</a>
      </nav>
      <button className="header-button">Get Started</button>
    </header>
  );
};

export default Header;
