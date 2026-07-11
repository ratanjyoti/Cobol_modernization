import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import {
  BrainCircuit,
  ChevronDown,
  Code2,
  Database,
  FileText,
  FolderOpen,
  Lightbulb,
  Moon,
  Network,
  Rocket,
  ServerCog,
  ShieldCheck,
  Sun,
  Workflow,
  Zap,
} from 'lucide-react';

interface TopNavProps {
  theme: string;
  toggleTheme: () => void;
}

const MEGA_NAV = [
  {
    id: 'core',
    label: 'Core',
    items: [
      { title: 'Dashboard', desc: 'Overview, workspace, and run controls', path: '/dashboard', icon: Database },
      { title: 'Projects', desc: 'Create, resume, and manage migration runs', path: '/projects', icon: FolderOpen },
    ],
  },
  {
    id: 'reverse',
    label: 'Reverse Engineering',
    items: [
      { title: 'Source Files', desc: 'Upload COBOL, JCL, copybooks, SQL, and folders', path: '/source-files', icon: FileText },
      { title: 'System Discovery', desc: 'Dependency graph, copybook links, and relationships', path: '/discovery', icon: Network },
      { title: 'Analysis', desc: 'Complexity, DDD discovery, and technical structure', path: '/reverse-engineering', icon: BrainCircuit },
      { title: 'Business Logic', desc: 'Extract, review, and approve business rules', path: '/business-logic', icon: Lightbulb },
    ],
  },
  {
    id: 'modernization',
    label: 'Modernization',
    items: [
      { title: 'Code Generation', desc: 'Generate modern services, DTOs, and APIs', path: '/code-generation', icon: Code2 },
      { title: 'AI Chat', desc: 'Ask questions about the migration and outputs', path: '/chat', icon: BrainCircuit },
      { title: 'Modernization Plan', desc: 'View staged blueprint and execution roadmap', path: '/modernization-plan', icon: Workflow },
    ],
  },
  {
    id: 'system',
    label: 'System',
    items: [
      { title: 'Mission Control', desc: 'Monitor execution and validation loops', path: '/mission-control', icon: Rocket },
      { title: 'Prompt Studio', desc: 'Tune prompts and modernization instructions', path: '/prompt-studio', icon: Zap },
      { title: 'AI Configuration', desc: 'Provider, model, endpoint, and API settings', path: '/settings', icon: ServerCog },
      { title: 'System Admin', desc: 'Global administration and settings workspace', path: '/admin', icon: ShieldCheck },
    ],
  },
];

const TopNav = ({ theme, toggleTheme }: TopNavProps) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [activeMegaMenu, setActiveMegaMenu] = useState<string | null>(null);

  const activeGroup = MEGA_NAV.find((group) => group.items.some((item) => item.path === location.pathname))?.id;

  return (
    <nav className="rocket-landing-nav app-top-nav" onMouseLeave={() => setActiveMegaMenu(null)}>
      <button onClick={() => navigate('/dashboard')} className="rocket-nav-logo" aria-label="ModernizerAI home">
        <span className="rocket-logo-mark">M</span>
        <strong>Modernizer<span>AI</span></strong>
      </button>

      <div className="rocket-nav-links">
        {MEGA_NAV.map((group) => (
          <button
            key={group.id}
            type="button"
            onClick={() => setActiveMegaMenu((current) => current === group.id ? null : group.id)}
            onMouseEnter={() => setActiveMegaMenu(group.id)}
            className={activeMegaMenu === group.id || activeGroup === group.id ? 'rocket-nav-link-active' : ''}
          >
            {group.label}
            <ChevronDown size={14} className={activeMegaMenu === group.id ? 'rotate-180' : ''} />
          </button>
        ))}
      </div>

      <div className="rocket-nav-actions">
        <button type="button" onClick={toggleTheme} className="rocket-theme-toggle" aria-label="Toggle theme">
          {theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
        </button>
        <button type="button" onClick={() => navigate('/settings')}>Sign in</button>
        <motion.button whileTap={{ scale: 0.96 }} onClick={() => navigate('/dashboard?new=true')} className="rocket-nav-primary">
          Get started
        </motion.button>
      </div>

      <AnimatePresence>
        {activeMegaMenu && (
          <motion.div
            className="rocket-mega-menu"
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.18 }}
          >
            <div className="rocket-mega-grid">
              {MEGA_NAV.find((group) => group.id === activeMegaMenu)?.items.map((item) => (
                <button
                  key={item.path}
                  type="button"
                  onClick={() => {
                    setActiveMegaMenu(null);
                    navigate(item.path);
                  }}
                  className={location.pathname === item.path ? 'rocket-mega-item rocket-mega-item-active' : 'rocket-mega-item'}
                >
                  <span className="rocket-mega-icon"><item.icon size={18} /></span>
                  <span>
                    <strong>{item.title}</strong>
                    <small>{item.desc}</small>
                  </span>
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
};

export default TopNav;
