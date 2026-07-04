import { PROJECT_TABS } from '../../config/tabsConfig';

const Tabs = () => {
  return (
    <div className="flex space-x-4">
      {PROJECT_TABS.map((tab) => (
        <div 
          key={tab.id} 
          className="relative group cursor-pointer p-2 border-b-2"
        >
          <span>{tab.label}</span>
          
          {/* The Hover Tooltip */}
          <div className="absolute hidden group-hover:block bg-gray-800 text-white text-xs rounded p-2 w-48 bottom-full mb-2 left-1/2 -translate-x-1/2 z-50">
            {tab.description}
            {/* Tooltip Arrow */}
            <div className="absolute w-2 h-2 bg-gray-800 rotate-45 -bottom-1 left-1/2 -translate-x-1/2"></div>
          </div>
        </div>
      ))}
    </div>
  );
};
