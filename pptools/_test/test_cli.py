"""Tests for `pptools.cli` (fast, no network)"""

from pptools import main, __version__

def test_version(capsys):
    try:
        main(["--version"])
    except SystemExit as err:
        assert err.code == 0
    assert capsys.readouterr().out.strip() == f"pptools {__version__}"

def test_new_and_list(tmp_path,capsys):
    root = str(tmp_path)
    assert main(["new","s1","--description","first","-r",root]) == 0
    assert capsys.readouterr().out.strip() == str(tmp_path/"s1")
    assert main(["new","s1","-r",root]) == 1
    assert "ERROR [pptools]" in capsys.readouterr().err
    assert main(["list","-r",root]) == 0
    assert capsys.readouterr().out.strip() == "s1  first"

def test_new_needs_name(tmp_path,capsys):
    assert main(["new","-r",str(tmp_path)]) == 1
    assert "needs a project NAME" in capsys.readouterr().err
