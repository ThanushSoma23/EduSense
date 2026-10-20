import React from "react";
import { BookOpen, ClipboardCheck, Upload, Users } from "lucide-react";
import PageHeader from "../../components/PageHeader";
import StatCard from "../../components/StatCard";

export default function TeacherDashboard() {
  return <div><PageHeader title="Teacher Dashboard" subtitle="Manage assessments, evaluate answer sheets and publish results."/>
    <div className="stats-grid"><StatCard label="Exams" value="—" icon={BookOpen}/><StatCard label="To evaluate" value="—" icon={ClipboardCheck}/><StatCard label="Uploaded sheets" value="—" icon={Upload}/><StatCard label="Appeals" value="—" icon={Users}/></div>
    <div className="dashboard-grid"><section className="card"><h2>Evaluation workflow</h2><div className="steps"><div><b>01</b><span>Upload answer sheets</span></div><div><b>02</b><span>Run AI-assisted evaluation</span></div><div><b>03</b><span>Review and award final marks</span></div><div><b>04</b><span>Publish results</span></div></div></section><section className="card accent-card"><h2>Teacher control</h2><p>AI suggestions support the review process. Final marks remain under teacher control.</p></section></div>
  </div>;
}