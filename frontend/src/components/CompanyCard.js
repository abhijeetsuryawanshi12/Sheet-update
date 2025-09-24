import React from 'react';
import './CompanyCard.css';
import { 
  FaBuilding, FaGlobe, FaChartLine, FaUsers, FaMoneyBillAlt, FaCalendarAlt, 
  FaHandshake, FaFileSignature 
} from 'react-icons/fa';
import { motion } from 'framer-motion';

const CompanyCard = ({ company, onClick }) => {
  // No formatting needed, just display the string
  const valuation = company.valuation || 'N/A';

  return (
    <motion.div
      className="company-card"
      whileHover={{ y: -5, boxShadow: 'var(--shadow-hover)' }}
      transition={{ duration: 0.2 }}
      onClick={onClick} // Added onClick handler
    >
      <div className="card-header">
        <FaBuilding className="company-icon" />
        <h3 className="company-name">{company.name}</h3>
      </div>
      <div className="card-body">
        <p className="card-info">
          <FaChartLine className="info-icon" />
          <strong>Sector:</strong> {company.sector || 'N/A'}
        </p>
        <p className="card-info">
          <FaUsers className="info-icon" />
          <strong>Investors:</strong> {(company.investors && company.investors.length > 50) ? company.investors.substring(0, 50) + '...' : (company.investors || 'N/A')}
        </p>
        <p className="card-info">
          <FaMoneyBillAlt className="info-icon" />
          <strong>Latest Funding:</strong> {company.latest_funding || 'N/A'}
        </p>
        <p className="card-info">
          <FaCalendarAlt className="info-icon" />
          <strong>Latest Funding Date:</strong> {company.latest_funding_date || 'N/A'}
        </p>
        <p className="card-info valuation">
          <strong>Valuation:</strong> {valuation}
        </p>
        {/* New Fields */}
        <p className="card-info">
            <FaHandshake className="info-icon" />
            <strong>Sinarmas Interest:</strong> {company.sinarmas_interest || 'N/A'}
        </p>
        <p className="card-info">
            <FaFileSignature className="info-icon" />
            <strong>Share Transfer:</strong> {company.share_transfer_allowed || 'N/A'}
        </p>
      </div>
      <div className="card-footer">
        {company.website ? (
          <a
            href={`//${company.website.replace(/^https?:\/\//, '')}`}
            target="_blank"
            rel="noopener noreferrer"
            className="website-link"
            onClick={(e) => e.stopPropagation()} // Prevent card click when link is clicked
          >
            <FaGlobe /> Visit Website
          </a>
        ) : (
          <span className="no-website">No Website</span>
        )}
      </div>
    </motion.div>
  );
};

export default CompanyCard;
