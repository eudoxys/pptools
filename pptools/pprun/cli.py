"""Command line interface of `pprun`

Syntax
------

    pprun [serve] [-P PROJECT] [-r ROOT] [-p PORT] [--host HOST] [--no-browser] [-d] [-v] [-w] [--version]

Opens the `pprun` page (`/pprun/`) of the pptools server in a browser,
starting the server if none is running on the port (default 8040) and
reusing it otherwise. The options are those of `pptools serve`; see
`pptools`. The page is described in `pptools.pprun`.

Examples
--------

    pprun
    pprun -P wecc240
    pprun -P wecc240 --root ~/studies --no-browser
"""

import sys

from pptools.cli import tool_main

def main(argv:list[str]|None=None) -> int:
    """Command line entry point of `pprun` (see `pptools.cli.tool_main`)"""
    return tool_main("pprun",argv)

if __name__ == "__main__":
    sys.exit(main())
