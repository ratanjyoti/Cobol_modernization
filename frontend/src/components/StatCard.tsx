// Note the 'type' keyword here. This is the fix!
import type { LucideIcon } from 'lucide-react';

interface StatCardProps {
  label: string;
  value: string;
  icon: LucideIcon;
  color: string;
}

const StatCard = ({ label, value, icon: Icon, color }: StatCardProps) => {
  return (
    <div className="glass-card p-6 rounded-xl flex items-center gap-4 hover:-translate-y-1">
      <div className={`p-3 rounded-lg ${color} shadow-lg`}>
        <Icon size={24} className="text-white" />
      </div>
      <div className="flex flex-col">
        <p className="text-slate-500 text-xs uppercase font-bold tracking-wider">{label}</p>
        <h3 className="text-2xl font-black text-slate-950">{value}</h3>
      </div>
    </div>
  );
};

export default StatCard;
