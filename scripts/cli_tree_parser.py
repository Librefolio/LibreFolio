#!/usr/bin/env python3
"""
Tree Parser Library for LibreFolio CLI

Provides enhanced argparse classes that display command trees and
better formatted help messages.

Usage:
    from scripts.cli_tree_parser import TreeParser, CustomFormatter, format_help

    parser = TreeParser(
        description="My CLI",
        formatter_class=format_help
    )

Features:
    - TreeParser: Automatically shows command tree after help
    - CustomFormatter: Better option formatting (combines short/long options)
    - subparser_tree(): Generate ASCII tree of all subcommands
    - format_help: Pre-configured formatter factory

Author: LibreFolio Contributors
"""

import argparse
import shutil


def get_term_width(min_width: int = 60) -> int:
    """Get terminal width with a minimum fallback."""
    try:
        return max(shutil.get_terminal_size().columns, min_width)
    except Exception:
        return min_width


def format_help(prog: str) -> 'CustomFormatter':
    """
    Factory function for CustomFormatter with good defaults.

    Usage:
        parser = argparse.ArgumentParser(formatter_class=format_help)
    """
    return CustomFormatter(prog, max_help_position=50, width=get_term_width(60))


class CustomFormatter(argparse.RawDescriptionHelpFormatter):
    """
    Enhanced help formatter that:
    - Combines short and long options on same line (-s, --long ARGS)
    - Better indentation for subactions
    - Preserves description formatting (RawDescription)
    """

    def add_argument(self, action):
        if action.help is not argparse.SUPPRESS:
            # Find all invocations
            get_invocation = self._format_action_invocation
            invocations = [get_invocation(action)]
            current_indent = self._current_indent

            for subaction in self._iter_indented_subactions(action):
                # Compensate for the indent that will be added
                indent_chg = self._current_indent - current_indent
                added_indent = 'x' * indent_chg
                invocations.append(added_indent + get_invocation(subaction))

            # Update the maximum item length
            invocation_length = max([len(s) for s in invocations])
            action_length = invocation_length + self._current_indent
            self._action_max_length = max(self._action_max_length, action_length)

            # Add the item to the list
            self._add_item(self._format_action, [action])

    def _format_action_invocation(self, action):
        if not action.option_strings:
            metavar, = self._metavar_formatter(action, action.dest)(1)
            return metavar
        else:
            parts = []

            # If the Optional doesn't take a value, format is: -s, --long
            if action.nargs == 0:
                parts.extend(action.option_strings)
            # If the Optional takes a value, format is: -s, --long ARGS
            else:
                default = action.dest.upper()
                args_string = self._format_args(action, default)
                for option_string in action.option_strings:
                    parts.append('%s' % option_string)
                parts[-1] += ' %s' % args_string

            return ', '.join(parts)


class TreeParser(argparse.ArgumentParser):
    """
    ArgumentParser that automatically displays command tree after help.

    Usage:
        parser = TreeParser(
            description="My CLI",
            formatter_class=format_help
        )
    """

    def __init__(self, *args, show_tree: bool = True, **kwargs):
        """
        Args:
            show_tree: If True, display command tree after help (default: True)
            *args, **kwargs: Passed to ArgumentParser
        """
        self._show_tree = show_tree
        super().__init__(*args, **kwargs)

    def print_help(self, file=None):
        super().print_help(file)
        if self._show_tree:
            tree = subparser_tree(self)
            if tree.strip():
                print(f"\nCommand tree:\n{tree}", file=file)


def _option_strings_formatter(parser: argparse.ArgumentParser) -> str:
    """
    Format option strings for a parser (used in tree display).

    Returns a string like: "[--verbose] [-h] FILE"
    """
    ret_str = ""

    if not parser._optionals:
        return ret_str

    options_str = []
    positional_str = []

    for action in parser._optionals._actions:
        # Skip subparsers (they're shown in tree)
        if isinstance(action, argparse._SubParsersAction):
            continue

        pars = []

        # Add option selector (short form priority)
        if action.option_strings:
            pars.append(f"{action.option_strings[0]}")

        # Add metavar
        if action.metavar:
            if isinstance(action.metavar, tuple):
                meta_join = "...".join(action.metavar)
                pars.append(meta_join)
            else:
                pars.append(f"{action.metavar}")
        elif (action.nargs or action.required) and action.dest:
            pars.append(f"{action.dest.upper()}")

        # Format and categorize
        if pars:
            par_str = " ".join(pars)
            par_str = f"{par_str}" if action.required else f"[{par_str}]"

            if action.option_strings:
                options_str.append(par_str)
            else:
                positional_str.append(par_str)

    # Build output string
    if positional_str:
        positional_str.sort()
        ret_str += " " + " ".join(positional_str)

    if options_str:
        options_str.sort()
        ret_str += " " + " ".join(options_str)

    return ret_str


def subparser_tree(
    parser: argparse.ArgumentParser,
    start: str = "",
    down: tuple = ("│", " "),
    leaf: tuple = ("├", "╰"),
    item: tuple = ("┬", "─", "╴"),
    ind_inc: int = 1,
    _is_root: bool = True
    ) -> str:
    """
    Generate ASCII tree representation of parser and all subparsers.

    Args:
        parser: The ArgumentParser to visualize
        start: Current line prefix (for recursion)
        down: Characters for vertical lines (continuing, last)
        leaf: Characters for branch points (continuing, last)
        item: Characters for items (has children, line, end)
        ind_inc: Indentation increment
        _is_root: Internal flag for root node

    Returns:
        ASCII tree string

    Example output:
        dev.py [-h]
        ├─┬╴server [-h]
        ├─┬╴db [-h]
        │ ├──╴check [-h] [PATH]
        │ ├──╴upgrade [-h]
        │ ╰──╴migrate [-h] MESSAGE
        ├─┬╴test [-h] [-v]
        │ ├──╴api [-h]
        │ ╰──╴all [-h]
        ╰──╴fe [-h]
    """
    # Find all subparser actions
    subparsers_actions = [
        action for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
        ]

    # Root node shows prog name
    str_out = f"{parser.prog}{_option_strings_formatter(parser)}\n" if _is_root else ""

    for subparsers_action in subparsers_actions:
        choices = list(subparsers_action.choices.items())

        for i, (choice, subparser) in enumerate(choices):
            is_last = (i == len(choices) - 1)

            # Build the branch prefix
            branch_char = leaf[1] if is_last else leaf[0]
            str_out += start + branch_char + item[1] * ind_inc

            # Recurse into subparser
            child_prefix = start + (down[1] if is_last else down[0]) + " " * ind_inc
            ret_string = subparser_tree(
                subparser,
                start=child_prefix,
                down=down,
                leaf=leaf,
                item=item,
                ind_inc=ind_inc,
                _is_root=False
                )

            # Add connector if has children
            str_out += item[0] if ret_string else item[1]
            str_out += item[2] + choice + _option_strings_formatter(subparser) + "\n"
            str_out += ret_string

    return str_out


# Convenience aliases
tree_parser = TreeParser
custom_formatter = CustomFormatter
