#!/usr/bin/env python3
"""
mkexample - Generate code examples for various programming languages.

Usage:
    ./mkexample.py <lang> <template> [-o <output>] [+/-options...]
    ./mkexample.py <lang> buildtool
"""

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any


class OptionNotAvailableError(Exception):
    """Raised when an option is not available for a language."""
    pass


class RequiredOptionError(Exception):
    """Raised when a required option is not enabled but was expected."""
    pass


def _read_meta(path: Path) -> dict[str, str]:
    """Parse a key=value meta.ini file into a dict."""
    meta: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if "=" in line:
            k, _, v = line.partition("=")
            meta[k.strip()] = v.strip()
    return meta


def _load_levels(directory: Path) -> dict[str, str]:
    """Return {level_key: code} for every non-meta file in a directory."""
    levels: dict[str, str] = {}
    for p in sorted(directory.iterdir()):
        if p.is_file() and p.stem != "meta":
            levels[p.stem] = p.read_text(encoding="utf-8")
    return levels


def _load_template(entry: Path) -> dict[str, Any]:
    """Load a template entry: file → {base: ...}, directory → {levels: {...}}."""
    if entry.is_file():
        return {"base": entry.read_text(encoding="utf-8")}
    # directory: may contain base.<ext> and level files
    result: dict[str, Any] = {}
    levels = _load_levels(entry)
    if "base" in levels:
        result["base"] = levels.pop("base")
    if levels:
        result["levels"] = levels
    return result


def _load_option(opt_dir: Path) -> dict[str, Any]:
    """Load one option directory into an option spec dict."""
    meta_file = opt_dir / "meta.ini"
    spec: dict[str, Any] = {}
    if meta_file.exists():
        raw = _read_meta(meta_file)
        spec["available"] = raw.get("available", "false").lower() == "true"
        spec["required"] = raw.get("required", "false").lower() == "true"
        if "description" in raw:
            spec["description"] = raw["description"]
    levels = _load_levels(opt_dir)
    if levels:
        spec["levels"] = levels
    return spec


def load_lang_specs(specs_path: Path | None = None) -> dict[str, Any]:
    """Load language specifications from a directory tree."""
    if specs_path is None:
        specs_path = Path(__file__).parent / "lang_specs"

    if not specs_path.exists():
        raise FileNotFoundError(f"Language specs directory not found: {specs_path}")
    if not specs_path.is_dir():
        raise FileNotFoundError(f"Expected a directory, got a file: {specs_path}")

    specs: dict[str, Any] = {}
    for lang_dir in sorted(specs_path.iterdir()):
        if not lang_dir.is_dir():
            continue
        lang = lang_dir.name

        # meta.ini
        meta = _read_meta(lang_dir / "meta.ini") if (lang_dir / "meta.ini").exists() else {}
        lang_spec: dict[str, Any] = {
            "extension": meta.get("extension", lang),
            "buildtool": meta.get("buildtool", "unknown"),
        }

        # templates/
        templates_dir = lang_dir / "templates"
        if templates_dir.is_dir():
            templates: dict[str, Any] = {}
            for entry in sorted(templates_dir.iterdir()):
                name = entry.stem if entry.is_file() else entry.name
                templates[name] = _load_template(entry)
            lang_spec["templates"] = templates

        # options/
        options_dir = lang_dir / "options"
        if options_dir.is_dir():
            options: dict[str, Any] = {}
            for opt_dir in sorted(options_dir.iterdir()):
                if opt_dir.is_dir():
                    options[opt_dir.name] = _load_option(opt_dir)
            lang_spec["options"] = options

        specs[lang] = lang_spec

    return specs


def parse_level(level_str: str, available_levels: list[str]) -> str:
    """
    Parse a level string and return the appropriate level key.
    
    Supports:
    - Numeric levels: 0, 1, 2, 3...
    - 'max' for maximum complexity
    - 'rand' for random selection
    """
    if level_str == "rand":
        return random.choice(available_levels)
    
    if level_str == "max":
        return "max" if "max" in available_levels else available_levels[-1]
    
    # Try numeric
    if level_str in available_levels:
        return level_str
    
    # Try to find closest numeric level
    try:
        requested = int(level_str)
        numeric_levels = [l for l in available_levels if l.isdigit()]
        if not numeric_levels:
            return available_levels[0]
        
        # Find the closest level that doesn't exceed requested
        valid = [l for l in numeric_levels if int(l) <= requested]
        if valid:
            return max(valid, key=int)
        return min(numeric_levels, key=int)
    except ValueError:
        return available_levels[0]


# Level specifiers that are recognized as complexity levels (not param values)
_LEVEL_KEYS = {"max", "rand", "types"}


def parse_items(
    items: list[str],
    lang_spec: dict[str, Any],
) -> tuple[str | None, dict[str, tuple[bool, str]], dict[str, str]]:
    """
    Parse positional item arguments into a template name, options, and params.

    Each item is one of:
      class           → enable 'class' option at level 0
      class=max       → enable 'class' option at level 'max'
      comment=1       → enable 'comment' option at level '1'
      classname=Foo   → named param  (value is not a level specifier)
      helloworld      → explicit template name
      buildtool       → passed through as template (special-cased in main)

    Returns (template, options, params).
    """
    known_options   = set(lang_spec.get("options",   {}).keys())
    known_templates = set(lang_spec.get("templates", {}).keys())

    template: str | None = None
    options:  dict[str, tuple[bool, str]] = {}
    params:   dict[str, str] = {}

    for item in items:
        if "=" in item:
            key, _, val = item.partition("=")
            # val is a level specifier if it's a digit or a known level keyword
            if val.isdigit() or val in _LEVEL_KEYS:
                options[key] = (True, val)
            else:
                params[key] = val
        elif item in known_options:
            options[item] = (True, "0")
        elif item in known_templates or item == "buildtool":
            template = item
        else:
            # Unknown item – treat as template name (user may be extending specs)
            template = item

    return template, options, params


def validate_options(lang: str, lang_spec: dict[str, Any], options: dict[str, tuple[bool, str]]) -> None:
    """
    Validate that all requested options are available for the language.
    Raises OptionNotAvailableError if an unavailable option is requested.
    """
    available_options = lang_spec.get("options", {})
    
    for opt_name, (enabled, _) in options.items():
        if enabled:
            if opt_name not in available_options:
                raise OptionNotAvailableError(
                    f"Option '{opt_name}' is not defined for language '{lang}'"
                )
            
            opt_spec = available_options[opt_name]
            if not opt_spec.get("available", False):
                raise OptionNotAvailableError(
                    f"Option '{opt_name}' is not available for language '{lang}'"
                )


def apply_placeholders(code: str, params: dict[str, str], defaults: dict[str, str] | None = None) -> str:
    """
    Apply placeholder substitutions to generated code.
    
    Placeholders in code like {classname}, {funname}, {args} are replaced
    with values from params or defaults.
    """
    if defaults is None:
        defaults = {
            "classname": "HelloWorld",
            "interfacename": "Greeter",
            "funname": "example",
            "methodname": "greet",
            "args": "",
            "typed_args": "",
            "return_type": "None",
            "description": "Example code",
            "filename": "example",
            "arg_docs": "",
            "return_doc": "None",
            "extends": "",
            "extends_clause": "",
        }
    
    result = code
    
    # Merge defaults with params (params override defaults)
    all_params = {**defaults, **params}
    
    # Handle extends_clause: if extends is set, format the clause
    if all_params.get("extends") and not all_params.get("extends_clause"):
        all_params["extends_clause"] = f" : public {all_params['extends']}"
    
    # Replace all placeholders
    for key, value in all_params.items():
        result = result.replace(f"{{{key}}}", value)
    
    return result


def _first_nonempty(levels: dict[str, str]) -> str:
    """Return the first non-empty level value, preferring level '1', then by key order."""
    # Prefer '1' as the minimal meaningful level
    if "1" in levels and levels["1"]:
        return levels["1"]
    for v in levels.values():
        if v:
            return v
    return ""


def select_level(
    levels: dict[str, str],
    requested_level: str,
    has_types: bool = False
) -> str:
    """
    Select the appropriate level from available levels.

    When the requested level is the implicit default ("0") and level 0 is
    empty, fall through to the first non-empty level so that options like
    `doc` and `comment` work sensibly without requiring `=1` or `=max`.
    """
    available = list(levels.keys())

    # If types requested and types level exists, use it
    if has_types and "types" in available:
        return levels["types"]

    # Handle special level values
    if requested_level == "rand":
        return levels[random.choice(available)]

    if requested_level == "max":
        if "max" in available:
            return levels["max"]
        numeric = [l for l in available if l.isdigit()]
        if numeric:
            return levels[max(numeric, key=int)]
        return levels[available[-1]]

    # Try exact match
    if requested_level in available:
        content = levels[requested_level]
        # If the user accepted the default "0" and it's empty, pick first non-empty
        if not content and requested_level == "0":
            return _first_nonempty(levels)
        return content

    # Try to find closest numeric level
    try:
        requested = int(requested_level)
        numeric = [l for l in available if l.isdigit()]
        if numeric:
            valid = [l for l in numeric if int(l) <= requested]
            if valid:
                return levels[max(valid, key=int)]
            return levels[min(numeric, key=int)]
    except ValueError:
        pass

    # Default to level 0 or first available, skipping empty
    result = levels.get("0", levels[available[0]])
    if not result:
        return _first_nonempty(levels)
    return result


def generate_code(
    lang: str,
    template: str,
    lang_spec: dict[str, Any],
    options: dict[str, tuple[bool, str]],
    params: dict[str, str] | None = None
) -> str:
    """Generate code based on language spec, template, and options."""
    templates = lang_spec.get("templates", {})
    
    if template not in templates:
        available = ", ".join(templates.keys())
        raise ValueError(f"Template '{template}' not found for '{lang}'. Available: {available}")
    
    template_spec = templates[template]
    available_options = lang_spec.get("options", {})
    params = params or {}
    
    # Check if +types is enabled
    has_types = "types" in options and options["types"][0]
    
    # Start building output
    parts = []
    
    # Add includes if available and enabled (for C)
    if "include" in options and options["include"][0]:
        _, level = options["include"]
        include_spec = available_options.get("include", {})
        if include_spec.get("available", False):
            levels = include_spec.get("levels", {})
            if levels:
                content = select_level(levels, level, has_types)
                if content:
                    parts.append(content)
    
    # Add doc if enabled (goes at top)
    if "doc" in options and options["doc"][0]:
        _, level = options["doc"]
        doc_spec = available_options.get("doc", {})
        if doc_spec.get("available", False):
            levels = doc_spec.get("levels", {})
            if levels:
                content = select_level(levels, level, has_types)
                if content:
                    parts.append(content)
    
    # Add comment if enabled
    if "comment" in options and options["comment"][0]:
        _, level = options["comment"]
        comment_spec = available_options.get("comment", {})
        if comment_spec.get("available", False):
            levels = comment_spec.get("levels", {})
            if levels:
                content = select_level(levels, level, has_types)
                if content:
                    parts.append(content)
    
    # Add interface if enabled
    if "interface" in options and options["interface"][0]:
        _, level = options["interface"]
        interface_spec = available_options.get("interface", {})
        if interface_spec.get("available", False):
            levels = interface_spec.get("levels", {})
            if levels:
                content = select_level(levels, level, has_types)
                parts.append(content)
    
    # Handle +fun option (generate function)
    if "fun" in options and options["fun"][0]:
        _, level = options["fun"]
        fun_spec = available_options.get("fun", {})
        if fun_spec.get("available", False):
            levels = fun_spec.get("levels", {})
            if levels:
                content = select_level(levels, level, has_types)
                parts.append(content)
        else:
            # Fall back to template fun if it exists
            if "levels" in template_spec:
                content = select_level(template_spec["levels"], level, has_types)
                parts.append(content)
    # Add class if enabled
    elif "class" in options and options["class"][0]:
        _, level = options["class"]
        class_spec = available_options.get("class", {})
        if class_spec.get("available", False):
            levels = class_spec.get("levels", {})
            if levels:
                content = select_level(levels, level, has_types)
                parts.append(content)
            elif "base" in template_spec:
                parts.append(template_spec["base"])
        elif "base" in template_spec:
            parts.append(template_spec["base"])
    elif "interface" in options and options["interface"][0]:
        # Interface was already added above, don't add base template
        pass
    else:
        # No class, fun, or interface specified - use base template or template levels
        class_spec = available_options.get("class", {})
        if class_spec.get("required", False):
            raise RequiredOptionError(
                f"Option 'class' is required for language '{lang}' but was not enabled. "
                f"Use +class to enable it."
            )
        
        # Check if template has levels (for fun template)
        if "levels" in template_spec:
            level = "0"
            if has_types and "types" in template_spec["levels"]:
                level = "types"
            content = select_level(template_spec["levels"], level, has_types)
            parts.append(content)
        elif "base" in template_spec:
            parts.append(template_spec["base"])
    
    # Join parts and apply placeholder substitutions
    result = "\n\n".join(p for p in parts if p)
    result = apply_placeholders(result, params)
    
    return result


def get_buildtool(lang_spec: dict[str, Any]) -> str:
    """Get the build tool for a language."""
    return lang_spec.get("buildtool", "unknown")


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="mkexample",
        description="Generate code examples for various programming languages.",
        epilog="""
Examples:
  %(prog)s python helloworld -o hello.py
  %(prog)s cpp class
  %(prog)s cpp class=max comment
  %(prog)s java class doc=max classname=MyApp
  %(prog)s python fun classname=Greeter
  %(prog)s c buildtool

Items (positional after lang):
  class           enable option at minimal level
  class=max       enable option at specified level (0, 1, max, rand)
  classname=Foo   named parameter (value is not a level)
  helloworld      explicit template name
""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "lang",
        nargs="?",
        help="Programming language (e.g., python, rust, c, java, cpp)"
    )

    parser.add_argument(
        "items",
        nargs="*",
        help="What to generate: option names, option=level, or named params"
    )

    parser.add_argument(
        "-o", "--output",
        help="Output file path. If not specified, prints to stdout."
    )

    parser.add_argument(
        "--specs",
        type=Path,
        help="Path to custom language specs directory (default: lang_specs/)"
    )

    parser.add_argument(
        "--list-langs",
        action="store_true",
        help="List available languages and exit"
    )

    parser.add_argument(
        "--list-options",
        action="store_true",
        help="List available options for the specified language"
    )

    return parser


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    try:
        # Load language specs
        specs = load_lang_specs(args.specs)

        # Handle --list-langs
        if args.list_langs:
            print("Available languages:")
            for lang, spec in specs.items():
                ext  = spec.get("extension", "?")
                tool = spec.get("buildtool", "?")
                print(f"  {lang} (.{ext}) - build tool: {tool}")
            return 0

        # Require language
        if not args.lang:
            parser.print_help()
            return 0
        lang = args.lang.lower()
        if lang not in specs:
            available = ", ".join(specs.keys())
            print(f"Error: Unknown language '{lang}'. Available: {available}", file=sys.stderr)
            return 1

        lang_spec = specs[lang]

        # Handle --list-options
        if args.list_options:
            print(f"Available options for '{lang}':")
            for opt_name, opt_spec in lang_spec.get("options", {}).items():
                available = opt_spec.get("available", False)
                required  = opt_spec.get("required", False)
                levels    = list(opt_spec.get("levels", {}).keys())
                status = "\u2713" if available else "\u2717"
                req    = " (REQUIRED)" if required else ""
                lvls   = f" [levels: {', '.join(levels)}]" if levels else ""
                print(f"  {status} {opt_name}{req}{lvls}")
            return 0

        # Parse items into template + options + params
        template, options, params = parse_items(args.items, lang_spec)

        # buildtool shortcut
        if template == "buildtool":
            print(get_buildtool(lang_spec))
            return 0

        # Validate options
        validate_options(lang, lang_spec, options)

        # Infer template if not explicit
        if not template:
            if "fun" in options:
                template = "fun"
            else:
                template = "helloworld"

        # Generate code
        code = generate_code(lang, template, lang_spec, options, params)

        # Output
        if args.output:
            output_path = Path(args.output)
            if not output_path.suffix:
                ext = lang_spec.get("extension", "txt")
                output_path = output_path.with_suffix(f".{ext}")
            output_path.write_text(code + "\n")
            print(f"Generated: {output_path}")
        else:
            print(code)

        return 0

    except OptionNotAvailableError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except RequiredOptionError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
