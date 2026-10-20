import React, { useEffect, useMemo, useState } from "react";
import { Eye, EyeOff, GraduationCap } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { register } from "../../api/auth";
import client from "../../api/client";

export default function Register() {
  const navigate = useNavigate();
  const [role, setRole] = useState("student");
  const [form, setForm] = useState({
    full_name: "", email: "", password: "", college_id: "",
    college_name: "", roll_number: "", subject: "", semester: "",
  });
  const [colleges, setColleges] = useState([]);
  const [collegeStatus, setCollegeStatus] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const res = await client.get("/auth/colleges");
        const list = Array.isArray(res.data) ? res.data : (res.data?.colleges || []);
        if (active) setColleges(list);
      } catch {
        if (active) setCollegeStatus("Unable to load colleges from the backend.");
      }
    })();
    return () => { active = false; };
  }, []);

  function update(e) {
    const { name, value } = e.target;
    if (name === "college_id") {
      const found = colleges.find(c => String(c.id || c.college_id) === String(value));
      setForm(prev => ({
        ...prev,
        college_id: value,
        college_name: found?.name || found?.college_name || ""
      }));
      return;
    }
    setForm(prev => ({ ...prev, [name]: value }));
  }

  async function submit(e) {
    e.preventDefault();
    setMessage("");
    if (!form.full_name || !form.email || !form.password) {
      setMessage("Please fill in your name, email and password.");
      return;
    }
    if (!form.college_id) {
      setMessage("Enter the exact name of a college available in the EduSense backend.");
      return;
    }
    setLoading(true);
    try {
      const payload = {
        full_name: form.full_name,
        email: form.email,
        password: form.password,
        college_id: form.college_id,
        ...(role === "student"
          ? { roll_number: form.roll_number }
          : { subject: form.subject, semester: form.semester })
      };
      await register(payload, role);
      setMessage(role === "teacher"
        ? "Teacher account created. It may require admin approval before access."
        : "Account created successfully. You can now log in.");
    } catch (err) {
      setMessage(err?.response?.data?.detail || "Registration failed. Check that the backend is running and the college exists.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card register-card">
        <Link to="/" className="brand auth-brand">
          <div className="brand-icon"><GraduationCap size={22}/></div>
          <strong>EduSense</strong>
        </Link>
        <h1>Create your account</h1>
        <p className="auth-subtitle">Register as a student or teacher.</p>

        <div className="role-toggle">
          <button type="button" className={role === "student" ? "active" : ""} onClick={() => setRole("student")}>Student</button>
          <button type="button" className={role === "teacher" ? "active" : ""} onClick={() => setRole("teacher")}>Teacher</button>
        </div>

        <form onSubmit={submit}>
          <label>Full name<input name="full_name" value={form.full_name} onChange={update} placeholder="Enter your full name" /></label>
          <label>Email<input type="email" name="email" value={form.email} onChange={update} placeholder="Enter your email" /></label>

          <label>Password
            <div className="password-wrap">
              <input type={showPassword ? "text" : "password"} name="password" value={form.password} onChange={update} placeholder="Enter your password" />
              <button type="button" className="password-toggle" onClick={() => setShowPassword(v => !v)} aria-label="Show or hide password">
                {showPassword ? <EyeOff size={17}/> : <Eye size={17}/>}
              </button>
            </div>
          </label>

          <label>College
            <select name="college_id" value={form.college_id} onChange={update}>
              <option value="">Select your college</option>
              {colleges.map((c, i) => (
                <option key={c.id || c.college_id || i} value={c.id || c.college_id}>
                  {c.name || c.college_name}
                </option>
              ))}
            </select>
            <small className="college-help">
              {collegeStatus || (colleges.length
                ? `${colleges.length} college${colleges.length === 1 ? "" : "s"} available`
                : "No colleges were loaded. Make sure the backend is running.")}
            </small>
          </label>

          {role === "student" && <label>Roll number<input name="roll_number" value={form.roll_number} onChange={update} placeholder="Enter your roll number" /></label>}
          {role === "teacher" && <>
            <label>Subject<input name="subject" value={form.subject} onChange={update} placeholder="Enter your subject" /></label>
            <label>Semester<input name="semester" value={form.semester} onChange={update} placeholder="Enter semester" /></label>
          </>}

          {message && <div className="auth-message">{message}</div>}
          <button className="btn btn-primary btn-block" disabled={loading}>
            {loading ? "Creating account..." : "Create account"}
          </button>
        </form>

        <p className="auth-footer">Already have an account? <Link to="/login">Log in</Link></p>
      </div>
    </div>
  );
}
