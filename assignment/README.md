# Image Generation API

A FastAPI app that accepts an image request, answers immediately with an image ID, and generates the image in the background with Stable Diffusion. The image is fetched later by its ID.

## Setup

```bash
cd assignment
uv sync
uv run uvicorn app:app --port 8000
```

The key is read from the `.env` file in the repository root: `STABILITY_API_KEY=<your-key>`. Docs: <http://localhost:8000/docs>

## API

**`POST /images`**: `prompt` required (3–500 chars), `style` optional (`blueprint` (default), `storyboard`, `patent`).

```bash
curl -X POST localhost:8000/images -H "Content-Type: application/json" \
  -d '{"prompt": "a cat riding a bicycle", "style": "patent"}'
```

Returns `202` immediately with `{"image_id": "...", "status": "processing", "prompt": "<final prompt>"}`, or `422` for an invalid body.

**`GET /image/{image_id}`**

```bash
curl -o cat.png localhost:8000/image/<image_id>
```

| State | Status | Body |
|---|---|---|
| ready | `200` | PNG bytes (`image/png`) |
| processing | `202` | `{"image_id": "...", "status": "processing"}` |
| failed | `500` | `{"image_id": "...", "status": "failed", "error": "..."}` |
| unknown ID | `404` | `{"detail": "image not found"}` |

## Design decisions

- **BackgroundTasks instead of a Redis queue:** a single process is enough for this app, so no extra infrastructure is needed.
- **`gen_image_task` is a plain `def`:** the Stability SDK is synchronous and blocks for ~15 s. FastAPI runs plain `def` tasks in a thread pool; `async def` would block the event loop and the whole API. The task catches exceptions and the `None` the SDK returns when the safety filter triggers, so a job ends as `failed` instead of staying `processing` forever.
- **In-memory job store:** a dict maps each ID to its status; images are saved in `generated_images/`. Simple, but lost on restart and limited to one process. In production this would be Redis or a database.
- **Prompt system:** `prompt_builder.py` appends a style preset to the user's subject, so users only describe *what* they want. `ImageGenerator` stays unchanged and always adds a pencil-sketch style, so the three presets are chosen to fit that style: technical blueprint, storyboard panel and vintage patent drawing.

## Limitations

- Job states are lost on restart.
- Single worker only.
- No authentication.
- Prompts blocked by Stability's safety filter end as `failed`.
