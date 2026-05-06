"""Generate a PowerPoint about renewable energy via the Claude API pptx skill.

The pptx skill is an Anthropic-managed skill loaded via the Skills API beta.
Claude executes code in a sandbox to build a .pptx, then returns it as a file
we download via the Files API.

Run:
    export ANTHROPIC_API_KEY=...
    python renewable_energy_pptx.py
"""
from __future__ import annotations

import os
from pathlib import Path

import anthropic

OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

PROMPT = (
    "Create a professional 8-slide PowerPoint presentation on renewable energy. "
    "Cover: title slide, why it matters, solar, wind, hydro, geothermal, "
    "challenges & outlook, and a closing slide. Use clean visuals and concise "
    "bullet points. Save the file and return it."
)


def main() -> None:
    client = anthropic.Anthropic()

    response = client.beta.messages.create(
        model="claude-opus-4-7",
        max_tokens=16000,
        betas=["skills-2025-10-02", "files-api-2025-04-14"],
        container={"skills": [{"type": "anthropic", "skill_id": "pptx"}]},
        tools=[{"type": "code_execution_20260120", "name": "code_execution"}],
        messages=[{"role": "user", "content": PROMPT}],
    )

    saved: list[Path] = []
    for block in response.content:
        if block.type == "text":
            print(block.text)
        elif block.type == "bash_code_execution_tool_result":
            result = block.content
            if getattr(result, "type", None) == "bash_code_execution_result":
                for ref in result.content or []:
                    if ref.type == "bash_code_execution_output":
                        meta = client.beta.files.retrieve_metadata(ref.file_id)
                        safe_name = os.path.basename(meta.filename) or ref.file_id
                        out = OUTPUT_DIR / safe_name
                        client.beta.files.download(ref.file_id).write_to_file(out)
                        saved.append(out)

    print(f"\nStop reason: {response.stop_reason}")
    print(f"Tokens: in={response.usage.input_tokens} out={response.usage.output_tokens}")
    if saved:
        print("Saved files:")
        for p in saved:
            print(f"  {p}")
    else:
        print("No files returned. Check the response text above for diagnostics.")


if __name__ == "__main__":
    main()
