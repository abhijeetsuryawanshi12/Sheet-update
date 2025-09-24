import React from 'react';
import './Loader.css';
import { motion } from 'framer-motion';

const Loader = () => {
  return (
    <motion.div 
      className="loader-container"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <div className="loader-spinner"></div>
    </motion.div>
  );
};

export default Loader;