import api from "./client";

export const authApi = {
  colleges: () => api.get("/auth/colleges"),
  me: () => api.get("/auth/me"),
  checkAccessCode: (payload) => api.post("/auth/check-access-code", payload),
  forgotPassword: (payload) => api.post("/auth/forgot-password", payload),
  registerStudent: (payload) => api.post("/auth/register/student", payload),
  registerTeacher: (payload) => api.post("/auth/register/teacher", payload),
};

export const studentApi = {
  results: () => api.get("/student/results"),
  evaluation: (sheetId) => api.get(`/evaluate/${sheetId}/result`),
  tutorChat: (payload) => api.post("/tutor/chat", payload),
};

export const teacherApi = {
  exams: () => api.get("/exams"),
  exam: (id) => api.get(`/exams/${id}`),
  createExam: (payload) => api.post("/exams", payload),
  uploadReference: (id, formData) => api.post(`/exams/${id}/reference`, formData, {headers:{"Content-Type":"multipart/form-data"}}),
  uploadSheet: (formData) => api.post("/sheets/upload", formData, {headers:{"Content-Type":"multipart/form-data"}}),
  evaluateSheet: (sheetId) => api.post(`/evaluate/${sheetId}`),
  evaluationResult: (sheetId) => api.get(`/evaluate/${sheetId}/result`),
  uploadKb: (formData) => api.post("/kb/upload", formData, {headers:{"Content-Type":"multipart/form-data"}}),
  updateTranscript: (answerId, text) => api.patch(`/answers/${answerId}/transcript`, {text}),
  awardMarks: (answerId, payload) => api.post(`/marks/${answerId}/award`, payload),
  publishStatus: (examId) => api.get(`/exams/${examId}/publish-status`),
  publish: (examId) => api.post(`/exams/${examId}/publish`),
  appeals: () => api.get("/appeals"),
};

export const adminApi = {
  pendingTeachers: () => api.get("/admin/pending-teachers"),
  actionTeacher: (teacherId, action) => api.post("/admin/approve-teacher", {teacher_id: teacherId, action}),
};