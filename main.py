from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

students = [
    {
        "id": 1,
        "name": "John Doe",
        "age": 20,
        "course": "Python"
    },
    {
        "id": 2,
        "name": "Jane Smith",
        "age": 22,
        "course": "Java"
    }
]

@app.get("/api")
def home():
    return {"message": "Welcome to the FastAPI application!"}

@app.get("/students/{student_id}")
def get_student(student_id: int):
    for student in students:
        if student["id"] == student_id:
            return student
    return {"error": "Student not found"}

@app.get("/students")
def get_all_students(course: str = None):
    if course:
        return [
            student
            for student in students
            if student["course"].lower() == course.lower()
        ]
    return students

@app.get("/")
def serve_frontend():
    return FileResponse("Frontend/index.html")

# Serve static files (CSS, JS) from the Frontend folder
app.mount("/static", StaticFiles(directory="Frontend"), name="static")