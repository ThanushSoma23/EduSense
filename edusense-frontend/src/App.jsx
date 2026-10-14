import React, { useState, useEffect } from "react";
import api from "./api";
import {
  BookOpen,
  FileText,
  CheckCircle,
  AlertTriangle,
  Upload,
  User,
  LogOut,
  GraduationCap,
  ShieldAlert,
  Send,
  Layers,
  Sparkles,
} from "lucide-react";

export default function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [authTab, setAuthTab] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState("TEACHER");
  const [collegeId, setCollegeId] = useState("COLL-101");
  const [authError, setAuthError] = useState("");
  const [activeTab, setActiveTab] = useState("exams");

  // Exam state
  const [exams, setExams] = useState([]);
  const [newExamTitle, setNewExamTitle] = useState("");
  const [newExamSubject, setNewExamSubject] = useState("");
  const [newExamQuestions, setNewExamQuestions] = useState([
    { question_number: 1, question_text: "", model_answer: "", max_marks: 5.0 },
  ]);

  // Submissions & OCR state
  const [submissions, setSubmissions] = useState([]);
  const [selectedSub, setSelectedSub] = useState(null);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [ocrResult, setOcrResult] = useState(null);

  // Review & Grading state
  const [gradingMarks, setGradingMarks] = useState({});
  const [gradingNotes, setGradingNotes] = useState({});
  const [gradingMessage, setGradingMessage] = useState("");

  // Student results state
  const [studentResults, setStudentResults] = useState(null);

  // System Health
  const [backendHealth, setBackendHealth] = useState(null);

  useEffect(() => {
    checkHealth();
    const token = localStorage.getItem("token");
    const savedUser = localStorage.getItem("user");
    if (token && savedUser) {
      try {
        setCurrentUser(JSON.parse(savedUser));
      } catch (e) {
        localStorage.clear();
      }
    }
  }, []);

  useEffect(() => {
    if (currentUser) {
      fetchExams();
      fetchSubmissions();
    }
  }, [currentUser]);

  const checkHealth = async () => {
    try {
      const res = await api.get("/health");
      setBackendHealth(res.data);
    } catch (e) {
      setBackendHealth({ status: "offline", error: e.message });
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setAuthError("");
    try {
      const res = await api.post("/auth/login", { email, password });
      const { access_token, user } = res.data;
      localStorage.setItem("token", access_token);
      localStorage.setItem("user", JSON.stringify(user));
      setCurrentUser(user);
    } catch (err) {
      setAuthError(err.response?.data?.detail || "Authentication failed.");
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setAuthError("");
    try {
      const res = await api.post("/auth/register", {
        email,
        password,
        name,
        role,
        college_id: collegeId,
      });
      setAuthTab("login");
      setAuthError("Registration successful! Please log in.");
    } catch (err) {
      setAuthError(err.response?.data?.detail || "Registration failed.");
    }
  };

  const handleLogout = () => {
    localStorage.clear();
    setCurrentUser(null);
    setExams([]);
    setSubmissions([]);
    setSelectedSub(null);
  };

  const fetchExams = async () => {
    try {
      const res = await api.get("/exams");
      setExams(res.data);
    } catch (e) {
      console.error("Failed to load exams", e);
    }
  };

  const fetchSubmissions = async () => {
    try {
      const res = await api.get("/submissions");
      setSubmissions(res.data);
    } catch (e) {
      console.error("Failed to load submissions", e);
    }
  };

  const handleCreateExam = async (e) => {
    e.preventDefault();
    try {
      await api.post("/exams", {
        title: newExamTitle,
        subject: newExamSubject,
        questions: newExamQuestions,
      });
      setNewExamTitle("");
      setNewExamSubject("");
      setNewExamQuestions([
        { question_number: 1, question_text: "", model_answer: "", max_marks: 5.0 },
      ]);
      fetchExams();
      alert("Exam created successfully!");
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to create exam");
    }
  };

  const triggerTranscribe = async (subId) => {
    setOcrLoading(true);
    setOcrResult(null);
    try {
      const res = await api.post(`/submissions/${subId}/transcribe?backend=mock`);
      setOcrResult(res.data);
      fetchSubmissions();
    } catch (err) {
      alert(err.response?.data?.detail || "Transcription error");
    } finally {
      setOcrLoading(false);
    }
  };

  const handleApproveMark = async (answerId) => {
    const marks = gradingMarks[answerId];
    if (marks === undefined || marks === "") {
      alert("Please enter approved marks.");
      return;
    }
    try {
      await api.post("/final-marks/review", {
        answer_id: answerId,
        approved_marks: parseFloat(marks),
        evaluation_type: "AI_SUGGESTION_ACCEPTED",
        review_notes: gradingNotes[answerId] || "Approved by teacher",
      });
      setGradingMessage("Marks transactionally approved and recorded!");
      setTimeout(() => setGradingMessage(""), 3000);
      if (selectedSub) {
        const res = await api.get(`/submissions/${selectedSub.id}`);
        setSelectedSub(res.data);
      }
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to approve marks");
    }
  };

  const fetchStudentResults = async (subId) => {
    try {
      const res = await api.get(`/final-marks/student/results/${subId}`);
      setStudentResults(res.data);
    } catch (err) {
      alert(err.response?.data?.detail || "Could not fetch results");
    }
  };

  if (!currentUser) {
    return (
      <div className="auth-container">
        <header className="brand-header">
          <GraduationCap size={36} color="#3b82f6" />
          <h1>EduSense AI</h1>
          <p>Automated Answer Evaluation & OCR Pipeline</p>
          <div className="system-pill">
            Server: {backendHealth?.status === "healthy" ? "🟢 Online" : "🟡 Connecting"}
          </div>
        </header>

        <div className="auth-card">
          <div className="auth-tabs">
            <button
              className={authTab === "login" ? "active" : ""}
              onClick={() => {
                setAuthTab("login");
                setAuthError("");
              }}
            >
              Login
            </button>
            <button
              className={authTab === "register" ? "active" : ""}
              onClick={() => {
                setAuthTab("register");
                setAuthError("");
              }}
            >
              Register
            </button>
          </div>

          {authError && <div className="auth-banner">{authError}</div>}

          {authTab === "login" ? (
            <form onSubmit={handleLogin}>
              <div className="form-group">
                <label>Email Address</label>
                <input
                  type="email"
                  required
                  placeholder="teacher@edusense.edu"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>Password</label>
                <input
                  type="password"
                  required
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
              <button type="submit" className="primary-btn">
                Log In
              </button>
            </form>
          ) : (
            <form onSubmit={handleRegister}>
              <div className="form-group">
                <label>Full Name</label>
                <input
                  type="text"
                  required
                  placeholder="Prof. Alan Turing"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>Email Address</label>
                <input
                  type="email"
                  required
                  placeholder="teacher@edusense.edu"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>Password</label>
                <input
                  type="password"
                  required
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>Role</label>
                <select value={role} onChange={(e) => setRole(e.target.value)}>
                  <option value="TEACHER">Teacher</option>
                  <option value="STUDENT">Student</option>
                </select>
              </div>
              <div className="form-group">
                <label>College / Institution Code</label>
                <input
                  type="text"
                  required
                  value={collegeId}
                  onChange={(e) => setCollegeId(e.target.value)}
                />
              </div>
              <button type="submit" className="primary-btn">
                Register Account
              </button>
            </form>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <nav className="top-nav">
        <div className="nav-brand">
          <GraduationCap size={28} color="#3b82f6" />
          <span>EduSense AI</span>
          <span className="role-tag">{currentUser.role}</span>
        </div>
        <div className="nav-user">
          <User size={18} />
          <span>{currentUser.name}</span>
          <button className="logout-btn" onClick={handleLogout}>
            <LogOut size={16} /> Logout
          </button>
        </div>
      </nav>

      <div className="main-layout">
        <aside className="sidebar">
          <button
            className={activeTab === "exams" ? "active" : ""}
            onClick={() => setActiveTab("exams")}
          >
            <BookOpen size={18} /> Examinations
          </button>
          <button
            className={activeTab === "submissions" ? "active" : ""}
            onClick={() => setActiveTab("submissions")}
          >
            <Layers size={18} /> Submissions & OCR
          </button>
          {currentUser.role === "TEACHER" && (
            <button
              className={activeTab === "grading" ? "active" : ""}
              onClick={() => setActiveTab("grading")}
            >
              <CheckCircle size={18} /> Teacher Review
            </button>
          )}
          {currentUser.role === "STUDENT" && (
            <button
              className={activeTab === "results" ? "active" : ""}
              onClick={() => setActiveTab("results")}
            >
              <Sparkles size={18} /> My Exam Results
            </button>
          )}
        </aside>

        <main className="content-pane">
          {activeTab === "exams" && (
            <div className="section-card">
              <h2>Examinations</h2>
              {currentUser.role === "TEACHER" && (
                <form className="create-exam-form" onSubmit={handleCreateExam}>
                  <h3>Create New Examination</h3>
                  <div className="form-row">
                    <input
                      type="text"
                      placeholder="Exam Title (e.g. Operating Systems Final)"
                      value={newExamTitle}
                      required
                      onChange={(e) => setNewExamTitle(e.target.value)}
                    />
                    <input
                      type="text"
                      placeholder="Subject Code (e.g. CS-301)"
                      value={newExamSubject}
                      required
                      onChange={(e) => setNewExamSubject(e.target.value)}
                    />
                  </div>
                  {newExamQuestions.map((q, idx) => (
                    <div key={idx} className="question-input-card">
                      <div className="q-head">
                        <strong>Question #{q.question_number}</strong>
                        <label>
                          Max Marks:
                          <input
                            type="number"
                            step="0.5"
                            value={q.max_marks}
                            onChange={(e) => {
                              const updated = [...newExamQuestions];
                              updated[idx].max_marks = parseFloat(e.target.value);
                              setNewExamQuestions(updated);
                            }}
                          />
                        </label>
                      </div>
                      <textarea
                        placeholder="Question prompt..."
                        value={q.question_text}
                        required
                        onChange={(e) => {
                          const updated = [...newExamQuestions];
                          updated[idx].question_text = e.target.value;
                          setNewExamQuestions(updated);
                        }}
                      />
                      <textarea
                        placeholder="Model answer / key concepts..."
                        value={q.model_answer}
                        required
                        onChange={(e) => {
                          const updated = [...newExamQuestions];
                          updated[idx].model_answer = e.target.value;
                          setNewExamQuestions(updated);
                        }}
                      />
                    </div>
                  ))}
                  <button type="submit" className="primary-btn">
                    Publish Exam
                  </button>
                </form>
              )}

              <div className="table-responsive">
                <table>
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Title</th>
                      <th>Subject</th>
                      <th>Questions</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {exams.map((ex) => (
                      <tr key={ex.id}>
                        <td>{ex.id}</td>
                        <td>{ex.title}</td>
                        <td>{ex.subject}</td>
                        <td>{ex.questions?.length || 0}</td>
                        <td><span className="badge-active">Active</span></td>
                      </tr>
                    ))}
                    {exams.length === 0 && (
                      <tr>
                        <td colSpan={5} className="empty-cell">
                          No examinations created yet.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === "submissions" && (
            <div className="section-card">
              <h2>Answer Sheet Submissions & OCR Pipeline</h2>
              <div className="table-responsive">
                <table>
                  <thead>
                    <tr>
                      <th>Sub ID</th>
                      <th>Exam ID</th>
                      <th>Student ID</th>
                      <th>Status</th>
                      <th>Extracted Answers</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {submissions.map((sub) => (
                      <tr key={sub.id}>
                        <td>{sub.id}</td>
                        <td>{sub.exam_id}</td>
                        <td>{sub.student_id}</td>
                        <td>
                          <span className={`status-${sub.processing_status.toLowerCase()}`}>
                            {sub.processing_status}
                          </span>
                        </td>
                        <td>{sub.answers?.length || 0}</td>
                        <td>
                          <button
                            className="btn-action"
                            onClick={() => {
                              setSelectedSub(sub);
                              triggerTranscribe(sub.id);
                            }}
                          >
                            <FileText size={14} /> Run TrOCR
                          </button>
                          <button
                            className="btn-action"
                            onClick={() => setSelectedSub(sub)}
                          >
                            View Details
                          </button>
                        </td>
                      </tr>
                    ))}
                    {submissions.length === 0 && (
                      <tr>
                        <td colSpan={6} className="empty-cell">
                          No submissions uploaded yet.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {ocrLoading && (
                <div className="ocr-progress">
                  <div className="spinner"></div>
                  <span>Running TrOCR handwriting recognition and question segmentation...</span>
                </div>
              )}

              {selectedSub && (
                <div className="sub-detail-card">
                  <h3>Submission #{selectedSub.id} Details</h3>
                  <p><strong>File:</strong> {selectedSub.file_reference}</p>
                  <p><strong>Status:</strong> {selectedSub.processing_status}</p>

                  <div className="answers-list">
                    <h4>Segmented Questions & Answers</h4>
                    {selectedSub.answers && selectedSub.answers.length > 0 ? (
                      selectedSub.answers.map((ans) => (
                        <div key={ans.id} className="answer-item">
                          <div className="ans-header">
                            <strong>Question ID: {ans.question_id}</strong>
                            <div className="conf-badge">
                              OCR Confidence: {(ans.ocr_confidence * 100).toFixed(1)}%
                              {ans.extraction_status === "LOW_CONFIDENCE" && (
                                <span className="warning-flag">
                                  <AlertTriangle size={14} /> Needs Review
                                </span>
                              )}
                            </div>
                          </div>
                          <p className="ans-body">{ans.extracted_text || "(No answer transcribed)"}</p>
                        </div>
                      ))
                    ) : (
                      <p className="empty-note">Click "Run TrOCR" to extract student handwritten answers.</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === "grading" && currentUser.role === "TEACHER" && (
            <div className="section-card">
              <h2>Teacher Review & Mark Awarding</h2>
              <div className="principle-banner">
                <ShieldAlert size={20} color="#f59e0b" />
                <span>
                  <strong>Guiding Principle:</strong> AI assists. Teachers decide. AI suggested marks remain suggestions until explicitly approved by you.
                </span>
              </div>

              {gradingMessage && <div className="success-banner">{gradingMessage}</div>}

              {selectedSub ? (
                <div className="review-sheet">
                  <h3>Grading Submission #{selectedSub.id}</h3>
                  {selectedSub.answers?.map((ans) => (
                    <div key={ans.id} className="grading-row">
                      <div className="grading-info">
                        <strong>Question #{ans.question_id}</strong>
                        <p className="student-ans">{ans.extracted_text}</p>
                        <div className="ai-suggestion-box">
                          <Sparkles size={16} color="#8b5cf6" />
                          <span>AI Suggestion: ~85% Concept Match (Suggestion: 4.5 marks)</span>
                        </div>
                      </div>
                      <div className="grading-inputs">
                        <label>
                          Approved Marks:
                          <input
                            type="number"
                            step="0.5"
                            placeholder="e.g. 4.5"
                            value={gradingMarks[ans.id] || ""}
                            onChange={(e) =>
                              setGradingMarks({ ...gradingMarks, [ans.id]: e.target.value })
                            }
                          />
                        </label>
                        <textarea
                          placeholder="Teacher remarks..."
                          value={gradingNotes[ans.id] || ""}
                          onChange={(e) =>
                            setGradingNotes({ ...gradingNotes, [ans.id]: e.target.value })
                          }
                        />
                        <button
                          className="primary-btn"
                          onClick={() => handleApproveMark(ans.id)}
                        >
                          Approve & Finalize
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="empty-cell">Select a submission in "Submissions & OCR" tab to begin review.</p>
              )}
            </div>
          )}

          {activeTab === "results" && currentUser.role === "STUDENT" && (
            <div className="section-card">
              <h2>My Published Exam Results</h2>
              <div className="results-lookup">
                <input
                  type="number"
                  placeholder="Enter Submission ID"
                  onChange={(e) => fetchStudentResults(e.target.value)}
                />
              </div>
              {studentResults && (
                <div className="student-results-card">
                  <h3>{studentResults.exam_title}</h3>
                  <div className="score-summary">
                    <span>Total Score: <strong>{studentResults.total_final_marks} / {studentResults.total_max_marks}</strong></span>
                    <span>Status: {studentResults.is_published ? "🟢 Published" : "🟡 Under Review"}</span>
                  </div>
                  <div className="questions-breakdown">
                    {studentResults.questions?.map((q, idx) => (
                      <div key={idx} className="result-item">
                        <strong>Q{q.question_number}: {q.question_text}</strong>
                        <p>Your Answer: {q.extracted_text}</p>
                        <div className="marks-badge">
                          Approved: {q.final_approved_marks} / {q.max_marks} marks
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
