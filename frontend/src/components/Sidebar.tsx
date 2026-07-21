import { Link, useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard, FolderOpen, Cpu, FileText,
  MessageSquare, Code2, Activity, Settings,
  Database, Menu, Moon, Sun, BrainCircuit, Zap, Workflow, ShieldCheck,
} from 'lucide-react';
import Tooltip from './Tooltip';

interface SidebarProps {
  isOpen: boolean;
  toggleSidebar: () => void;
  theme: string;
  toggleTheme: () => void;
}

const menuGroups = [
  {
    group: 'Core',
    items: [
      { name: 'Dashboard',      path: '/dashboard',          icon: LayoutDashboard, desc: 'View project health, progress, and next modernization actions.' },
      { name: 'Initial Setup', path: '/initial-setup',      icon: Settings,       desc: 'Configure AI models, project runs, and regional settings.' }, // ADD THIS
      { name: 'Projects',       path: '/projects',           icon: Database,        desc: 'Create a new migration run or resume an existing project.' },
    ],
  },
  {
    group: 'Reverse Engineering',
    items: [
      { name: 'Source Files',     path: '/source-files',       icon: FolderOpen,   desc: 'Upload, inspect, and manage legacy source files for analysis.' },
      { name: 'System Discovery', path: '/discovery',          icon: BrainCircuit, desc: 'Analyze calls, copybooks, SQL tables, and dependency relationships.' },
      { name: 'Analysis',         path: '/reverse-engineering',icon: Cpu,          desc: 'Review technical analysis, structure, and modernization insights.' },
      { name: 'Business Logic',   path: '/business-logic',     icon: FileText,     desc: 'Translate legacy code behavior into plain-English business rules.' },
    ],
  },
  {
    group: 'Modernization',
    items: [
      { name: 'Code Gen',        path: '/code-generation', icon: Code2,         desc: 'Generate modern application code from the analyzed legacy system.' },
      { name: 'AI Chat',         path: '/chat',            icon: MessageSquare, desc: 'Ask guided questions about the migration and generated outputs.' },
      { name: 'Modernization Plan', path: '/modernization-plan', icon: Workflow, desc: 'View the staged blueprint and execution roadmap.' },
    ],
  },
  {
    group: 'System',
    items: [
      { name: 'Mission Control', path: '/mission-control', icon: Activity, desc: 'Monitor pipeline execution, validation loops, and run status.' },
      { name: 'Prompt Studio',   path: '/prompt-studio',   icon: Zap,      desc: 'Edit and tune prompts used by modernization agents.' },
      { name: 'AI Configuration', path: '/settings',        icon: Settings, desc: 'Change provider, API key, endpoint, and model settings.' },
      { name: 'System Admin',     path: '/admin',           icon: ShieldCheck, desc: 'Manage global administration and platform settings.' },
    ],
  },
];

const Sidebar = ({ isOpen, toggleSidebar, theme, toggleTheme }: SidebarProps) => {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <motion.aside
      animate={{ width: isOpen ? 256 : 68 }}
      transition={{ duration: 0.28, ease: [0.4, 0, 0.2, 1] }}
      className="h-screen flex flex-col overflow-hidden shrink-0 relative"
      style={{
        background: 'linear-gradient(180deg, var(--corporate-bg-soft) 0%, var(--corporate-bg) 100%)',
        borderRight: '1px solid var(--corporate-border)',
      }}
    >
      {/* TOP BAR */}
      <div
        className="flex items-center justify-between px-3 py-3 shrink-0"
        style={{ borderBottom: '1px solid var(--corporate-border)' }}
      >
        <button
          onClick={toggleSidebar}
          aria-label={isOpen ? 'Collapse sidebar' : 'Open sidebar'}
          title={isOpen ? 'Collapse sidebar' : 'Open sidebar'}
          className="p-2 rounded-lg transition-all duration-150"
          style={{ color: 'var(--corporate-muted)' }}
          onMouseEnter={e => {
            (e.currentTarget as HTMLElement).style.background = 'rgba(31,31,29,0.055)';
            (e.currentTarget as HTMLElement).style.color = '#1f1f1d';
          }}
          onMouseLeave={e => {
            (e.currentTarget as HTMLElement).style.background = 'transparent';
            (e.currentTarget as HTMLElement).style.color = 'var(--corporate-muted)';
          }}
        >
          <Menu size={18} />
        </button>

        <AnimatePresence>
          {isOpen && (
            <motion.button
              initial={{ opacity: 0, scale: 0.7 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.7 }}
              transition={{ duration: 0.15 }}
              onClick={toggleTheme}
              aria-label={'Toggle theme'}
              title={'Toggle theme'}
              className="p-2 rounded-lg transition-all duration-150"
              style={{ color: 'var(--corporate-muted)' }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLElement).style.background = 'rgba(31,31,29,0.055)';
                (e.currentTarget as HTMLElement).style.color = '#1f1f1d';
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLElement).style.background = 'transparent';
                (e.currentTarget as HTMLElement).style.color = 'var(--corporate-muted)';
              }}
            >
              {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
            </motion.button>
          )}
        </AnimatePresence>
      </div>

      {/* LOGO */}
      <div className="px-3 py-4 shrink-0">
        <div className="flex items-center gap-3 overflow-hidden">
          {/* Spinning gradient logo mark */}
          <div className="relative shrink-0" style={{ width: 34, height: 34 }}>
            <div
              className="absolute inset-0 rounded-xl"
              style={{
                background: '#1f1f1d',
                borderRadius: 10,
                animation: 'none',
              }}
            />
            <div
              className="absolute flex items-center justify-center font-black text-white text-sm"
              style={{
                inset: 2,
                borderRadius: 8,
                background: '#1f1f1d',
                color: '#ffffff',
              }}
            >
              M
            </div>
          </div>

          <AnimatePresence>
            {isOpen && (
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                transition={{ duration: 0.18 }}
                className="overflow-hidden"
              >
                <div className="font-black text-[0.9375rem] leading-none whitespace-nowrap" style={{ color: 'var(--corporate-text)' }}>
                  Modernizer<span style={{ color: 'var(--corporate-accent)' }}>AI</span>
                </div>
                <div
                  className="mt-0.5 whitespace-nowrap"
                  style={{ fontSize: '0.6rem', fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--corporate-faint)' }}
                >
                  Legacy Command Center
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* NAV */}
      <nav className="flex-1 px-2 overflow-y-auto py-1 space-y-4" style={{ scrollbarWidth: 'none' }}>
        {menuGroups.map((group, gIdx) => (
          <div key={gIdx}>
            <AnimatePresence>
              {isOpen && (
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.15 }}
                  className="px-3 mb-1"
                  style={{ fontSize: '0.6rem', fontWeight: 800, letterSpacing: '0.16em', textTransform: 'uppercase', color: 'var(--corporate-faint)' }}
                >
                  {group.group}
                </motion.p>
              )}
            </AnimatePresence>

            <div className="space-y-0.5">
              {group.items.map(item => {
                const isActive = location.pathname === item.path;
                return (
                  <Tooltip key={item.path} title={item.name} text={item.desc} position="right" className="w-full">
                    <Link
                      to={item.path}
                      aria-label={`${item.name}: ${item.desc}`}
                      className="relative flex items-center gap-2.5 px-3 py-2.5 rounded-xl transition-all duration-150 w-full"
                      style={{
                        justifyContent: isOpen ? 'flex-start' : 'center',
                        background: isActive ? 'rgba(31,31,29,0.055)' : 'transparent',
                        color: isActive ? '#1f1f1d' : 'var(--corporate-muted)',
                      }}
                      onMouseEnter={e => {
                        if (!isActive) {
                          (e.currentTarget as HTMLElement).style.background = 'rgba(31,31,29,0.055)';
                          (e.currentTarget as HTMLElement).style.color = '#1f1f1d';
                        }
                      }}
                      onMouseLeave={e => {
                        if (!isActive) {
                          (e.currentTarget as HTMLElement).style.background = 'transparent';
                          (e.currentTarget as HTMLElement).style.color = 'var(--corporate-muted)';
                        }
                      }}
                    >
                      {/* Animated active left pill */}
                      {isActive && (
                        <motion.div
                          layoutId="sidebarActivePill"
                          className="absolute left-0 rounded-r-full"
                          style={{
                            width: 3,
                            height: 18,
                            background: 'var(--corporate-accent)',
                            boxShadow: 'none',
                          }}
                          transition={{ type: 'spring', stiffness: 400, damping: 32 }}
                        />
                      )}

                      <item.icon size={16} className="shrink-0" />

                      <AnimatePresence>
                        {isOpen && (
                          <motion.span
                            initial={{ opacity: 0, x: -8 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -8 }}
                            transition={{ duration: 0.14 }}
                            className="text-sm font-semibold whitespace-nowrap"
                          >
                            {item.name}
                          </motion.span>
                        )}
                      </AnimatePresence>
                    </Link>
                  </Tooltip>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* FOOTER */}
      <div className="p-2 shrink-0" style={{ borderTop: '1px solid var(--corporate-border)' }}>
        <button
          onClick={() => navigate('/settings')}
          className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl transition-all duration-150"
          style={{
            justifyContent: isOpen ? 'flex-start' : 'center',
            color: 'var(--corporate-muted)',
          }}
          onMouseEnter={e => {
            (e.currentTarget as HTMLElement).style.background = 'rgba(31,31,29,0.055)';
            (e.currentTarget as HTMLElement).style.color = '#1f1f1d';
          }}
          onMouseLeave={e => {
            (e.currentTarget as HTMLElement).style.background = 'transparent';
            (e.currentTarget as HTMLElement).style.color = 'var(--corporate-muted)';
          }}
        >
          <Settings size={16} className="shrink-0" />
          <AnimatePresence>
            {isOpen && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.14 }}
                className="text-sm font-semibold whitespace-nowrap"
              >
                AI Configuration
              </motion.span>
            )}
          </AnimatePresence>
        </button>
      </div>
    </motion.aside>
  );
};

export default Sidebar;







