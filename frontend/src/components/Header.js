import React from 'react';

const Header = () => {
  return (
    <header className="flex items-center justify-between px-8 py-4 bg-card-white shadow-md border-b-4 border-primary-red">
      <div className="flex items-center">
        <img
          src="https://sinarmastechnology.com/wp-content/uploads/2024/06/Sinarmas-Technology-Logo-1.png"
          alt="Sinarmas Technology Logo"
          className="h-10 w-auto"
        />
      </div>
      <nav className="hidden md:flex items-center gap-8">
        <a href="#dashboard" className="font-medium text-secondary-text hover:text-primary-text transition-colors duration-200 relative group">
          <span>Dashboard</span>
          <span className="absolute bottom-0 left-0 w-full h-0.5 bg-primary-red scale-x-0 group-hover:scale-x-100 transition-transform duration-300 origin-right group-hover:origin-left"></span>
        </a>
        <a href="#companies" className="font-medium text-secondary-text hover:text-primary-text transition-colors duration-200 relative group">
          <span>Companies</span>
          <span className="absolute bottom-0 left-0 w-full h-0.5 bg-primary-red scale-x-0 group-hover:scale-x-100 transition-transform duration-300 origin-right group-hover:origin-left"></span>
        </a>
        <a href="#reports" className="font-medium text-secondary-text hover:text-primary-text transition-colors duration-200 relative group">
          <span>Reports</span>
           <span className="absolute bottom-0 left-0 w-full h-0.5 bg-primary-red scale-x-0 group-hover:scale-x-100 transition-transform duration-300 origin-right group-hover:origin-left"></span>
        </a>
      </nav>
      <button className="px-6 py-2 bg-primary-red text-white font-semibold rounded-full shadow-sm hover:bg-secondary-red hover:scale-105 transform transition-all duration-200">
        Get Started
      </button>
    </header>
  );
};

export default Header;
