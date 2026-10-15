import React from "react";
import {NavLink,Outlet,useNavigate} from "react-router-dom";
import {BookOpen,ClipboardCheck,FileText,GraduationCap,LayoutDashboard,LogOut,MessageCircle,Upload,Users,Database,Send} from "lucide-react";
import {useAuth} from "../context/AuthContext";
const nav={
student:[["/student","Dashboard",LayoutDashboard],["/student/results","Results",FileText],["/student/appeals","Appeals",ClipboardCheck],["/student/tutor","AI Tutor",MessageCircle]],
teacher:[["/teacher","Dashboard",LayoutDashboard],["/teacher/exams","Exams",BookOpen],["/teacher/upload","Upload Sheets",Upload],["/teacher/evaluation","Evaluation",ClipboardCheck],["/teacher/knowledge","Knowledge Base",Database],["/teacher/publish","Publish Results",Send]],
admin:[["/admin","Teacher Approvals",Users]]
};
export default function Layout(){const{user,logout}=useAuth();const navs=nav[user?.role]||[];const go=useNavigate();return <div className="app-shell"><aside className="sidebar"><div className="brand"><div className="brand-icon"><GraduationCap size={24}/></div><div><strong>EduSense</strong><span>AI-powered education</span></div></div><div className="profile-mini"><div className="avatar">{(user?.full_name||"U")[0]}</div><div><strong>{user?.full_name||"User"}</strong><span>{user?.role||"user"}</span></div></div><nav>{navs.map(([to,label,I])=><NavLink key={to} to={to} end={to===`/${user?.role}`}><I size={18}/>{label}</NavLink>)}</nav><button className="logout" onClick={()=>{logout();go("/login")}}><LogOut size={18}/>Logout</button></aside><main className="main-content"><Outlet/></main></div>}