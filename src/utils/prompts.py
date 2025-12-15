import yaml
from pathlib import Path
from typing import Any


class PromptRenderError(Exception):
    """Raised when prompt rendering fails."""


def load_prompt_from_yaml(
    yaml_path: str,
    prompt_key: str,
    **kwargs: Any
) -> str:
    """
    Load and render a prompt template from a YAML file.

    Args:
        yaml_path (str): Path to YAML file containing prompts.
        prompt_key (str): Key of the prompt to load.
        **kwargs: Variables to substitute into the template.

    Returns:
        str: Rendered prompt.

    Raises:
        FileNotFoundError: If YAML file does not exist.
        KeyError: If prompt_key is missing.
        PromptRenderError: If rendering fails.
    """
    main_path = f"src/prompts/{yaml_path}"      
    path = Path(main_path)

    if not path.exists():
        raise FileNotFoundError(f"Prompt YAML not found: {path}")

    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        raise PromptRenderError(f"Failed to load YAML: {e}")

    if prompt_key not in data:
        raise KeyError(f"Prompt '{prompt_key}' not found in {yaml_path}")

    template = data[prompt_key].get("template")
    if not template:
        raise PromptRenderError(f"Prompt '{prompt_key}' has no template field")

    try:
        return template.format(**kwargs)
    except KeyError as e:
        missing = e.args[0]
        raise PromptRenderError(
            f"Missing template variable '{missing}' for prompt '{prompt_key}'"
        )
    except Exception as e:
        raise PromptRenderError(f"Failed to render prompt '{prompt_key}': {e}")
