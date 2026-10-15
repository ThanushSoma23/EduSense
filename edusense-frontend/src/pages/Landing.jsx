import React from "react";
import { ArrowRight, Brain, CheckCircle2, GraduationCap, ShieldCheck, Sparkles, BarChart3, MessageCircle, FileCheck2, Menu } from "lucide-react";
import { Link } from "react-router-dom";

export default function Landing() {
  return (
    <div className="landing">
      <nav className="landing-nav">
        <Link className="brand landing-brand" to="/">
          <div className="brand-icon"><GraduationCap size={24} /></div>
          <div><strong>EduSense</strong><span>AI-powered education</span></div>
        </Link>
        <div className="landing-links">
          <a href="#features">Features</a>
          <a href="#how">How it works</a>
          <a href="#roles">For teachers & students</a>
        </div>
        <div className="nav-actions">
          <Link className="btn btn-ghost" to="/login">Log in</Link>
          <Link className="btn btn-primary" to="/register">Get started free <ArrowRight size={16}/></Link>
        </div>
        <button className="mobile-menu" aria-label="Menu"><Menu size={25}/></button>
      </nav>

      <main>
        <section className="hero redesigned-hero">
          <div className="hero-copy">
            <div className="eyebrow"><Sparkles size={16}/> AI-powered learning & assessment</div>
            <h1>Make every assessment <span>smarter.</span></h1>
            <p className="hero-lead">Evaluate answers, manage exams, support students and turn feedback into better learning — all in one simple platform.</p>
            <div className="hero-actions">
              <Link className="btn btn-primary btn-lg" to="/register">Get started free <ArrowRight size={18}/></Link>
              <Link className="btn btn-secondary btn-lg" to="/login">Explore EduSense</Link>
            </div>
            <div className="trust-row">
              <span><CheckCircle2 size={16}/> Teacher-controlled final marks</span>
              <span><ShieldCheck size={16}/> Secure role-based access</span>
            </div>
          </div>

          <div className="hero-visual">
            <div className="dashboard-preview">
              <div className="preview-top"><span className="preview-brand"><GraduationCap size={16}/> EduSense</span><span className="preview-pill">Live overview</span></div>
              <div className="preview-title">Good morning, Teacher 👋<small>Here’s what is happening today.</small></div>
              <div className="preview-stats">
                <div><span>Students</span><strong>248</strong><b>+12%</b></div>
                <div><span>Evaluations</span><strong>86</strong><b>Today</b></div>
                <div><span>Avg. score</span><strong>82%</strong><b>+4.2%</b></div>
              </div>
              <div className="preview-chart"><div className="chart-label">Evaluation activity</div><div className="bars">{[45,62,50,78,67,91,73].map((h,i)=><i key={i} style={{height:`${h}%`}} />)}</div></div>
            </div>
            <div className="floating-card floating-ai"><Brain size={20}/><div><strong>AI evaluation</strong><span>Suggestions ready for review</span></div></div>
            <div className="floating-card floating-score"><span>Average score</span><strong>82%</strong><small>↑ 4.2% this week</small></div>
          </div>
        </section>

        <section className="trust-strip">
          <span>BUILT FOR MODERN EDUCATION</span>
          <b>Assessment</b><b>Feedback</b><b>Learning</b><b>Student support</b>
        </section>

        <section id="features" className="section">
          <div className="section-heading">
            <div className="eyebrow"><Sparkles size={15}/> One connected platform</div>
            <h2>Everything you need to make learning <span>more effective.</span></h2>
            <p>EduSense brings the everyday tools for teachers and students into one focused workspace.</p>
          </div>
          <div className="feature-grid">
            <article className="feature-card feature-wide"><div className="feature-icon"><FileCheck2/></div><h3>AI-assisted evaluation</h3><p>Get AI-generated evaluation suggestions while keeping the teacher in control of the final marks.</p><Link to="/login">See evaluation workflow <ArrowRight size={16}/></Link></article>
            <article className="feature-card"><div className="feature-icon orange"><BarChart3/></div><h3>Clear results</h3><p>Students can view marks and feedback in a simple, organised results space.</p></article>
            <article className="feature-card"><div className="feature-icon purple"><MessageCircle/></div><h3>AI Tutor</h3><p>Give students an always-available place to ask questions and learn.</p></article>
          </div>
        </section>

        <section id="how" className="section workflow-section">
          <div className="workflow-copy">
            <div className="eyebrow"><Brain size={15}/> Simple workflow</div>
            <h2>From answer sheet to <span>useful feedback.</span></h2>
            <p>Designed around the real teacher workflow: prepare, evaluate, review, award and publish.</p>
          </div>
          <div className="workflow-steps">
            <div><b>01</b><div><strong>Create exams</strong><span>Prepare questions, marks and concepts.</span></div></div>
            <div><b>02</b><div><strong>Upload answer sheets</strong><span>Bring student responses into EduSense.</span></div></div>
            <div><b>03</b><div><strong>Review AI suggestions</strong><span>Use AI assistance while retaining teacher control.</span></div></div>
            <div><b>04</b><div><strong>Publish results</strong><span>Share final results with students.</span></div></div>
          </div>
        </section>

        <section id="roles" className="role-section">
          <div><div className="role-card teacher-role"><span className="role-label">FOR TEACHERS</span><h2>Less repetitive work.<br/><em>More time to teach.</em></h2><p>Manage exams, evaluate answer sheets, review AI suggestions and publish final results from one dashboard.</p><Link className="btn btn-primary" to="/register">Create teacher account <ArrowRight size={16}/></Link></div>
          <div className="role-card student-role"><span className="role-label">FOR STUDENTS</span><h2>Understand your results.<br/><em>Keep learning.</em></h2><p>Access results, feedback, appeals and an AI Tutor in one place.</p><Link className="btn btn-secondary" to="/register">Join as a student <ArrowRight size={16}/></Link></div></div>
        </section>

        <section className="final-cta">
          <div><Sparkles size={24}/><h2>Ready to build a better learning workflow?</h2><p>Start exploring EduSense today.</p></div>
          <Link className="btn btn-primary btn-lg" to="/register">Get started free <ArrowRight size={18}/></Link>
        </section>
      </main>

      <footer className="landing-footer"><span>© 2026 EduSense</span><span>AI-powered education platform</span></footer>
    </div>
  );
}
