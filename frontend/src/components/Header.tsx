import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { LayoutDashboard, Cpu, FileText, Code2, Activity, Plus, Settings, Sun, Moon } from 'lucide-react';

interface HeaderProps {
  theme: string;
  toggleTheme: () => void;
}

const navLinks = [
  { name: 'Dashboard',     path: '/dashboard',          icon: LayoutDashboard },
  { name: 'Reverse Eng.',  path: '/reverse-engineering', icon: Cpu },
  { name: 'Business Logic',path: '/business-logic',     icon: FileText },
  { name: 'Code Gen',      path: '/code-generation',    icon: Code2 },
  { name: 'Mission Ctrl',  path: '/mission-control',    icon: Activity },
];

const statusMessages = [
  'AI Engine: Connected',
  'Ollama: Running locally',
  'Pipeline: Ready',
  'All systems nominal',
];

const Header = ({ theme, toggleTheme }: HeaderProps) => {
  const location  = useLocation();
  const navigate  = useNavigate();
  const [scrolled,   setScrolled]   = useState(false);
  const [statusIdx,  setStatusIdx]  = useState(0);

  // Detect scroll on main content panel
  useEffect(() => {
    const el = document.querySelector('main');
    if (!el) return;
    const onScroll = () => setScrolled(el.scrollTop > 10);
    el.addEventListener('scroll', onScroll);
    return () => el.removeEventListener('scroll', onScroll);
  }, []);

  // Cycle status messages
  useEffect(() => {
    const t = setInterval(() => setStatusIdx(i => (i + 1) % statusMessages.length), 3000);
    return () => clearInterval(t);
  }, []);

  return (
    <header
      className="h-14 px-5 flex items-center justify-between sticky top-0 z-50 transition-all duration-300"
      style={{
        background: scrolled
          ? 'rgba(var(--corporate-bg-rgb, 246, 240, 230), 0.97)'
          : 'rgba(var(--corporate-bg-rgb, 246, 240, 230), 0.80)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        borderBottom: '1px solid var(--corporate-border)',
        boxShadow: scrolled ? '0 4px 24px rgba(61,45,32,0.10)' : 'none',
      }}
    >
      {/* LEFT: Logo + Nav */}
      <div className="flex items-center gap-6">
        {/* Logo */}
        <Link to="/dashboard" className="flex items-center gap-2 group">
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center font-black text-white text-xs transition-transform duration-200 group-hover:scale-110"
            style={{ background: 'linear-gradient(135deg, var(--corporate-accent), var(--corporate-success))' }}
          >
            M
          </div>
          <span className="font-black text-sm tracking-tight" style={{ color: 'var(--corporate-text)' }}>
            Modernizer<span style={{ color: 'var(--corporate-accent)' }}>AI</span>
          </span>
        </Link>

        {/* Nav Links */}
        <nav className="hidden md:flex items-center gap-0.5">
          {navLinks.map(link => {
            const isActive = location.pathname === link.path;
            return (
              <Link
                key={link.path}
                to={link.path}
                className="relative flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors duration-150"
                style={{ color: isActive ? 'var(--corporate-accent)' : 'var(--corporate-muted)' }}
                onMouseEnter={e => { if (!isActive) (e.currentTarget as HTMLElement).style.color = 'var(--corporate-text)'; }}
                onMouseLeave={e => { if (!isActive) (e.currentTarget as HTMLElement).style.color = 'var(--corporate-muted)'; }}
              >
                <link.icon size={13} />
                {link.name}
                {/* Animated underline */}
                {isActive && (
                  <motion.div
                    layoutId="headerUnderline"
                    className="absolute bottom-0 left-2 right-2 rounded-full"
                    style={{ height: 2, background: 'linear-gradient(90deg, var(--corporate-accent), var(--corporate-success))' }}
                    transition={{ type: 'spring', stiffness: 400, damping: 32 }}
                  />
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* RIGHT: Actions */}
      <div className="flex items-center gap-2.5">
        {/* Live status ticker */}
        <div
          className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full"
          style={{
            background: 'var(--corporate-accent-soft)',
            border: '1px solid color-mix(in srgb, var(--corporate-success) 30%, transparent)',
          }}
        >
          <span className="relative flex h-1.5 w-1.5">
            <span
              className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
              style={{ background: 'var(--corporate-success)' }}
            />
            <span
              className="relative inline-flex h-1.5 w-1.5 rounded-full"
              style={{ background: 'var(--corporate-success)' }}
            />
          </span>
          <motion.span
            key={statusIdx}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.25 }}
            className="text-[10px] font-bold uppercase tracking-wider"
            style={{ color: 'var(--corporate-success)' }}
          >
            {statusMessages[statusIdx]}
          </motion.span>
        </div>

        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          className="w-8 h-8 rounded-lg flex items-center justify-center transition-all duration-150"
          style={{ color: 'var(--corporate-muted)', border: '1px solid var(--corporate-border)' }}
          onMouseEnter={e => {
            (e.currentTarget as HTMLElement).style.borderColor = 'var(--corporate-accent)';
            (e.currentTarget as HTMLElement).style.color = 'var(--corporate-accent)';
          }}
          onMouseLeave={e => {
            (e.currentTarget as HTMLElement).style.borderColor = 'var(--corporate-border)';
            (e.currentTarget as HTMLElement).style.color = 'var(--corporate-muted)';
          }}
        >
          {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
        </button>

        {/* Configure AI */}
        <button
          onClick={() => navigate('/settings')}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150"
          style={{
            color: 'var(--corporate-muted)',
            border: '1px solid var(--corporate-border)',
          }}
          onMouseEnter={e => {
            (e.currentTarget as HTMLElement).style.color = 'var(--corporate-text)';
            (e.currentTarget as HTMLElement).style.borderColor = 'var(--corporate-border-strong)';
          }}
          onMouseLeave={e => {
            (e.currentTarget as HTMLElement).style.color = 'var(--corporate-muted)';
            (e.currentTarget as HTMLElement).style.borderColor = 'var(--corporate-border)';
          }}
        >
          <Settings size={12} /> Configure AI
        </button>

        {/* New Project CTA */}
        <motion.button
          whileHover={{ scale: 1.04, translateY: -1 }}
          whileTap={{ scale: 0.96 }}
          onClick={() => navigate('/initial-setup')}
          className="btn-glow flex items-center gap-1.5 text-xs"
          style={{ padding: '0.45rem 0.9rem', borderRadius: 8 }}
        >
          <Plus size={13} /> New Project
        </motion.button>
      </div>
    </header>
  );
};

export default Header;

