import inspect
from functools import wraps


def merge(section: str | None = None):
    """
    Decorator to merge the func call arguments/options of Typer with config defaults provided via TOML tables.
    The precedence is as follows:
        - Explicit CLI Arguments: (i.e. surge <cmd> -<option-flag> --<option-name>)

        - Configuration Data for a given section (
            found in TOML table under table, i.e.:
            [table-name]
            <option> = <value>

            # Provided as a KWArg for Python in config.py
        )

        - Typer function default signature (
            i.e.
            def name(option: typer.Option('-x', '--flag') = <value>, ...):
        )
    """

    def decorator(func):
        orig_sig = inspect.signature(func)
        declared_defaults = {
            name: param.default
            for name, param in orig_sig.parameters.items()
            if param.default is not inspect._empty
        }

        # Modded signature with defaults set to None for Typer to see as optional; leaves *args, **kwargs, and positional-only params default
        new_params = []
        for param in orig_sig.parameters.values():
            if param.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
                inspect.Parameter.POSITIONAL_ONLY,
            ):
                new_params.append(param)
            else:
                new_params.append(param.replace(default=None))
        new_sig = orig_sig.replace(parameters=new_params)

        # Actual wrapper lets go
        @wraps(func)
        def wrapper(*args, **kwargs):
            config_data = func.__globals__.get("config_data", {})

            section_key = section or func.__name__
            config_section = (
                config_data.get(section_key, {})
                if isinstance(config_data, dict)
                else {}
            )

            bound = orig_sig.bind_partial(*args, **kwargs)
            final_args = {}

            for name in orig_sig.parameters:
                val = bound.arguments.get(name, None)

                if val is not None:  # Explicit cli option
                    final_args[name] = val
                    continue

                if name in config_section:  # Config option
                    final_args[name] = config_section[name]
                    continue

                if name in declared_defaults:  # Default fallback
                    final_args[name] = declared_defaults[name]
                else:
                    final_args[name] = None

            return func(**final_args)

        wrapper.__signature__ = new_sig
        return wrapper

    return decorator
