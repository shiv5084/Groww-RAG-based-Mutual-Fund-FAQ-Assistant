'use client';

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Home, 
  Settings, 
  HelpCircle, 
  ChevronRight, 
  Menu, 
  X,
  TrendingUp,
  PieChart,
  Shield,
  Zap,
  Briefcase,
  Lock,
  Wallet
} from 'lucide-react';

interface FundDetails {
  expenseRatio: string;
  nav: string;
  exitLoad: string;
  lockIn: string;
  minSip: string;
  aum: string;
  riskometer: string;
}

interface Fund {
  id: string;
  name: string;
  details: FundDetails;
}

const SUPPORTED_FUNDS: Fund[] = [
  {
    id: 'hdfc-large-cap',
    name: 'HDFC Large Cap Fund — Direct Growth',
    details: {
      expenseRatio: '0.85%',
      nav: '₹124.50',
      exitLoad: '1% if redeemed within 1 year',
      lockIn: 'None',
      minSip: '₹500',
      aum: '₹34,000 Cr',
      riskometer: 'Very High'
    }
  },
  {
    id: 'hdfc-elss-tax',
    name: 'HDFC ELSS Tax Saver — Direct Plan Growth',
    details: {
      expenseRatio: '1.12%',
      nav: '₹1,245.32',
      exitLoad: 'Nil',
      lockIn: '3 Years',
      minSip: '₹500',
      aum: '₹15,200 Cr',
      riskometer: 'Very High'
    }
  },
  {
    id: 'hdfc-focused',
    name: 'HDFC Focused Fund — Direct Growth',
    details: {
      expenseRatio: '0.98%',
      nav: '₹85.42',
      exitLoad: '1% if redeemed within 1 year',
      lockIn: 'None',
      minSip: '₹500',
      aum: '₹8,400 Cr',
      riskometer: 'Very High'
    }
  },
  {
    id: 'hdfc-equity',
    name: 'HDFC Equity Fund — Direct Growth',
    details: {
      expenseRatio: '1.05%',
      nav: '₹1,450.12',
      exitLoad: '1% if redeemed within 1 year',
      lockIn: 'None',
      minSip: '₹500',
      aum: '₹42,000 Cr',
      riskometer: 'Very High'
    }
  },
  {
    id: 'hdfc-mid-cap',
    name: 'HDFC Mid Cap Fund — Direct Growth',
    details: {
      expenseRatio: '0.92%',
      nav: '₹156.80',
      exitLoad: '1% if redeemed within 1 year',
      lockIn: 'None',
      minSip: '₹500',
      aum: '₹52,000 Cr',
      riskometer: 'Very High'
    }
  }
];

export default function Sidebar({ onToggle }: { onToggle?: (isOpen: boolean) => void }) {
  const [isOpen, setIsOpen] = useState(true);
  const [selectedFund, setSelectedFund] = useState<Fund | null>(null);
  const [activeFundPos, setActiveFundPos] = useState<number>(0);
  const [isMobile, setIsMobile] = useState(false);
  const submenuRef = useRef<HTMLDivElement>(null);

  // Handle responsiveness
  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth < 1024;
      setIsMobile(mobile);
      const newIsOpen = mobile ? false : true;
      setIsOpen(newIsOpen);
      if (onToggle) onToggle(newIsOpen);
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [onToggle]);

  // Close submenu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (submenuRef.current && !submenuRef.current.contains(event.target as Node)) {
        setSelectedFund(null);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const toggleSidebar = () => {
    const newState = !isOpen;
    setIsOpen(newState);
    if (onToggle) onToggle(newState);
  };

  const sidebarVariants = {
    open: { 
      width: isMobile ? '100%' : '320px',
      x: 0,
      transition: { type: 'spring', stiffness: 300, damping: 30 }
    },
    closed: { 
      width: isMobile ? '0px' : '80px',
      x: isMobile ? -320 : 0,
      transition: { type: 'spring', stiffness: 300, damping: 30 }
    }
  };

  const submenuVariants = {
    hidden: { 
      opacity: 0, 
      x: -30, 
      rotateY: -35, 
      perspective: 1000,
      scale: 0.9,
    },
    visible: { 
      opacity: 1, 
      x: 0, 
      rotateY: 0, 
      perspective: 1000,
      scale: 1,
      transition: { 
        type: 'spring', 
        stiffness: 200, 
        damping: 20 
      }
    },
    exit: { 
      opacity: 0, 
      x: -20, 
      rotateY: -25, 
      scale: 0.95,
      transition: { duration: 0.2 },
    }
  };

  return (
    <>
      {/* Mobile Toggle Button */}
      {isMobile && !isOpen && (
        <motion.button 
          initial={{ scale: 0, rotate: -180 }}
          animate={{ scale: 1, rotate: 0 }}
          onClick={toggleSidebar}
          className="fixed top-4 left-4 z-50 p-3 bg-green-600 text-white rounded-full shadow-[0_0_20px_rgba(34,197,94,0.4)] hover:bg-green-500 transition-colors border border-green-400/30"
        >
          <Menu size={24} />
        </motion.button>
      )}

      {/* Sidebar Overlay for Mobile */}
      <AnimatePresence>
        {isMobile && isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={toggleSidebar}
            className="fixed inset-0 bg-black/80 backdrop-blur-md z-[45]"
          />
        )}
      </AnimatePresence>

      <motion.aside
        initial={false}
        animate={isOpen ? 'open' : 'closed'}
        variants={sidebarVariants}
        onClick={() => !isOpen && toggleSidebar()}
        className={`fixed left-0 top-0 h-screen z-50 bg-[#06140d] border-r border-green-500/20 flex flex-col overflow-visible shadow-[10px_0_50px_rgba(0,0,0,0.5)] ${!isOpen ? 'cursor-pointer hover:bg-white/5 transition-colors' : ''}`}
        style={{
          background: 'linear-gradient(180deg, #06140d 0%, #030a07 100%)',
        }}
      >
        {/* Sidebar Header */}
        <div className={`p-6 flex items-center ${isOpen ? 'justify-between' : 'justify-center'}`}>
          <AnimatePresence mode="wait">
            {isOpen ? (
              <motion.div 
                key="logo-full"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="flex items-center space-x-3"
              >
                <motion.div 
                  whileHover={{ rotate: 360 }}
                  transition={{ duration: 0.5 }}
                  className="w-10 h-10 bg-gradient-to-br from-green-400 to-green-600 rounded-xl flex items-center justify-center shadow-[0_0_20px_rgba(34,197,94,0.5)]"
                >
                  <TrendingUp className="text-white" size={24} />
                </motion.div>
                <span className="text-white font-black text-xl tracking-tighter">GROWW<span className="text-green-500">.</span></span>
              </motion.div>
            ) : (
              <motion.div 
                key="logo-small"
                initial={{ opacity: 0, scale: 0.5 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.5 }}
                className="w-10 h-10 bg-gradient-to-br from-green-400 to-green-600 rounded-xl flex items-center justify-center mx-auto shadow-[0_0_20px_rgba(34,197,94,0.5)]"
                onClick={toggleSidebar}
                style={{ cursor: 'pointer' }}
              >
                <TrendingUp className="text-white" size={20} />
              </motion.div>
            )}
          </AnimatePresence>
          {isOpen && (
            <button 
              onClick={toggleSidebar}
              className="p-2 text-green-500/50 hover:text-white hover:bg-white/10 rounded-lg transition-all"
            >
              <X size={20} />
            </button>
          )}
        </div>

        {/* Navigation Items */}
        <div className="flex-1 px-4 py-2 overflow-y-auto custom-scrollbar-dark">
          <nav className="space-y-2">
            <NavItem 
              icon={<Home size={22} />} 
              label="Home" 
              isOpen={isOpen} 
              active={true}
            />
            
            <div className={`pt-8 pb-3 transition-opacity duration-300 ${isOpen ? 'opacity-100' : 'opacity-0'}`}>
              <p className="text-[10px] font-black text-green-500/40 uppercase tracking-[3px] px-3">
                Mutual Fund Schemes
              </p>
            </div>

            <div className="space-y-2">
              {SUPPORTED_FUNDS.map((fund) => (
                <div key={fund.id} className="relative group">
                  <motion.button
                    whileHover={{ x: 5 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={(e) => {
                      e.stopPropagation();
                      const rect = e.currentTarget.getBoundingClientRect();
                      setActiveFundPos(rect.top);
                      setSelectedFund(selectedFund?.id === fund.id ? null : fund);
                    }}
                    className={`w-full flex items-center p-3.5 rounded-2xl transition-all duration-300 group
                      ${selectedFund?.id === fund.id 
                        ? 'bg-green-500 text-white shadow-[0_10px_25px_rgba(34,197,94,0.3)] scale-[1.02]' 
                        : 'text-green-100/60 hover:bg-white/5 hover:text-white'
                      }`}
                  >
                    <div className="min-w-[24px] flex justify-center">
                      <Briefcase size={20} className={selectedFund?.id === fund.id ? 'text-white' : 'text-green-500/50 group-hover:text-green-400'} />
                    </div>
                    {isOpen && (
                      <>
                        <span className="ml-3 text-sm font-semibold truncate flex-1 text-left">
                          {fund.name.split('—')[0]}
                        </span>
                        <ChevronRight 
                          size={16} 
                          className={`transition-transform duration-500 ${selectedFund?.id === fund.id ? 'rotate-90 text-white' : 'text-green-500/30'}`}
                        />
                      </>
                    )}
                  </motion.button>

                  {/* Submenu moved out of this container to avoid clipping */}
                </div>
              ))}
            </div>
          </nav>
        </div>

        {/* Sidebar Footer */}
        <div className="p-4 border-t border-green-900/30 space-y-1">
          <NavItem icon={<Settings size={22} />} label="Settings" isOpen={isOpen} />
          <NavItem icon={<HelpCircle size={22} />} label="Help" isOpen={isOpen} />
        </div>

        {/* Global Submenu Portal-like rendering */}
        <AnimatePresence>
          {selectedFund && (
            <motion.div
              ref={submenuRef}
              variants={submenuVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              style={{ 
                top: activeFundPos + 450 > (typeof window !== 'undefined' ? window.innerHeight : 1000) 
                  ? 'auto' 
                  : activeFundPos,
                bottom: activeFundPos + 450 > (typeof window !== 'undefined' ? window.innerHeight : 1000) 
                  ? '20px' 
                  : 'auto'
              }}
              className={`fixed ${isOpen ? 'left-[335px]' : 'left-[95px]'} w-[280px] z-[100] perspective-1000 pointer-events-auto`}
            >
              <div className="bg-[#0f2a1e]/95 backdrop-blur-2xl border border-green-500/30 rounded-2xl p-5 shadow-[0_20px_50px_rgba(0,0,0,0.5)] relative group overflow-hidden">
                {/* Decorative Background Glow */}
                <div className="absolute -top-20 -right-20 w-40 h-40 bg-green-500/10 blur-[50px] rounded-full pointer-events-none" />
                
                <h3 className="text-white font-bold text-base mb-4 flex items-center">
                  <span className="w-1.5 h-6 bg-green-500 rounded-full mr-3" />
                  {selectedFund.name.split('—')[0]}
                </h3>
                
                <div className="grid grid-cols-1 gap-1">
                  <SubmenuItem label="Expense Ratio" icon={<Zap size={14} />} />
                  <SubmenuItem label="NAV" icon={<TrendingUp size={14} />} />
                  <SubmenuItem label="Exit Load" icon={<PieChart size={14} />} />
                  <SubmenuItem label="Lock-in" icon={<Lock size={14} />} />
                  <SubmenuItem label="Min SIP" icon={<Wallet size={14} />} />
                  <SubmenuItem label="AUM" icon={<Briefcase size={14} />} />
                  <SubmenuItem label="Riskometer" icon={<Shield size={14} />} />
                </div>
                
                <div className="absolute inset-0 border-t border-l border-white/5 pointer-events-none rounded-2xl" />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.aside>

      <style jsx global>{`
        .custom-scrollbar-dark::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scrollbar-dark::-webkit-scrollbar-track {
          background: rgba(0, 0, 0, 0.1);
        }
        .custom-scrollbar-dark::-webkit-scrollbar-thumb {
          background: rgba(34, 197, 94, 0.2);
          border-radius: 10px;
        }
        .custom-scrollbar-dark::-webkit-scrollbar-thumb:hover {
          background: rgba(34, 197, 94, 0.4);
        }
      `}</style>
    </>
  );
}

function NavItem({ icon, label, isOpen, active = false }: { icon: React.ReactNode, label: string, isOpen: boolean, active?: boolean }) {
  return (
    <button
      className={`w-full flex items-center p-3 rounded-xl transition-all duration-200 group relative
        ${active 
          ? 'bg-green-500 text-white shadow-[0_0_20px_rgba(34,197,94,0.2)]' 
          : 'text-green-100/70 hover:bg-green-800/20 hover:text-white'
        }`}
    >
      <div className="min-w-[24px] flex justify-center">
        {icon}
      </div>
      <AnimatePresence mode="wait">
        {isOpen && (
          <motion.span
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -10 }}
            className="ml-3 text-sm font-medium whitespace-nowrap"
          >
            {label}
          </motion.span>
        )}
      </AnimatePresence>
      {!isOpen && (
        <div className="absolute left-16 bg-green-900 text-white px-3 py-1.5 rounded-lg text-xs opacity-0 group-hover:opacity-100 pointer-events-none transition-all transform translate-x-[-10px] group-hover:translate-x-0 shadow-xl border border-green-700/50 z-[100] whitespace-nowrap">
          {label}
        </div>
      )}
    </button>
  );
}

function SubmenuItem({ label, icon }: { label: string, icon: React.ReactNode }) {
  return (
    <div className="group/item flex items-center p-2 rounded-lg hover:bg-white/5 transition-colors">
      <div className="flex items-center space-x-3">
        <div className="text-green-500/70 group-hover/item:text-green-400 transition-colors">
          {icon}
        </div>
        <span className="text-[11px] text-green-100/60 font-medium">{label}</span>
      </div>
    </div>
  );
}
