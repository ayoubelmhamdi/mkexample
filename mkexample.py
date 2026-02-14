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


def load_lang_specs(specs_path: Path | None = None) -> dict[str, Any]:
    """Load language specifications from JSON file."""
    if specs_path is None:
        specs_path = Path(__file__).parent / "lang_specs.json"
    
    if not specs_path.exists():
        raise FileNotFoundError(f"Language specs file not found: {specs_path}")
    
    with open(specs_path, "r") as f:
        return json.load(f)


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


def parse_options(args: list[str]) -> tuple[dict[str, tuple[bool, str]], dict[str, str]]:
    """
    Parse option arguments like +class, -interface, +classlevel=2, -classname=Foo.
    
    Returns:
        options: dict of option_name -> (enabled, level)
        params: dict of param_name -> value (e.g., classname -> Foo)
    """
    options = {}
    params = {}
    
    for arg in args:
        if not arg.startswith('+') and not arg.startswith('-'):
            continue
        
        enabled = arg.startswith('+')
        opt_part = arg[1:]  # Remove +/-
        
        # Check for value specification
        if '=' in opt_part:
            opt_name, value = opt_part.split('=', 1)
            
            # Handle level options like "classlevel" -> "class"
            if opt_name.endswith('level'):
                opt_name = opt_name[:-5]  # Remove 'level' suffix
                options[opt_name] = (enabled, value)
            # Handle name/value params like "classname", "interfacename"
            elif opt_name.endswith('name'):
                param_key = opt_name  # Keep as "classname", "interfacename", etc.
                params[param_key] = value
            else:
                # Generic value param
                params[opt_name] = value
        else:
            opt_name = opt_part
            options[opt_name] = (enabled, "0")  # Default to simplest level
    
    return options, params


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


def select_level(
    levels: dict[str, str],
    requested_level: str,
    has_types: bool = False
) -> str:
    """
    Select the appropriate level from available levels.
    
    If +types is enabled and a 'types' level exists, prefer it.
    Otherwise fall back to numeric levels or 'max'.
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
        # Fall back to highest numeric level
        numeric = [l for l in available if l.isdigit()]
        if numeric:
            return levels[max(numeric, key=int)]
        return levels[available[-1]]
    
    # Try exact match
    if requested_level in available:
        return levels[requested_level]
    
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
    
    # Default to level 0 or first available
    return levels.get("0", levels[available[0]])


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
  %(prog)s rust helloworld +class -interface +comment
  %(prog)s java helloworld +class +classlevel=max +doc
  %(prog)s c buildtool
  %(prog)s python helloworld +classlevel=rand

Options format:
  +option      Enable option (e.g., +class, +comment)
  -option      Disable option (e.g., -interface)
  +optionlevel=N   Set complexity level (0, 1, 2, max, rand)
""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "lang",
        nargs="?",
        help="Programming language (e.g., python, rust, c, java)"
    )
    
    parser.add_argument(
        "template",
        nargs="?",
        help="Template name (e.g., helloworld) or 'buildtool' to show build tool"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Output file path. If not specified, prints to stdout."
    )
    
    parser.add_argument(
        "--specs",
        type=Path,
        help="Path to custom language specs JSON file"
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
    args, extra_args = parser.parse_known_args()
    
    try:
        # Load language specs
        specs = load_lang_specs(args.specs)
        
        # Handle --list-langs
        if args.list_langs:
            print("Available languages:")
            for lang, spec in specs.items():
                ext = spec.get("extension", "?")
                tool = spec.get("buildtool", "?")
                print(f"  {lang} (.{ext}) - build tool: {tool}")
            return 0
        
        # Validate language
        lang = args.lang.lower()
        if lang not in specs:
            available = ", ".join(specs.keys())
            print(f"Error: Unknown language '{lang}'. Available: {available}", file=sys.stderr)
            return 1
        
        lang_spec = specs[lang]
        
        # Handle --list-options
        if args.list_options:
            print(f"Available options for '{lang}':")
            options = lang_spec.get("options", {})
            for opt_name, opt_spec in options.items():
                available = opt_spec.get("available", False)
                required = opt_spec.get("required", False)
                levels = list(opt_spec.get("levels", {}).keys())
                
                status = "✓" if available else "✗"
                req = " (REQUIRED)" if required else ""
                lvls = f" [levels: {', '.join(levels)}]" if levels else ""
                
                print(f"  {status} {opt_name}{req}{lvls}")
            return 0
        
        # Handle buildtool special case
        if args.template and args.template.lower() == "buildtool":
            tool = get_buildtool(lang_spec)
            print(tool)
            return 0
        
        # Check if template looks like an option (starts with + or -)
        # If so, treat it as an option and infer template from options
        template = args.template
        all_extra_args = list(extra_args)
        
        if template and (template.startswith('+') or template.startswith('-')):
            # Move template to extra_args
            all_extra_args.insert(0, template)
            template = None
        
        # Parse and validate options
        options, params = parse_options(all_extra_args)
        validate_options(lang, lang_spec, options)
        
        # If no template specified, infer from options
        if not template:
            if "fun" in options and options["fun"][0]:
                template = "fun"
            elif "class" in options and options["class"][0]:
                template = "helloworld"  # Default template for class
            elif "interface" in options and options["interface"][0]:
                template = "helloworld"  # Default template for interface
            else:
                template = "helloworld"  # Ultimate default
        
        # Generate code
        code = generate_code(lang, template, lang_spec, options, params)
        
        # Output
        if args.output:
            output_path = Path(args.output)
            # Auto-add extension if not provided
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
