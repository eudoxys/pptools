"""Command line interface of `ppdata`

Syntax
------

    ppdata [serve] [-P PROJECT] [-r ROOT] [-p PORT] [--host HOST] [--no-browser] [-d] [-v] [-w] [--version]

Opens the `ppdata` page (`/ppdata/`) of the pptools server in a browser,
starting the server if none is running on the port (default 8040) and
reusing it otherwise. The options are those of `pptools serve`; see
`pptools`. `ppdata` is planned: the page lists the planned features and the
files in the project's folder.

Examples
--------

    ppdata
    ppdata -P wecc240
    ppdata -P wecc240 --root ~/studies --no-browser
"""

import sys

from pptools.cli import tool_main

def main(argv:list[str]|None=None) -> int:
    """Command line entry point of `ppdata` (see `pptools.cli.tool_main`)"""
    return tool_main("ppdata",argv)

if __name__ == "__main__":
    sys.exit(main())
