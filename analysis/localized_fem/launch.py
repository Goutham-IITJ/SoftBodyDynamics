"""Run the unchanged CLI, explain output locations, and optionally open a viewer."""
import argparse
import subprocess
import sys
import webbrowser
from pathlib import Path
from analysis.localized_fem.view_results import build_view


def main():
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--open',action='store_true');parser.add_argument('--output',type=Path)
    args,_=parser.parse_known_args()
    forwarded=[a for a in sys.argv[1:] if a!='--open']
    result=subprocess.run([sys.executable,'-B','-m','analysis.localized_fem.simulator',*forwarded])
    if result.returncode:raise SystemExit(result.returncode)
    if args.output is None:return  # Original CLI help, not a simulation run.
    viewer=build_view(args.output)
    print(f'\nSUCCESS: solved FEM result saved to {args.output.resolve()}')
    print(f'VIEW MODEL: {viewer}')
    print(f'FINAL IMAGE: {args.output.resolve() / "deformed.png"}')
    print('The browser viewer rotates the solved mesh and shows force, displacement colors and saved states.')
    if args.open:
        webbrowser.open(viewer.as_uri())
        print('Requested opening in your default browser. If no window appears, double-click viewer.html.')
    else:print('Double-click viewer.html, or add --open to this launcher command.')


if __name__=='__main__':main()
