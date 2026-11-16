"""Command line interface of `ppoutput`

Syntax
------

    ppoutput [serve] [-P PROJECT] [-r ROOT] [-p PORT] [--host HOST] [--no-browser] [-d] [-v] [-w] [--version]

Opens the `ppoutput` page (`/ppoutput/`) of the pptools server in a browser,
starting the server if none is running on the port (default 8040) and
reusing it otherwise. The options are those of `pptools serve`; see
`pptools`. `ppoutput` is planned: the page lists the planned features and the
files in the project's folder.

Examples
--------

    ppoutput
    ppoutput -P wecc240
    ppoutput -P wecc240 --root ~/studies --no-browser
"""

import sys

from pptools.cli import tool_main

def main(argv:list[str]|None=None) -> int:
    """Command line entry point of `ppoutput` (see `pptools.cli.tool_main`)"""
    return tool_main("ppoutput",argv)

if __name__ == "__main__":
    sys.exit(main())
