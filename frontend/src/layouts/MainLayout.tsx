import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Header from '../components/Header';
import ConfigModal from '../components/ConfigModal';
import HITLModal from '../components/HITLModal';
import toast from 'react-hot-toast';

const MainLayout = () => {
  const [showConfig, setShowConfig] = useState(false);
  
  // HITL State
  const [hitlOpen, setHitlOpen] = useState(false);
  const [hitlData, setHitlData] = useState({ tabName: '', message: '', reason: '' });

  // Global function to trigger HITL from any child page
  const triggerHITL = (name: string, msg: string, reason: string) => {
    setHitlData({ tabName: name, message: msg, reason: reason });
    setHitlOpen(true);
  };

  // We attach this to the window object so any page can call it without complex props
  React.useEffect(() => {
    (window as any).triggerHITL = triggerHITL;
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50">
      <Header />
      <main className="p-8 max-w-7xl mx-auto">
        <Outlet />
      </main>
      
      <ConfigModal isOpen={showConfig} onClose={() => setShowConfig(false)} />

      {/* HITL Modal */}
      <HITLModal 
        isOpen={hitlOpen} 
        onDeny={() => setHitlOpen(false)}
        onApprove={() => {
          setHitlOpen(false);
          toast.success("Approved! Pipeline resuming...");
        }}
        config={hitlData}
      />
    </div>
  );
};

export default MainLayout;
