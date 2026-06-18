import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  FolderOpen,
  Cpu,
  FileText,
  MessageSquare,
  Code2,
  Activity,
  Settings,
  Database,
  Menu,
  Moon,
  Sun,
  BrainCircuit // <--- Added this icon for System Discovery
} from 'lucide-react';

interface SidebarProps {
  isOpen: boolean;
  toggleSidebar: () => void;
  theme: string;
  toggleTheme: () => void;
  openConfig: () => void;
}

const menuGroups = [
  {
    group: 'Core',
    items: [
      { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
      { name: 'Projects', path: '/projects', icon: Database },
    ],
  },
  {
    group: 'Reverse Engineering',
    items: [
      { name: 'Source Files', path: '/source-files', icon: FolderOpen },
      // --- ADDED SYSTEM DISCOVERY HERE ---
      { name: 'System Discovery', path: '/discovery', icon: BrainCircuit }, 
      { name: 'Analysis', path: '/reverse-engineering', icon: Cpu },
      { name: 'Business Logic', path: '/business-logic', icon: FileText },
    ],
  },
  {
    group: "Modernization",
    items: [
      { name: 'Code Gen', path: '/code-generation', icon: Code2 },
      { name: 'Modernizer Chat', path: '/chat', icon: MessageSquare },
    ]
  },
  {
    group: 'System',
    items: [
      { name: 'Mission Control', path: '/mission-control', icon: Activity },
      { name: 'Prompt Studio', path: '/prompt-studio', icon: Settings },
      { name: 'Settings', path: '/settings', icon: Settings },
    ],
  },
];

const Sidebar = ({
  isOpen,
  toggleSidebar,
  theme,
  toggleTheme,
  openConfig,
}: SidebarProps) => {
  const location = useLocation();

  return (
    <aside
      className={`h-screen bg-slate-950 border-r border-slate-800 flex flex-col transition-all duration-300 ease-in-out ${
        isOpen ? 'w-72' : 'w-20'
      }`}
    >
      {/* TOP BAR */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <button
          onClick={toggleSidebar}
          className="p-2 rounded-lg text-slate-400 hover:bg-slate-900 hover:text-white transition-all"
        >
          <Menu size={20} />
        </button>

        {isOpen && (
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg text-slate-400 hover:bg-slate-900 hover:text-white transition-all"
          >
            {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
          </button>
        )}
      </div >

      {/* LOGO SECTION */}
      <div className="p-6 mb-2">
        <div className="flex items-center gap-3">
          <div className="min-w-[40px] h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-500/20">
            <span className="text-xl font-black">M</span>
          </div>
          {isOpen && (
            <div className="overflow-hidden transition-all duration-300">
              <span className="block text-lg font-bold text-white whitespace-nowrap">
                Modernizer<span className="text-indigo-500">AI</span>
              </span>
              <p className="text-[10px] text-slate-500 uppercase tracking-widest font-semibold">
                Legacy Command Center
              </p>
            </div>
          )}
        </div>
      </div>

      {/* NAVIGATION MENU */}
      <nav className="flex-1 px-3 space-y-6 overflow-y-auto scrollbar-hide">
        {menuGroups.map((group, idx) => (
          <div key={idx} className="space-y-1">
            {isOpen && (
              <p className="px-4 mb-2 text-[11px] font-bold text-slate-500 uppercase tracking-widest">
                {group.group}
              </p>
            )}

            {group.items.map(item => {
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`
                    relative flex items-center gap-3 px-3 py-3 rounded-xl transition-all duration-200 group mb-1
                    ${isActive 
                      ? 'bg-indigo-600/10 text-indigo-400' 
                      : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'}
                  `}
                >
                  {isActive && (
                    <div className="absolute left-0 w-1 h-6 bg-indigo-500 rounded-r-full" />
                  )}
                  <item.icon 
                    size={20} 
                    className={`${isActive ? 'text-indigo-400' : 'text-slate-500 group-hover:text-slate-300'} transition-colors`} 
                  />
                  {isOpen && (
                    <span className={`text-sm font-medium transition-all ${isActive ? 'text-indigo-400' : 'text-slate-400 group-hover:text-slate-200'}`}>
                      {item.name}
                    </span>
                  )}
                  {!isOpen && (
                    <div className="absolute left-full ml-4 px-2 py-1 bg-slate-800 text-white text-xs rounded opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-50">
                      {item.name}
                    </div>
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* FOOTER */}
      <div className="p-4 border-t border-slate-800 bg-slate-950/50">
        <button
          onClick={openConfig}
          className={`
            w-full flex items-center gap-3 px-3 py-3 rounded-xl border transition-all
            ${isOpen 
              ? 'border-slate-800 text-slate-400 hover:bg-slate-900 hover:text-white' 
              : 'border-slate-800 text-slate-400 hover:bg-slate-900 hover:text-white justify-center'}
          `}
        >
          <Settings size={20} />
          {isOpen && <span className="text-sm font-medium">Configure AI</span>}
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
