"""`python3 -m pptools.pprun run PROJECT RUN`: how `pptools.pprun.runner.Runs` starts a run"""
import sys
from pptools.pprun.runner import main
sys.exit(main(sys.argv[1:]))
