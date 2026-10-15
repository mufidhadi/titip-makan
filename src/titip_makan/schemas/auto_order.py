from typing import List
from pydantic import BaseModel, ConfigDict, Field, model_validator

class AutoOrderCandidate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    vendor: str = Field(..., min_length=1, max_length=100, examples=["Mie Ayam"])
    item_name: str = Field(..., min_length=1, max_length=150, examples=["Mie Ayam Polos"])
    price: int = Field(default=0, ge=0, examples=[15000])

class AutoOrderPreferenceIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    user_name: str = Field(..., min_length=1, max_length=100, examples=["Amal"])
    enabled: bool = False
    candidates: List[AutoOrderCandidate] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def enabled_needs_candidates(self):
        if self.enabled and not self.candidates:
            raise ValueError("Pilih minimal satu menu untuk auto pesan random.")
        return self

class AutoOrderPreferenceOut(BaseModel):
    user_name: str
    enabled: bool
    candidates: List[AutoOrderCandidate]
