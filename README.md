# 📐 Beam Deflection Visualizer

An interactive engineering web application and REST API for structural and mechanical engineers, researchers, and students.
Enter beam parameters, support configurations, point loads, uniformly distributed loads (UDL), triangular loads (UVL), and concentrated moments to compute and visualize **Shear Force Diagrams (SFD)**, **Bending Moment Diagrams (BMD)**, **Slope Diagrams**, and **Elastic Deflection Curves**.

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🌟 Key Features

- **Live 2D Beam Schematic Canvas**: Interactive high-DPI canvas showing real-time updates of the beam member, pin supports, roller supports, fixed clamps, point loads, distributed loads with directional arrows, and dimension tick lines.
- **Euler-Bernoulli Calculation Engine**:
  - Uses 1D Hermite cubic finite element formulation with high-density numerical discretization (350+ evaluation nodes).
  - Automatically handles **Statically Determinate** (Simply Supported, Cantilever, Overhanging) and **Statically Indeterminate** beams (Propped Cantilever, Fixed-Fixed, Continuous beams).
  - Supports combinations of:
    - **Point Loads** ($ in $\text{kN}$)
    - **Uniformly Distributed Loads** ($\text{UDL}$, $ in $\text{kN/m}$)
    - **Linearly Varying Loads** ($\text{UVL}$, triangular/trapezoidal  \to w_2$ in $\text{kN/m}$)
    - **Concentrated Moments** ($ in $\text{kN}\cdot\text{m}$)
  - Verifies global static equilibrium ($\sum F_y = 0, \sum M = 0$).
- **Interactive Engineering Diagrams (Chart.js)**:
  - **Shear Force Diagram (SFD)** with zero-axis line and shaded positive/negative shear fields.
  - **Bending Moment Diagram (BMD)** highlighting peak sagging and hogging bending moments.
  - **Elastic Deflection Curve ((x)$)** showing the magnified deflected profile of the beam in millimeters ($\text{mm}$).
  - **Slope Diagram ($\theta(x)$)** in milliradians ($\text{mrad}$).
- **Cross-Section Inertia Calculator**:
  - Computes Area Moment of Inertia $ and Section Modulus $ for:
    - Solid Rectangular sections ( \times h$)
    - Solid Circular sections (Diameter $)
    - Hollow Circular pipes (Outer  \times$ Inner $)
    - Standard I-Beam profiles (, h, t_f, t_w$)
- **Material Database**: Preloaded with Structural Steel (A36), Stainless Steel 304, Aluminum 6061-T6, Structural Timber, Concrete C30, and Titanium.
- **Engineering Presets**: 1-click loading for standard engineering cases:
  1. Simply Supported — Center Point Load
  2. Simply Supported — Full UDL
  3. Cantilever — End Point Load
  4. Cantilever — Full UDL
  5. Overhanging Beam — Combined Loads
  6. Propped Cantilever — Indeterminate
  7. Fixed-Fixed Beam — Center Load

---

## 🔬 Mathematical Formulation

The solver employs the **Euler-Bernoulli beam theory**:

EI \frac{d^4 v}{dx^4} = q(x)
EI \frac{d^3 v}{dx^3} = V(x)
EI \frac{d^2 v}{dx^2} = M(x)
\theta(x) = \frac{dv}{dx}

Where:
- (x)$ is vertical displacement (deflection)
- $ is Young's Modulus ($\text{GPa} = 10^9\text{ N/m}^2$)
- $ is Area Moment of Inertia (^6\text{ mm}^4 = 10^{-6}\text{ m}^4$)
- (x)$ is the internal shear force
- (x)$ is the internal bending moment

### Sign Conventions:
- **Applied Downward Loads**: Entered as positive magnitudes acting downward.
- **Shear Force (x)$**: Upward forces to the left of the section produce positive shear.
- **Bending Moment (x)$**: Sagging (tension at bottom, compression at top) is positive ($+$); Hogging (tension at top) is negative ($-$).
- **Deflection**: Downward deflection is negative in Cartesian coordinate system and reported in millimeters ($\text{mm}$).

---

## 🚀 Quick Start (Local Development)

### 1. Clone & Activate Environment
`ash
# Clone the repository
git clone https://github.com/shirudepratik24-stack/beam-deflection-visualizer.git
cd beam-deflection-visualizer

# Create virtual environment
python -m venv .venv

# Activate environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
`

### 2. Run the Development Server
`ash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
`
Open your browser at:
- Web Application: **http://localhost:8000**
- Interactive Swagger API: **http://localhost:8000/docs**
- ReDoc Documentation: **http://localhost:8000/redoc**

### 3. Run Test Suite
`ash
pytest tests/ -v
`

---

## 📡 REST API Reference

### POST /api/calculate
Calculates internal reactions, critical singularity points, and sampled diagram curves.

**Request Payload:**
`json
{
  "beam": {
    "length": 6.0,
    "elastic_modulus": 200.0,
    "moment_of_inertia": 83.3
  },
  "supports": [
    {"id": "S1", "type": "pin", "position": 0.0},
    {"id": "S2", "type": "roller", "position": 6.0}
  ],
  "loads": [
    {"type": "point", "magnitude": 20.0, "position": 3.0}
  ]
}
`

**Response Payload:**
`json
{
  "success": true,
  "beam_length": 6.0,
  "reactions": [
    {"support_id": "S1", "support_type": "pin", "position": 0.0, "vertical_force_kN": 10.0, "moment_kNm": 0.0},
    {"support_id": "S2", "support_type": "roller", "position": 6.0, "vertical_force_kN": 10.0, "moment_kNm": 0.0}
  ],
  "equilibrium": {
    "sum_applied_vertical_kN": 20.0,
    "sum_reaction_vertical_kN": 20.0,
    "vertical_balance_error_kN": 0.0,
    "is_equilibrated": true
  },
  "max_deflection_mm": -5.402,
  "max_deflection_x": 3.0,
  "max_shear_kN": 10.0,
  "min_shear_kN": -10.0,
  "max_moment_kNm": 30.0,
  "min_moment_kNm": 0.0,
  "diagrams": {
    "x": [0.0, 0.5, ...],
    "shear_force": [10.0, 10.0, ...],
    "bending_moment": [0.0, 5.0, ...],
    "deflection": [0.0, -1.2, ...]
  }
}
`

### Other Endpoints
- GET /health — Health check & uptime status
- GET /api/presets — Preconfigured engineering cases
- GET /api/materials — Engineering materials modulus library
- POST /api/section-calculator — Compute $ and $ from dimensions

---

## ☁️ Deployment on Railway

The repository includes a ready-to-run Procfile and ailway.toml:
`	oml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port "
`

1. Create a project at [railway.app](https://railway.app).
2. Connect your GitHub repository eam-deflection-visualizer.
3. Railway automatically detects Python via Nixpacks and starts the service.

---

## 📄 License

This project is licensed under the MIT License.
