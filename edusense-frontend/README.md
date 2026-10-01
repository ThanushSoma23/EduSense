# EduSense — Complete React Frontend

This is the single frontend package for the EduSense FastAPI backend supplied with the project.

## 1. Install
Install Node.js 18+ (Node 20+ recommended).

## 2. Start backend
Run the existing FastAPI backend first. The backend's URL is usually something like:
`http://localhost:8000`

## 3. Configure frontend
Copy `.env.example` to `.env` and set:

VITE_API_BASE_URL=http://localhost:8000/api/v1

## 4. Install and run

Windows:
```powershell
npm install
npm run dev
```

macOS/Linux:
```bash
npm install
npm run dev
```

Open the Vite URL shown in the terminal, normally `http://localhost:5173`.

## Included frontend areas
- Landing page
- Login and registration
- Student dashboard
- Student published results and question breakdown
- Student appeals
- Student AI Tutor
- Teacher dashboard
- Exam creation with questions/model answers/concepts
- Answer-sheet upload and preprocessing trigger
- AI evaluation trigger/result review
- Transcript/evaluation update API integration
- Teacher final-mark award API integration
- Knowledge Base upload
- Publish-status and result publishing
- Admin teacher approvals
- Axios authentication/API layer
- Responsive desktop/mobile UI

## Backend API contract
The frontend uses the routes exposed by the supplied FastAPI router, including:
`/auth`, `/admin`, `/exams`, `/sheets`, `/evaluate`, `/kb`, `/answers/{id}/transcript`, `/marks/{id}/award`, `/exams/{id}/publish-status`, `/exams/{id}/publish`, `/student/results`, `/appeals`, and `/tutor/chat`.

## Important backend note
The supplied backend ZIP imports `app.schemas.schemas`, but that module is not present in the uploaded archive. If the backend gives an import error, restore that missing backend schema module before testing the frontend.

The frontend does not replace or modify your backend. It is a React client for it.


## Run
1. Open a terminal in this folder.
2. Run `npm install`
3. Run `npm run dev`
4. Open http://localhost:5173/

## JSX runtime fix
This version includes explicit React imports and a Vite automatic JSX-runtime configuration,
so the app does not fail with `React is not defined`.


## UI redesign
The landing page and public-facing visual system were redesigned with a modern EdTech style inspired by the provided reference screenshot, while keeping EduSense branding and existing routes.


# EduSense Backend Connection

## Frontend
```text
http://localhost:5173
```

## Backend
The frontend expects the FastAPI backend at:
```text
http://localhost:8000/api/v1
```

Create `.env` from `.env.example`:
```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

## Start the frontend
```powershell
npm install
npm run dev
```

## Start the backend
Open a second terminal in the backend folder supplied by your team. Create/activate the Python virtual environment, install the project's requirements, then start the FastAPI app using the command specified by the backend README (commonly `uvicorn app.main:app --reload --port 8000` if `app/main.py` contains the FastAPI instance).

Before testing registration, open:
```text
http://localhost:8000/docs
```
If Swagger loads, the backend is running.

## Registration / College limitation
The frontend does NOT modify the backend. The College field is now a searchable/manual-looking text input, but registration still sends the `college_id` required by the existing backend. Therefore the typed college must match a college already registered in the backend. If it does not exist, the frontend reports that it is unavailable rather than creating a new college.

## Test order
1. Start backend.
2. Start frontend.
3. Open `http://localhost:5173`.
4. Open Register.
5. Choose Student or Teacher.
6. Enter name, email and password.
7. Type/select an existing backend college.
8. Submit.
9. Check the response message.
10. Try Login with the account if the backend permits immediate login. Teacher accounts may require administrator approval according to the backend workflow.


## College selection
The registration form now uses a real college dropdown populated from the existing backend `/auth/colleges` endpoint. The selected college ID is sent to the backend. No backend changes are required. If the list is empty, start the FastAPI backend first and verify `http://localhost:8000/docs` opens.
