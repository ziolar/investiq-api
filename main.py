import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import io

load_dotenv()

from services.extractor import extract_text
from services.claude_client import analyze_document
from services.report_builder import build_excel_report

app = FastAPI(title="Investment Analysis API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

INDUSTRY_DATA_PATH = Path(__file__).parent / "data" / "industry_benchmarks.json"
with open(INDUSTRY_DATA_PATH, encoding="utf-8") as f:
    INDUSTRY_BENCHMARKS = json.load(f)

ALLOWED_EXTENSIONS = {".pdf", ".pptx", ".ppt", ".xlsx", ".xls"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


@app.get("/")
def health():
    return {"status": "ok", "message": "Investment Analysis API is running"}


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型 {suffix}，请上传 PDF、PPT/PPTX 或 Excel 文件"
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件大小超过 20MB 限制")

    try:
        text = extract_text(content, file.filename)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"文件解析失败：{str(e)}")

    if not text.strip():
        raise HTTPException(status_code=422, detail="文件内容为空，无法分析")

    try:
        analysis = await analyze_document(text, file.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 分析失败：{str(e)}")

    # Attach industry benchmarks
    tag = analysis.get("industry_tag", "其他")
    analysis["industry_data"] = INDUSTRY_BENCHMARKS.get(tag, INDUSTRY_BENCHMARKS["其他"])

    return analysis


@app.post("/api/report")
async def generate_report(analysis: dict):
    try:
        excel_bytes = build_excel_report(analysis)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"报告生成失败：{str(e)}")

    project_name = analysis.get("project_name", "investment")
    filename = f"{project_name}_投资评估报告.xlsx"

    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}
    )
