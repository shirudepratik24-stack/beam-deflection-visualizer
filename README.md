# Student Directory — FastAPI + Vanilla JS

A simple full-stack Student Management System built with **FastAPI** (Python) on the backend and **HTML/CSS/JavaScript** on the frontend.

## Features

- View all students
- Search student by ID
- Filter students by course
- Clean, responsive UI

## Project Structure

`
FastAPI/
├── main.py              # FastAPI backend
├── Frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
└── .gitignore
`

## Setup & Run

### 1. Create & activate virtual environment
`ash
python -m venv .venv
.venv\Scripts\activate
`

### 2. Install dependencies
`ash
pip install fastapi uvicorn
`

### 3. Start the server
`ash
uvicorn main:app --reload
`

### 4. Open the frontend
Open `Frontend/index.html` in your browser.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | / | Welcome message |
| GET | /students | Get all students |
| GET | /students?course={name} | Filter by course |
| GET | /students/{id} | Get student by ID |

## Tech Stack

- **Backend:** Python, FastAPI, Uvicorn
- **Frontend:** HTML5, CSS3, Vanilla JavaScript
