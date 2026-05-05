from pathlib import Path


def read_prompt_template(path: Path, **values: str) -> str:
    text = path.read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text

