import React from 'react';
import { motion } from 'framer-motion';
import { FaBuilding, FaGlobe, FaChartLine, FaUsers, FaMoneyBillAlt, FaCalendarAlt, FaTimes } from 'react-icons/fa';

const InfoRow = ({ icon, label, value }) => (
  <div className="flex items-start gap-4 text-sm mb-3">
    <div className="text-primary-text mt-1">{icon}</div>
    <div className="flex-1">
      <strong className="block text-primary-text">{label}:</strong>
      <span className="text-secondary-text break-words">{value || 'N/A'}</span>
    </div>
  </div>
);

const CompanyModal = ({ company, onClose }) => {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
      className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
    >
      <motion.div
        initial={{ y: -50, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: 50, opacity: 0 }}
        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        onClick={(e) => e.stopPropagation()} // Prevent closing modal when clicking inside
        className="bg-card-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto relative border-l-8 border-primary-red"
      >
        <button onClick={onClose} className="absolute top-4 right-4 text-gray-400 hover:text-primary-red transition-colors">
          <FaTimes size={24} />
        </button>

        <div className="p-8">
          {/* Header */}
          <div className="flex items-center gap-4 mb-6 pb-6 border-b border-border-color">
            <FaBuilding className="text-primary-red text-4xl" />
            <h2 className="text-3xl font-bold text-primary-text">{company.name}</h2>
          </div>

          {/* Body */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4">
            <InfoRow icon={<FaChartLine />} label="Sector" value={company.sector} />
            <InfoRow icon={<FaMoneyBillAlt />} label="Valuation" value={company.valuation} />
            <InfoRow icon={<FaMoneyBillAlt />} label="Latest Funding" value={company.latest_funding} />
            <InfoRow icon={<FaCalendarAlt />} label="Latest Funding Date" value={company.latest_funding_date} />
            <InfoRow icon={<FaMoneyBillAlt />} label="Total Funding" value={company.total_funding} />
          </div>
          
          <div className="mt-4">
            <InfoRow icon={<FaUsers />} label="Investors" value={company.investors} />
            <InfoRow icon={<FaUsers />} label="Overview" value={company.overview} />
          </div>

          {/* Footer */}
          <div className="mt-8 text-center">
            {company.website ? (
              <a
                href={`//${company.website.replace(/^https?:\/\//, '')}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-6 py-2 bg-transparent text-primary-red border-2 border-primary-red rounded-full font-semibold hover:bg-primary-red hover:text-white transition-all duration-200"
              >
                <FaGlobe /> Visit Website
              </a>
            ) : (
              <span className="text-gray-400 italic">No Website</span>
            )}
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default CompanyModal;