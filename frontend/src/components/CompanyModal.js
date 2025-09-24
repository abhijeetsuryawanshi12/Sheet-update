import React from 'react';
import { motion } from 'framer-motion';
import { 
  FaTimes, FaBuilding, FaGlobe, FaFileInvoiceDollar, FaChartBar, FaChartLine, FaInfoCircle,
  FaTags, FaHandHoldingUsd, FaArrowUp, FaArrowDown, FaUsers, FaTable, FaBalanceScale,
  FaHandshake, FaFileSignature, FaWater
} from 'react-icons/fa';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';

// NOTE: You need to install recharts for the charts to work:
// npm install recharts

// --- MOCK DATA for demonstration ---
const mockPriceHistory = [
  { name: 'Q1 \'23', price: 110 }, { name: 'Q2 \'23', price: 125 },
  { name: 'Q3 \'23', price: 120 }, { name: 'Q4 \'23', price: 140 },
  { name: 'Q1 \'24', price: 155 }, { name: 'Q2 \'24', price: 150 },
];

const mockFundingTable = [
    { funding_date: '2022-10-20', share_class: 'Series C', amount_raised: '$250M', price_per_share: '$45.10', key_investors: 'Sequoia, a16z' },
    { funding_date: '2021-05-15', share_class: 'Series B', amount_raised: '$120M', price_per_share: '$28.50', key_investors: 'Tiger Global' },
    { funding_date: '2020-02-01', share_class: 'Series A', amount_raised: '$50M', price_per_share: '$15.00', key_investors: 'Insight Partners' },
    { funding_date: '2019-01-10', share_class: 'Seed', amount_raised: '$20M', price_per_share: '$5.00', key_investors: 'Y Combinator' },
];

// --- Helper Components ---
const Section = ({ title, icon, children }) => (
  <section className="mt-8">
    <div className="flex items-center gap-3 mb-4">
      <div className="text-primary-red text-xl">{icon}</div>
      <h3 className="text-xl font-bold text-primary-text">{title}</h3>
    </div>
    <div className="bg-gray-50 p-6 rounded-lg border border-border-color">
      {children}
    </div>
  </section>
);

const StatCard = ({ title, value, icon }) => (
  <div className="p-4 bg-white rounded-lg shadow-sm border border-border-color">
    <div className="flex items-start gap-3">
      <div className="text-gray-400 text-lg mt-1">{icon}</div>
      <div>
        <p className="text-sm text-secondary-text">{title}</p>
        <p className="text-lg font-bold text-primary-text">{value || 'N/A'}</p>
      </div>
    </div>
  </div>
);

const InterestTag = ({ interest }) => {
    if (!interest || interest === 'N/A') return <span className="text-gray-500">N/A</span>;
    const lowerInterest = interest.toLowerCase();
    let colorClasses = 'bg-gray-100 text-gray-800';
    if (lowerInterest === 'high') colorClasses = 'bg-red-100 text-red-800';
    else if (lowerInterest === 'medium') colorClasses = 'bg-yellow-100 text-yellow-800';
    else if (lowerInterest === 'low') colorClasses = 'bg-green-100 text-green-800';
    return <span className={`px-2.5 py-1 text-xs font-semibold rounded-full ${colorClasses}`}>{interest}</span>;
};

const ShareTag = ({ allowed }) => {
    if (!allowed || allowed === 'N/A') return <span className="text-gray-500">N/A</span>;
    const lowerAllowed = allowed.toLowerCase();
    let colorClasses = 'bg-gray-100 text-gray-800';
    if (lowerAllowed === 'yes') colorClasses = 'bg-green-100 text-green-800';
    else if (lowerAllowed === 'no') colorClasses = 'bg-red-100 text-red-800';
    return <span className={`px-2.5 py-1 text-xs font-semibold rounded-full ${colorClasses}`}>{allowed}</span>;
};

const parseJSON = (jsonString, fallback) => {
    if (!jsonString) return fallback;
    try {
        const data = JSON.parse(jsonString);
        return Array.isArray(data) ? data : fallback;
    } catch (e) {
        console.error("Failed to parse JSON string:", jsonString, e);
        return fallback;
    }
};

const CompanyModal = ({ company, onClose }) => {
  const priceHistory = parseJSON(company.price_history, mockPriceHistory);
  const fundingHistoryTable = parseJSON(company.funding_history, mockFundingTable);
  
  const fundingHistoryChart = (() => {
    const data = fundingHistoryTable || [];
    const byYear = data.reduce((acc, round) => {
      const year = round.funding_date?.split('-')[0];
      const amount = parseFloat(String(round.amount_raised).replace(/[^0-9.]/g, ''));
      if (year && !isNaN(amount)) {
        acc[year] = (acc[year] || 0) + amount;
      }
      return acc;
    }, {});
    const chartData = Object.entries(byYear).map(([year, amount]) => ({ year, amount })).sort((a,b) => a.year.localeCompare(b.year));
    return chartData.length > 0 ? chartData : [];
  })();

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
        className="bg-card-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto relative scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100"
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
                  target="_blank" rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-sm text-primary-red hover:underline"
                >
                  <FaGlobe /> {company.website}
                </a>
              )}
            </div>
          </div>

          {/* New Sections Layout */}
          
          <Section title="Company Details" icon={<FaInfoCircle />}>
            <p className="text-secondary-text mb-6 whitespace-pre-wrap">{company.summary || company.overview || 'No summary available.'}</p>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <StatCard title="Sector" value={company.sector} icon={<FaTags />} />
                <StatCard title="Valuation" value={company.valuation} icon={<FaFileInvoiceDollar />} />
                <StatCard title="Implied Valuation" value={company.implied_valuation} icon={<FaBalanceScale />} />
                <StatCard title="Sinarmas Interest" value={<InterestTag interest={company.sinarmas_interest} />} icon={<FaHandshake />} />
                <StatCard title="Share Transfer" value={<ShareTag allowed={company.share_transfer_allowed} />} icon={<FaFileSignature />} />
            </div>
            <h4 className="font-semibold text-primary-text mt-6 mb-2">Liquidity</h4>
             <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <StatCard title="EZ" value={company.liquidity_ez} icon={<FaWater />} />
                <StatCard title="Forge" value={company.liquidity_forge} icon={<FaWater />} />
                <StatCard title="Nasdaq" value={company.liquidity_nasdaq} icon={<FaWater />} />
            </div>
          </Section>

          <Section title="Active Market & Trade Metrics" icon={<FaChartBar />}>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-6">
              <StatCard title="Sellers Ask" value={company.sellers_ask} icon={<FaArrowUp className="text-red-500" />} />
              <StatCard title="Buyers Bid" value={company.buyers_bid} icon={<FaArrowDown className="text-green-500" />} />
              <StatCard title="Total Bids" value={company.total_bids} icon={<FaArrowDown />} />
              <StatCard title="Total Asks" value={company.total_asks} icon={<FaArrowUp />} />
              <StatCard title="Highest Bid" value={company.highest_bid_price} icon={<FaArrowUp className="text-green-500"/>} />
              <StatCard title="Lowest Ask" value={company.lowest_ask_price} icon={<FaArrowDown className="text-red-500"/>} />
            </div>
             <h4 className="font-semibold text-primary-text mb-2">Price History</h4>
            <div style={{ width: '100%', height: 300 }}>
              <ResponsiveContainer>
                <LineChart data={priceHistory}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis domain={['dataMin - 10', 'dataMax + 10']} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="price" stroke="#E63946" strokeWidth={2} activeDot={{ r: 8 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Section>

          <Section title="Funding Details" icon={<FaHandHoldingUsd />}>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
                <StatCard title="Total Funding" value={company.total_funding} icon={<FaHandHoldingUsd />} />
                <StatCard title="Latest Funding" value={company.latest_funding} icon={<FaFileInvoiceDollar />} />
                <StatCard title="Latest Funding Date" value={company.latest_funding_date} icon={<FaFileInvoiceDollar />} />
            </div>
            <div className="mb-6">
                <h4 className="font-semibold text-primary-text mb-1 flex items-center gap-2"><FaUsers /> Key Investors</h4>
                <p className="text-secondary-text">{company.investors || 'N/A'}</p>
            </div>
            <h4 className="font-semibold text-primary-text mb-2">Funding History (by Year)</h4>
             <div style={{ width: '100%', height: 300 }}>
                <ResponsiveContainer>
                    <BarChart data={fundingHistoryChart}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="year" />
                        <YAxis label={{ value: 'Amount (in millions)', angle: -90, position: 'insideLeft' }}/>
                        <Tooltip formatter={(value) => `$${value}M`} />
                        <Legend />
                        <Bar dataKey="amount" fill="#E63946" />
                    </BarChart>
                </ResponsiveContainer>
            </div>
            <h4 className="font-semibold text-primary-text mt-6 mb-2 flex items-center gap-2"><FaTable /> Funding Rounds</h4>
             <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-100">
                        <tr>
                            <th className="px-4 py-2 text-left text-xs font-bold text-secondary-text uppercase tracking-wider">Date</th>
                            <th className="px-4 py-2 text-left text-xs font-bold text-secondary-text uppercase tracking-wider">Share Class</th>
                            <th className="px-4 py-2 text-left text-xs font-bold text-secondary-text uppercase tracking-wider">Amount Raised</th>
                            <th className="px-4 py-2 text-left text-xs font-bold text-secondary-text uppercase tracking-wider">Price/Share</th>
                            <th className="px-4 py-2 text-left text-xs font-bold text-secondary-text uppercase tracking-wider">Key Investors</th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {fundingHistoryTable.map((round, index) => (
                            <tr key={index}>
                                <td className="px-4 py-2 whitespace-nowrap text-sm">{round.funding_date}</td>
                                <td className="px-4 py-2 whitespace-nowrap text-sm">{round.share_class}</td>
                                <td className="px-4 py-2 whitespace-nowrap text-sm">{round.amount_raised}</td>
                                <td className="px-4 py-2 whitespace-nowrap text-sm">{round.price_per_share}</td>
                                <td className="px-4 py-2 whitespace-nowrap text-sm">{round.key_investors}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
             </div>
          </Section>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default CompanyModal;
