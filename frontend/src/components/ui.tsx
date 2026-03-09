import React from 'react';
import { Eye, EyeOff, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';

export const Input: React.FC<React.InputHTMLAttributes<HTMLInputElement> & { label: string; description?: string }> = ({ label, description, className, ...props }) => (
  <div className={`flex flex-col gap-1.5 ${className || ''}`}>
    <label className="text-sm font-medium text-slate-700">{label}</label>
    {description && <p className="text-xs text-slate-500">{description}</p>}
    <input
      className="bg-slate-50/50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:bg-white focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all placeholder:text-slate-400 shadow-sm"
      {...props}
    />
  </div>
);

export const PasswordInput: React.FC<React.InputHTMLAttributes<HTMLInputElement> & { label: string; description?: string; status?: 'missing' | 'present' | 'verified' }> = ({ label, description, status, className, ...props }) => {
  const [show, setShow] = React.useState(false);
  return (
    <div className={`flex flex-col gap-1.5 ${className || ''}`}>
      <div className="flex justify-between items-center">
        <label className="text-sm font-medium text-slate-700">{label}</label>
        {status === 'verified' && <span className="text-xs font-medium text-emerald-600 flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5" /> 已验证</span>}
        {status === 'present' && <span className="text-xs font-medium text-amber-600 flex items-center gap-1"><AlertCircle className="w-3.5 h-3.5" /> 已存在</span>}
        {status === 'missing' && <span className="text-xs font-medium text-rose-500 flex items-center gap-1"><XCircle className="w-3.5 h-3.5" /> 未设置</span>}
      </div>
      {description && <p className="text-xs text-slate-500">{description}</p>}
      <div className="relative">
        <input
          type={show ? 'text' : 'password'}
          className="w-full bg-slate-50/50 border border-slate-200 rounded-xl pl-4 pr-11 py-2.5 text-sm text-slate-900 focus:outline-none focus:bg-white focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all placeholder:text-slate-400 shadow-sm font-mono"
          {...props}
        />
        <button
          type="button"
          onClick={() => setShow(!show)}
          className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
        >
          {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      </div>
    </div>
  );
};

export const Select: React.FC<React.SelectHTMLAttributes<HTMLSelectElement> & { label: string; description?: string; options: { value: string; label: string }[] }> = ({ label, description, options, className, ...props }) => (
  <div className={`flex flex-col gap-1.5 ${className || ''}`}>
    <label className="text-sm font-medium text-slate-700">{label}</label>
    {description && <p className="text-xs text-slate-500">{description}</p>}
    <select
      className="bg-slate-50/50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-slate-900 focus:outline-none focus:bg-white focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all appearance-none shadow-sm"
      {...props}
    >
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>{opt.label}</option>
      ))}
    </select>
  </div>
);

export const Toggle: React.FC<{ label: string; description?: string; checked: boolean; onChange: (checked: boolean) => void; className?: string }> = ({ label, description, checked, onChange, className }) => (
  <div className={`flex items-start justify-between gap-4 ${className || ''}`}>
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium text-slate-700 cursor-pointer" onClick={() => onChange(!checked)}>{label}</label>
      {description && <p className="text-xs text-slate-500 leading-relaxed">{description}</p>}
    </div>
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center justify-center rounded-full focus:outline-none focus:ring-4 focus:ring-blue-500/20 transition-colors duration-300 ${checked ? 'bg-blue-600' : 'bg-slate-200'}`}
    >
      <span className="sr-only">切换 {label}</span>
      <span
        aria-hidden="true"
        className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-sm ring-0 transition duration-300 ease-in-out ${checked ? 'translate-x-2.5' : '-translate-x-2.5'}`}
      />
    </button>
  </div>
);

export const Card: React.FC<{ title: string; description?: string; children: React.ReactNode; className?: string }> = ({ title, description, children, className }) => (
  <div className={`bg-white rounded-2xl p-6 shadow-[0_2px_12px_-4px_rgba(0,0,0,0.04)] border border-slate-100 ${className || ''}`}>
    <div className="mb-6 pb-5 border-b border-slate-100">
      <h3 className="text-lg font-semibold text-slate-800 tracking-tight">{title}</h3>
      {description && <p className="text-sm text-slate-500 mt-1.5">{description}</p>}
    </div>
    <div className="space-y-6">
      {children}
    </div>
  </div>
);
