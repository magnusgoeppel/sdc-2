"""Asynchronous image generation API built on FastAPI and Stable Diffusion."""

import logging
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from image_generator import ImageGenerator
from prompt_builder import build_prompt

load_dotenv()

logger = logging.getLogger("uvicorn.error")

IMAGE_DIR = Path("generated_images")
IMAGE_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Image Generation API")
generator = ImageGenerator(os.environ["STABILITY_API_KEY"])

# In-memory job store: image_id -> {"status", "path", "prompt", "error"}.
# Lost on restart, which is acceptable for this lab.
JOBS: dict[str, dict] = {}


class ImageRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=500)
    style: str | None = None


# Plain def, NOT async def: generate_image() blocks for ~15 seconds, so FastAPI
# must run this in its thread pool instead of on the event loop.
def gen_image_task(image_id: str, prompt: str) -> None:
    """Generate the image, save it to disk and update the job status."""
    job = JOBS[image_id]
    try:
        png_bytes = generator.generate_image(prompt)
        # The SDK returns None (without raising) when the safety filter triggers.
        if png_bytes is None:
            raise ValueError("no image returned, the prompt was probably blocked by the safety filter")
        path = IMAGE_DIR / f"{image_id}.png"
        path.write_bytes(png_bytes)
        job.update(status="ready", path=path)
    except Exception as exc:
        # Without this, the error would vanish and the job would stay "processing" forever.
        logger.exception("Image generation failed for %s", image_id)
        job.update(status="failed", error=str(exc))


@app.post("/images", status_code=202)
async def create_image(request: ImageRequest, background_tasks: BackgroundTasks):
    """Accept a request and generate the image in the background."""
    image_id = str(uuid.uuid4())
    final_prompt = build_prompt(request.prompt, request.style)
    JOBS[image_id] = {"status": "processing", "path": None, "prompt": final_prompt, "error": None}
    background_tasks.add_task(gen_image_task, image_id, final_prompt)
    return {"image_id": image_id, "status": "processing", "prompt": final_prompt}


@app.get("/image/{image_id}")
async def get_image(image_id: str):
    """Return the PNG if ready, otherwise the current job status."""
    job = JOBS.get(image_id)
    if job is None:
        raise HTTPException(status_code=404, detail="image not found")
    if job["status"] == "processing":
        return JSONResponse(status_code=202, content={"image_id": image_id, "status": "processing"})
    if job["status"] == "failed":
        return JSONResponse(
            status_code=500,
            content={"image_id": image_id, "status": "failed", "error": job["error"]},
        )
    return Response(content=job["path"].read_bytes(), media_type="image/png")
