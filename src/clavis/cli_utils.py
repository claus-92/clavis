import json
from typing import Any, Callable

PromptFunc = Callable[[str], str]


def parse_options(values: list[str]) -> dict[str, object]:
    options: dict[str, object] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("Options must be KEY=VALUE")
        key, raw = value.split("=", 1)
        if raw.isdigit():
            options[key] = int(raw)
        elif raw.lower() in {"true", "false"}:
            options[key] = raw.lower() == "true"
        else:
            options[key] = raw
    return options


def parse_schema_value(raw: str, schema: dict[str, Any]) -> object:
    value_type = schema.get("type")
    if value_type == "integer":
        return int(raw)
    if value_type == "number":
        return float(raw)
    if value_type == "boolean":
        lowered = raw.lower()
        if lowered in {"true", "yes", "y", "1"}:
            return True
        if lowered in {"false", "no", "n", "0"}:
            return False
        raise ValueError(f"Expected boolean value for {schema.get('title', 'field')}")
    return raw


def build_create_config(
    options: list[str], client: "ClavisClient", prompt: PromptFunc | None = None
) -> dict[str, object]:
    """Build board configuration from supplied options and interactive input."""
    if prompt is None:
        prompt = input  # type: ignore[assignment]

    config = parse_options(options)
    board_types = client.list_board_types()
    if not isinstance(board_types, list):
        raise ValueError("Daemon returned invalid board type information")

    type_map = {item.get("board_type"): item for item in board_types if isinstance(item, dict)}
    if not type_map:
        raise ValueError("No board types are available")

    if "board_type" not in config:
        available = ", ".join(sorted(str(bt) for bt in type_map))
        config["board_type"] = prompt(f"Board type ({available})")

    board_type = str(config["board_type"])
    info = get_board_type_info(list(type_map.values()), board_type)  # reuses validation
    schema = info.get("config_schema", {}) or {}
    properties = schema.get("properties", {}) or {}
    required_fields = get_required_fields(schema)

    for field in required_fields:
        if field in config:
            continue
        field_schema = properties.get(field, {}) if isinstance(properties, dict) else {}
        if not isinstance(field_schema, dict):
            field_schema = {}
        title = field_schema.get("title") or humanize_key(str(field))
        config[str(field)] = parse_schema_value(prompt(str(title)), field_schema)

    return config


def get_board_type_info(
    board_types: list[dict[str, Any]], board_type: str
) -> dict[str, Any]:
    """Return the type info dict for a board_type, or raise if not found."""
    type_map = {item.get("board_type"): item for item in board_types if isinstance(item, dict)}
    info = type_map.get(board_type)
    if info is None:
        available = ", ".join(sorted(str(bt) for bt in type_map))
        raise ValueError(f"Unknown board type: {board_type}. Available types: {available}")
    return info


def get_required_fields(schema: dict[str, Any]) -> list[str]:
    """Return required field names from a JSON schema."""
    req = schema.get("required", [])
    if not isinstance(req, list):
        return []
    return [str(f) for f in req]


def build_config_from_prompt_answers(
    board_type: str,
    field_answers: list[str],
    board_types: list[dict[str, Any]],
) -> dict[str, object]:
    """Build a complete board config from board_type + answers to required fields in schema order.

    This is the single place that knows how to interpret the config_schema for creation.
    """
    info = get_board_type_info(board_types, board_type)
    schema = info.get("config_schema", {}) or {}
    properties = schema.get("properties", {}) or {}
    required = get_required_fields(schema)

    if len(field_answers) < len(required):
        raise ValueError("Not enough answers provided for required fields")

    config: dict[str, object] = {"board_type": board_type}
    for i, field in enumerate(required):
        raw = field_answers[i]
        field_schema = properties.get(field, {}) if isinstance(properties, dict) else {}
        if not isinstance(field_schema, dict):
            field_schema = {}
        config[field] = parse_schema_value(raw, field_schema)
    return config


def get_create_next_prompt(
    answers: list[str], board_types: list[dict[str, Any]]
) -> tuple[str | None, dict[str, object] | None]:
    """Drive the create prompts using the shared schema logic.

    Returns:
        (next_question_text, None) if more input needed
        (None, config_dict) when complete
    Raises ValueError on bad input so caller can show error.
    """
    if not board_types:
        raise ValueError("No board types available")

    type_map = {item.get("board_type"): item for item in board_types if isinstance(item, dict)}

    # Step 0: ask for board_type
    if len(answers) == 0:
        available = ", ".join(sorted(str(bt) for bt in type_map))
        return (f"Board type ({available})", None)

    board_type = answers[0]
    try:
        info = get_board_type_info(board_types, board_type)
    except Exception as e:
        raise ValueError(str(e))

    schema = info.get("config_schema", {}) or {}
    properties = schema.get("properties", {}) or {}
    required = get_required_fields(schema)

    # answers[1:] correspond to required fields
    idx = len(answers) - 1
    if idx < len(required):
        field = required[idx]
        field_schema = properties.get(field, {}) if isinstance(properties, dict) else {}
        if not isinstance(field_schema, dict):
            field_schema = {}
        title = field_schema.get("title") or humanize_key(str(field))
        return (str(title), None)

    field_answers = answers[1:]
    config = build_config_from_prompt_answers(board_type, field_answers, board_types)
    return (None, config)


def format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(format_value(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, indent=2, sort_keys=True)
    return str(value)


def humanize_key(key: str) -> str:
    result = ""
    for char in key:
        if char.isupper() and result:
            result += " "
        result += char
    return result.replace("_", " ").title()


def format_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
    if not rows:
        return "No results."

    rendered_rows = [[format_value(row.get(key, "")) for key, _ in columns] for row in rows]
    widths = [len(label) for _, label in columns]
    for row in rendered_rows:
        widths = [max(width, len(value)) for width, value in zip(widths, row)]

    header = "  ".join(label.ljust(width) for width, (_, label) in zip(widths, columns)).rstrip()
    separator = "  ".join("-" * width for width in widths).rstrip()
    lines = [header, separator]
    lines.extend("  ".join(value.ljust(width) for width, value in zip(widths, row)).rstrip() for row in rendered_rows)
    return "\n".join(lines)


def format_key_values(data: dict[str, Any]) -> str:
    simple_items = [(key, value) for key, value in data.items() if not isinstance(value, (dict, list))]
    nested_items = [(key, value) for key, value in data.items() if isinstance(value, (dict, list))]
    width = max((len(humanize_key(key)) for key, _ in simple_items), default=0)
    lines = [f"{humanize_key(key).ljust(width)}  {format_value(value)}".rstrip() for key, value in simple_items]

    for key, value in nested_items:
        if lines:
            lines.append("")
        lines.append(f"{humanize_key(key)}:")
        lines.append(format_value(value))

    return "\n".join(lines)


def format_parameters(data: dict[str, Any]) -> str:
    sections = [
        ("General Parameters", data.get("generalParameters", [])),
        ("Channel Parameters", data.get("channelParameters", [])),
        ("Group Parameters", data.get("groupParameters", [])),
    ]
    columns = [
        ("name", "name"),
        ("type", "type"),
        ("defaultValue", "default"),
        ("options", "options"),
        ("description", "description"),
    ]
    lines: list[str] = []
    for title, rows in sections:
        if lines:
            lines.append("")
        lines.append(title)
        lines.append(format_table(rows, columns) if rows else "No parameters.")
    return "\n".join(lines)


def format_result(result: Any) -> str:
    if isinstance(result, dict) and {"generalParameters", "channelParameters", "groupParameters"}.issubset(result):
        return format_parameters(result)
    if isinstance(result, dict):
        return format_key_values(result)
    if isinstance(result, list):
        if not result:
            return "No results."
        if all(isinstance(item, dict) for item in result):
            keys = list(dict.fromkeys(key for item in result for key in item.keys()))
            columns = [(key, key) for key in keys if key != "config_schema"]
            table = format_table(result, columns)
            if any("config_schema" in item for item in result):
                details = []
                for item in result:
                    schema = item.get("config_schema")
                    if schema is None:
                        continue
                    board_type = item.get("board_type", "unknown")
                    details.append(f"\nConfig schema for {board_type}:\n{json.dumps(schema, indent=2, sort_keys=True)}")
                return table + "\n" + "\n".join(details)
            return table
        return "\n".join(format_value(item) for item in result)
    return format_value(result)
