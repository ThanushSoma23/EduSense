import React from "react";
export default function StatCard({ label, value, icon: Icon }) {
  return (
    <div className="stat-card">
      <div className="stat-icon"><Icon size={20} /></div>
      <div><span>{label}</span><strong>{value}</strong></div>
    </div>
  );
}