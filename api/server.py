from fastapi import FastAPI, Query
from typing import Optional, List
import json
from pathlib import Path

app = FastAPI(title="Donizo Materials API (Simulated)")

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "materials.json"

def load_data():
    if DATA_PATH.exists():
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return []

@app.get("/materials")
def get_materials() -> List[dict]:
    return load_data()

@app.get("/materials/{category}")
def get_by_category(category: str, supplier: Optional[str] = Query(default=None)) -> List[dict]:
    items = [x for x in load_data() if (x.get("category")==category)]
    if supplier:
        items = [x for x in items if x.get("supplier")==supplier]
    return items