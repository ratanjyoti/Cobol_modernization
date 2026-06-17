// import { Link, useLocation } from 'react-router-dom';
// import { 
//   LayoutDashboard, FolderOpen, Cpu, Share2, 
//   FileText, GitBranch, MessageSquare, Map, 
//   Code2, Activity, Settings, Database 
// } from 'lucide-react';

// const menuGroups = [
//   {
//     group: "Core",
//     items: [
//       { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
//       { name: 'Projects', path: '/projects', icon: Database },
//     ]
//   },
//   {
//     group: "Reverse Engineering",
//     items: [
//       { name: 'Source Files', path: '/source-files', icon: FolderOpen },
//       { name: 'Analysis', path: '/reverse-engineering', icon: Cpu },
//       { name: 'Dependency Graph', path: '/dependency-graph', icon: Share2 },
//       { name: 'Business Logic', path: '/business-logic', icon: FileText },
//       { name: 'DDD Discovery', path: '/ddd-discovery', icon: GitBranch },
//     ]
//   },
//   {
//     group: "Modernization",
//     items: [
//       { name: 'Modern Plan', path: '/modernization-plan', icon: Map },
//       { name: 'Code Gen', path: '/code-generation', icon: Code2 },
//       { name: 'Modernizer Chat', path: '/chat', icon: MessageSquare },
//     ]
//   },
//   {
//     group: "System",
//     items: [
//       { name: 'Mission Control', path: '/mission-control', icon: Activity },
//       { name: 'Prompt Studio', path: '/prompt-studio', icon: Settings },
//       { name: 'Settings', path: '/settings', icon: Settings },
//     ]
//   }
// ];

// const Sidebar = () => {
//   const location = useLocation();

//   return (
//     <div className="w-72 h-screen bg-panel border-r border-panel flex flex-col transition-colors backdrop-blur-xl">
//       <div className="p-6">
//         <div className="flex items-center gap-3 px-2">
//           <div className="w-10 h-10 bg-brand-500 rounded-lg flex items-center justify-center text-white shadow-lg shadow-brand-500/40">
//             <span className="text-xl font-black">M</span>
//           </div>
//           <div>
//             <span className="text-xl font-bold text-main tracking-tight">Modernizer<span className="text-brand-500">AI</span></span>
//             <p className="text-[10px] text-muted uppercase tracking-[0.16em] font-bold">Legacy command center</p>
//           </div>
//         </div>
//       </div>
      
//       <nav className="flex-1 px-4 space-y-7 overflow-y-auto">
//         {menuGroups.map((group, idx) => (
//           <div key={idx} className="space-y-2">
//             <p className="px-4 text-[10px] font-bold text-muted uppercase tracking-widest">{group.group}</p>
//             <div className="space-y-1">
//               {group.items.map((item) => (
//                 <Link 
//                   key={item.path} 
//                   to={item.path}
//                   className={`flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-200 group ${
//                     location.pathname === item.path 
//                     ? 'bg-brand-500 text-white shadow-lg shadow-brand-500/30' 
//                     : 'text-muted hover:bg-brand-50 hover:text-brand-600 dark:hover:bg-slate-800 dark:hover:text-white'
//                   }`}
//                 >
//                   <item.icon size={18} className={`${location.pathname === item.path ? 'text-white' : 'text-muted group-hover:text-brand-500'}`} />
//                   <span className="text-sm font-medium">{item.name}</span>
//                 </Link>
//               ))}
//             </div>
//           </div>
//         ))}
//       </nav>
      
//       <div className="p-6 border-t border-panel">
//         <div className="bg-panel-solid p-4 rounded-lg border border-panel">
//           <div className="flex items-center justify-between mb-3">
//             <div>
//               <p className="text-[10px] font-bold text-muted uppercase mb-1">Enterprise Tier</p>
//               <p className="text-xs text-main font-bold">Pipeline Capacity</p>
//             </div>
//             <span className="text-xs font-black text-brand-500">75%</span>
//           </div>
//           <div className="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
//             <div className="h-full bg-brand-500 w-3/4 shadow-[0_0_10px_rgba(59,130,246,0.5)]"></div>
//           </div>
//         </div>
//       </div>
//     </div>
//   );
// };

// export default Sidebar;


import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  FolderOpen,
  Cpu,
  Share2,
  FileText,
  GitBranch,
  MessageSquare,
  Map,
  Code2,
  Activity,
  Settings,
  Database,
  Menu,
  Moon,
  Sun
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
      {
        name: 'Dashboard',
        path: '/dashboard',
        icon: LayoutDashboard,
      },
      {
        name: 'Projects',
        path: '/projects',
        icon: Database,
      },
    ],
  },
  {
    group: 'Reverse Engineering',
    items: [
      {
        name: 'Source Files',
        path: '/source-files',
        icon: FolderOpen,
      },
      {
        name: 'Analysis',
        path: '/reverse-engineering',
        icon: Cpu,
      },
      {
        name: 'Dependency Graph',
        path: '/dependency-graph',
        icon: Share2,
      },
      {
        name: 'Business Logic',
        path: '/business-logic',
        icon: FileText,
      },
      {
        name: 'DDD Discovery',
        path: '/ddd-discovery',
        icon: GitBranch,
      },
    ],
  },
  {
    group: 'Modernization',
    items: [
      {
        name: 'Modern Plan',
        path: '/modernization-plan',
        icon: Map,
      },
      {
        name: 'Code Gen',
        path: '/code-generation',
        icon: Code2,
      },
      {
        name: 'Modernizer Chat',
        path: '/chat',
        icon: MessageSquare,
      },
    ],
  },
  {
    group: 'System',
    items: [
      {
        name: 'Mission Control',
        path: '/mission-control',
        icon: Activity,
      },
      {
        name: 'Prompt Studio',
        path: '/prompt-studio',
        icon: Settings,
      },
      {
        name: 'Settings',
        path: '/settings',
        icon: Settings,
      },
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
      className={`h-screen bg-panel border-r border-panel flex flex-col transition-all duration-300 ${
        isOpen ? 'w-72' : 'w-20'
      }`}
    >
      {/* TOP BAR */}

      <div className="p-4 border-b border-panel">
        <div className="flex items-center justify-between">
          <button
            onClick={toggleSidebar}
            className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <Menu size={18} />
          </button>

          {isOpen && (
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
            >
              {theme === 'dark' ? (
                <Sun size={18} />
              ) : (
                <Moon size={18} />
              )}
            </button>
          )}
        </div>
      </div>

      {/* LOGO */}

      <div className="p-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-brand-500 rounded-lg flex items-center justify-center text-white">
            M
          </div>

          {isOpen && (
            <div>
              <span className="text-xl font-bold text-main">
                Modernizer
                <span className="text-brand-500">
                  AI
                </span>
              </span>

              <p className="text-[10px] text-muted uppercase tracking-widest">
                Legacy command center
              </p>
            </div>
          )}
        </div>
      </div>

      {/* MENU */}

      <nav className="flex-1 px-3 overflow-y-auto">
        {menuGroups.map((group, idx) => (
          <div key={idx} className="mb-6">
            {isOpen && (
              <p className="px-3 mb-2 text-[10px] font-bold text-muted uppercase tracking-widest">
                {group.group}
              </p>
            )}

            {group.items.map(item => (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-3 py-3 rounded-lg transition-all mb-1 ${
                  location.pathname === item.path
                    ? 'bg-brand-500 text-white'
                    : 'text-muted hover:bg-brand-50 dark:hover:bg-slate-800'
                }`}
              >
                <item.icon size={18} />

                {isOpen && (
                  <span className="text-sm">
                    {item.name}
                  </span>
                )}
              </Link>
            ))}
          </div>
        ))}
      </nav>

      {/* FOOTER */}

      <div className="p-4 border-t border-panel space-y-2">
        <button
          onClick={openConfig}
          className="w-full px-3 py-2 rounded-lg border border-panel hover:bg-slate-100 dark:hover:bg-slate-800"
        >
          {isOpen ? 'Configure AI' : 'AI'}
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;