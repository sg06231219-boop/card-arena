"""
卡牌竞技场 - FastAPI 后端
版本: v1.0.0
独立部署，不依赖 SG 建站
"""

import os
import uuid
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── 配置 ──────────────────────────────────────────────
ZHIPUAI_API_KEY = os.environ.get("ZHIPUAI_API_KEY", "")
ZHIPUAI_IMAGE_URL = "https://open.bigmodel.cn/api/paas/v4/images/generations"

VERSION = "1.0.0"

# ── FastAPI 应用 ──────────────────────────────────────
app = FastAPI(title="卡牌竞技场", version=VERSION)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件目录
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ── 请求模型 ──────────────────────────────────────────
class GenerateArtRequest(BaseModel):
    prompt: str
    model: str = "cogview-4"


# ── 路由 ──────────────────────────────────────────────
@app.get("/")
async def index():
    """首页"""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/admin")
async def admin():
    """管理后台"""
    return FileResponse(os.path.join(STATIC_DIR, "admin.html"))


@app.get("/api/health")
async def health():
    """健康检查"""
    return {
        "status": "ok",
        "version": VERSION,
        "service": "card-arena",
    }


@app.post("/api/card-game/generate-art")
async def generate_art(req: GenerateArtRequest):
    """
    调用智谱 AI 生成卡牌图片
    前端发送 prompt，后端调用智谱 CogView API 返回图片 URL
    """
    if not ZHIPUAI_API_KEY:
        raise HTTPException(status_code=500, detail="ZHIPUAI_API_KEY 未配置")

    headers = {
        "Authorization": f"Bearer {ZHIPUAI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": req.model,
        "prompt": req.prompt,
        "size": "1024x1024",
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(ZHIPUAI_IMAGE_URL, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        # 智谱返回格式: {"data": [{"url": "https://..."}]}
        image_url = data.get("data", [{}])[0].get("url", "")
        if not image_url:
            raise HTTPException(status_code=502, detail="智谱 API 未返回图片 URL")

        return {
            "success": True,
            "image_url": image_url,
            "prompt": req.prompt,
        }

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"智谱 API 错误: {e.response.text}",
        )
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"请求智谱 API 失败: {str(e)}")
    except (KeyError, IndexError) as e:
        raise HTTPException(status_code=502, detail=f"解析智谱响应失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
