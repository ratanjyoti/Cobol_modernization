import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import HITLModal from '../components/HITLModal';
import TopNav from '../components/TopNav';

const MainLayout = () => {
  const [theme, setTheme] = useState(
    localStorage.getItem('theme') || 'light'
  );

  const [hitlOpen, setHitlOpen] = useState(false);
  const [hitlData, setHitlData] = useState({
    step: '',
    message: '',
    reason: '',
  });

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    localStorage.setItem('theme', theme);
  }, [theme]);

  useEffect(() => {
    (window as any).triggerHITL = (
      step: string,
      message: string,
      reason: string
    ) => {
      setHitlData({ step, message, reason });
      setHitlOpen(true);
    };

    return () => {
      window.triggerHITL = undefined;
    };
  }, []);

  return (
    <div className="min-h-screen flex flex-col" style={{ background: 'var(--corporate-bg)' }}>
      <TopNav
        theme={theme}
        toggleTheme={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
      />

      <main className="min-w-0 flex-1" style={{ background: 'var(--corporate-bg)' }}>
        <div className="app-content-shell w-full min-w-0">
          <Outlet />
        </div>
      </main>

      <HITLModal
        isOpen={hitlOpen}
        onDeny={() => setHitlOpen(false)}
        onApprove={() => setHitlOpen(false)}
        config={hitlData}
      />
    </div>
  );
};

export default MainLayout;





