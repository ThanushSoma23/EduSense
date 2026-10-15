import React from "react";
import { useEffect, useState } from "react";
import { BookOpen, CheckCircle2, Clock3, MessageCircle } from "lucide-react";
import { studentApi } from "../../api/services";
import PageHeader from "../../components/PageHeader";
import StatCard from "../../components/StatCard";

export default function StudentDashboard() {
  const [results, setResults] = useState([]);
  useEffect(() => { studentApi.results().then(r=>setResults(r.data?.results || r.data || [])).catch(()=>{}); }, []);
  const average = results.length ? Math.round(results.reduce((a,r)=>a+Number(r.total_marks||r.score||0),0)/results.length) : 0;

  return <div>
    <PageHeader title="Student Dashboard" subtitle="Track your assessments, results and learning progress." />
    <div className="stats-grid">
      <StatCard label="Assessments" value={results.length} icon={BookOpen}/>
      <StatCard label="Average score" value={average || "—"} icon={CheckCircle2}/>
      <StatCard label="Pending review" value="—" icon={Clock3}/>
      <StatCard label="AI Tutor" value="Ready" icon={MessageCircle}/>
    </div>
    <div className="dashboard-grid">
      <section className="card"><h2>Recent results</h2>{results.length ? results.slice(0,5).map((r,i)=><div className="list-row" key={i}><div><strong>{r.exam_title || r.exam_name || `Assessment ${i+1}`}</strong><span>{r.status || "Published"}</span></div><strong>{r.total_marks ?? r.score ?? "—"}</strong></div>) : <Empty text="Your published results will appear here."/>}</section>
      <section className="card accent-card"><MessageCircle size={28}/><h2>Need help?</h2><p>Ask the EduSense AI Tutor about your published assessment and learning areas.</p><a href="/student/tutor" className="btn btn-primary">Open AI Tutor</a></section>
    </div>
  </div>;
}
function Empty({text}) { return <div className="empty">{text}</div>; }