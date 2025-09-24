import React from 'react';
import { motion } from 'framer-motion';
import { 
  FaBuilding, FaGlobe, FaChartLine, FaUsers, FaMoneyBillAlt, FaCalendarAlt, FaTimes, 
  FaHandshake, FaFileSignature, FaWater, FaBalanceScale, FaInfoCircle 
} from 'react-icons/fa';

// A reusable component for displaying each piece of information
const InfoRow = ({ icon, label, children }) => (
  <div className="flex items-start gap-3 py-2">
    <div className="text-gray-500 mt-1">{icon}</div>
    <div className="flex-1">
      <strong className="block text-sm font-medium text-primary-text">{label}</strong>
      <div className="text-secondary-text break-words">{children}</div>
    </div>
  </div>
);

// A helper to create colored tags for "Sinarmas Interest"
const InterestTag = ({ interest }) => {
    if (!interest || interest === 'N/A') return <span className="text-gray-500">N/A</span>;
    const lowerInterest = interest.toLowerCase();
    let colorClasses = 'bg-gray-100 text-gray-800';
    if (lowerInterest === 'high') colorClasses = 'bg-red-100 text-red-800';
    else if (lowerInterest === 'medium') colorClasses = 'bg-yellow-100 text-yellow-800';
    else if (lowerInterest === 'low') colorClasses = 'bg-green-100 text-green-800';
    
    return <span className={`px-2.5 py-1 text-xs font-semibold rounded-full ${colorClasses}`}>{interest}</span>;
}

// A helper to create tags for "Share Transfer Allowed?"
const ShareTag = ({ allowed }) => {
    if (!allowed || allowed === 'N/A') return <span className="text-gray-500">N/A</span>;
    const lowerAllowed = allowed.toLowerCase();
    let colorClasses = 'bg-gray-100 text-gray-800';
    if (lowerAllowed === 'yes') colorClasses = 'bg-green-100 text-green-800';
    else if (lowerAllowed === 'no') colorClasses = 'bg-red-100 text-red-800';

    return <span className={`px-2.5 py-1 text-xs font-semibold rounded-full ${colorClasses}`}>{allowed}</span>;
}


const CompanyModal = ({ company, onClose }) => {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
      className="fixed inset-0 bg-black bg-opacity-60 z-50 flex items-center justify-center p-4"
    >
      <motion.div
        initial={{ y: -50, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: 50, opacity: 0 }}
        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-card-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto relative"
      >
        <button onClick={onClose} className="absolute top-4 right-4 text-gray-400 hover:text-primary-red transition-colors z-10">
          <FaTimes size={24} />
        </button>

        <div className="p-8">
          {/* Header */}
          <div className="flex items-center gap-4 mb-6 pb-6 border-b border-border-color">
            <div className="bg-red-50 p-3 rounded-xl">
                <FaBuilding className="text-primary-red text-3xl" />
            </div>
            <div>
                <h2 className="text-3xl font-bold text-primary-text">{company.name || 'N/A'}</h2>
                {company.website && (
                    <a
                        href={`//${company.website.replace(/^https?:\/\//, '')}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 text-sm text-primary-red hover:underline"
                    >
                        <FaGlobe /> {company.website}
                    </a>
                )}
            </div>
          </div>

          {/* Body */}
          <div className="space-y-6">
            {/* --- Section: Company Details --- */}
            <section>
              <h3 className="text-lg font-semibold text-primary-text mb-2">Company Details</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8">
                <InfoRow icon={<FaChartLine />} label="Sector">{company.sector || 'N/A'}</InfoRow>
                <InfoRow icon={<FaMoneyBillAlt />} label="Valuation">{company.valuation || 'N/A'}</InfoRow>
                <InfoRow icon={<FaBalanceScale />} label="Implied Valuation">{company.implied_valuation || 'N/A'}</InfoRow>
              </div>
            </section>
            
            {/* --- Section: Funding --- */}
            <section>
              <h3 className="text-lg font-semibold text-primary-text mb-2">Funding</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8">
                <InfoRow icon={<FaMoneyBillAlt />} label="Latest Funding">{company.latest_funding || 'N/A'}</InfoRow>
                <InfoRow icon={<FaCalendarAlt />} label="Latest Funding Date">{company.latest_funding_date || 'N/A'}</InfoRow>
                <InfoRow icon={<FaMoneyBillAlt />} label="Total Funding">{company.total_funding || 'N/A'}</InfoRow>
              </div>
               <InfoRow icon={<FaUsers />} label="Investors">{company.investors || 'N/A'}</InfoRow>
            </section>

            {/* --- Section: Internal & Liquidity --- */}
            <section>
              <h3 className="text-lg font-semibold text-primary-text mb-2">Internal & Liquidity</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-x-8">
                <InfoRow icon={<FaHandshake />} label="Sinarmas Interest"><InterestTag interest={company.sinarmas_interest} /></InfoRow>
                <InfoRow icon={<FaFileSignature />} label="Share Transfer"><ShareTag allowed={company.share_transfer_allowed} /></InfoRow>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-x-8 mt-2">
                 <InfoRow icon={<FaWater />} label="Liquidity EZ">{company.liquidity_ez || 'N/A'}</InfoRow>
                 <InfoRow icon={<FaWater />} label="Liquidity Forge">{company.liquidity_forge || 'N/A'}</InfoRow>
                 <InfoRow icon={<FaWater />} label="Liquidity Nasdaq">{company.liquidity_nasdaq || 'N/A'}</InfoRow>
              </div>
            </section>

            {/* --- Section: Overview --- */}
            <section>
              <h3 className="text-lg font-semibold text-primary-text mb-2">Overview</h3>
              <InfoRow icon={<FaInfoCircle />} label="">
                <p className="text-secondary-text whitespace-pre-wrap">{company.overview || 'N/A'}</p>
              </InfoRow>
            </section>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default CompanyModal;
