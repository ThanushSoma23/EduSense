import React from "react";
import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { GraduationCap } from "lucide-react";
import { useAuth } from "../../context/AuthContext";

export default function Login() {
  const { login, loading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    setError("");
    try {
      const user = await login(form);
      const destination = location.state?.from || `/${user.role || "student"}`;
      navigate(destination, { replace: true });
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Login failed");
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-panel">
        <Link className="brand auth-brand" to="/"><div className="brand-icon"><GraduationCap size={24}/></div><strong>EduSense</strong></Link>
        <div className="auth-copy"><h1>Welcome back</h1><p>Sign in to continue to your EduSense workspace.</p></div>
        {error && <div className="alert error">{error}</div>}
        <form onSubmit={submit} className="form">
          <label>Email<input type="email" required value={form.email} onChange={e=>setForm({...form,email:e.target.value})} placeholder="you@example.com"/></label>
          <label>Password<input type="password" required value={form.password} onChange={e=>setForm({...form,password:e.target.value})} placeholder="••••••••"/></label>
          <button className="btn btn-primary btn-block" disabled={loading}>{loading ? "Signing in..." : "Sign in"}</button>
        </form>
        <p className="auth-footer">Don't have an account? <Link to="/register">Create one</Link></p>
      </div>
    </div>
  );
}