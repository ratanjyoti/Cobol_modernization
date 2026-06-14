import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Cpu, FileText, Code2, Activity, Plus } from 'lucide-react';

const navLinks = [
  { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { name: 'Reverse Eng.', path: '/reverse-engineering', icon: Cpu },
  { name: 'Business Logic', path: '/business-logic', icon: FileText },
  { name: 'Code Gen', path: '/code-generation', icon: Code2 },
  { name: 'Mission Control', path: '/mission-control', icon: Activity },
];

const Header = () => {
  const location = useLocation();

  return (
    <header className="h-16 bg-slate-900/80 backdrop-blur-md border-b border-slate-800 px-6 flex items-center justify-between sticky top-0 z-50">
      <div className="flex items-center gap-10">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white font-bold shadow-lg shadow-indigo-500/30">M</div>
          <span className="font-bold text-white text-lg tracking-tight">Modernizer<span className="text-indigo-500">AI</span></span>
        </div>

        <nav className="hidden md:flex items-center gap-1">
          {navLinks.map((link) => (
            <Link 
              key={link.path} 
              to={link.path}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-all ${
                location.pathname === link.path 
                ? 'text-indigo-400 bg-indigo-500/10' 
                : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800'
              }`}
            >
              <link.icon size={16} /> {link.name}
            </Link>
          ))}
        </nav>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 bg-slate-800 px-3 py-1 rounded-full border border-slate-700">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span className="text-[11px] font-bold text-slate-300 uppercase tracking-tight">API Connected</span>
        </div>
        <button className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-bold flex items-center gap-2 hover:bg-indigo-500 transition-all">
          <Plus size={16} /> New Project
        </button>
      </div>
    </header>
  );
};

export default Header;
