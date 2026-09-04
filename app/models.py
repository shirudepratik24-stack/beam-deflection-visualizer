from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class SupportType(str, Enum):
    PIN = "pin"
    ROLLER = "roller"
    FIXED = "fixed"

class LoadType(str, Enum):
    POINT = "point"
    UDL = "udl"
    UVL = "uvl"
    MOMENT = "moment"

class Support(BaseModel):
    id: Optional[str] = None
    type: SupportType
    position: float = Field(..., ge=0.0, description="Position in meters from left end")

class Load(BaseModel):
    id: Optional[str] = None
    type: LoadType
    magnitude: Optional[float] = Field(None, description="Magnitude (kN for point load, kN*m for moment)")
    position: Optional[float] = Field(None, description="Position in meters for point load or moment")
    start_pos: Optional[float] = Field(None, description="Start position in meters for distributed load")
    end_pos: Optional[float] = Field(None, description="End position in meters for distributed load")
    start_magnitude: Optional[float] = Field(None, description="Start intensity in kN/m for distributed load")
    end_magnitude: Optional[float] = Field(None, description="End intensity in kN/m for distributed load")

class BeamParameters(BaseModel):
    length: float = Field(..., gt=0.0, description="Beam length in meters")
    elastic_modulus: float = Field(200.0, gt=0.0, description="Young's modulus E in GPa")
    moment_of_inertia: float = Field(83.3, gt=0.0, description="Moment of inertia I (value in 10^6 mm^4, equivalent to 10^-6 m^4)")

class BeamAnalysisRequest(BaseModel):
    beam: BeamParameters
    supports: List[Support] = Field(..., min_length=1)
    loads: List[Load] = Field(default_factory=list)

class ReactionForce(BaseModel):
    support_id: str
    support_type: str
    position: float
    vertical_force_kN: float
    moment_kNm: float

class EquilibriumSummary(BaseModel):
    sum_applied_vertical_kN: float
    sum_reaction_vertical_kN: float
    vertical_balance_error_kN: float
    sum_applied_moment_kNm: float
    sum_reaction_moment_kNm: float
    moment_balance_error_kNm: float
    is_equilibrated: bool

class CriticalPoint(BaseModel):
    type: str
    position: float
    value: float
    unit: str
    description: str

class DiagramData(BaseModel):
    x: List[float]
    shear_force: List[float]
    bending_moment: List[float]
    slope: List[float]
    deflection: List[float]

class BeamAnalysisResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    beam_length: float
    reactions: List[ReactionForce]
    equilibrium: EquilibriumSummary
    max_deflection_mm: float
    max_deflection_x: float
    max_shear_kN: float
    min_shear_kN: float
    max_moment_kNm: float
    min_moment_kNm: float
    critical_points: List[CriticalPoint]
    diagrams: DiagramData
    summary_text: str
