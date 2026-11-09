"""Independent synthetic verification; never reads video measurements to set loads."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import subprocess
import sys
import time
import numpy as np
from analysis.localized_fem.solver import TractionSolver
from analysis.localized_fem.traction import Rectangle,integrate_rectangle
from analysis.localized_fem.simulate import export,write_json

ROOT=Path(__file__).resolve().parents[2]


def protected_hashes():
    paths=[]
    for directory in ['analysis','Videos','docs','demo']:
        paths.extend(p for p in (ROOT/directory).rglob('*') if p.is_file() and 'localized_fem' not in p.parts and '__pycache__' not in p.parts and p.suffix!='.pyc')
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():parser.error('Refusing existing output directory')
    args.output.mkdir(parents=True);before=protected_hashes()
    write_json(args.output/'protected_before.json',before)
    write_json(args.output/'protocol.json',{'patch_m':[.0365,.025,.02,.03],'force_N':.3,'meshes':[[2,2,1],[4,4,2],[6,6,3]],'selection':'Synthetic central rectangle and sub-newton loads; no experimental response used','force_tolerance_N':5e-8,'load_step':.25,'max_iterations_per_step':600})
    tests=[]
    for name,command in [('localized',[sys.executable,'-B','-m','unittest','analysis.localized_fem.test_localized','-v']),('regression',[sys.executable,'-B','demo/check.py']),('baseline',[sys.executable,'-B','docs/check_baseline.py']),('experimental_analysis',[sys.executable,'-B','-m','unittest','discover','-s','analysis/localized_experiments','-p','test_analysis.py'])]:
        start=time.perf_counter();result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
        (args.output/f'{name}.log').write_text(result.stdout+result.stderr,encoding='utf-8')
        tests.append(dict(name=name,exit_code=result.returncode,runtime_s=time.perf_counter()-start))
    write_json(args.output/'test_results.json',tests)
    # Intentionally impossible iteration budget: exercise the failure path,
    # without exporting a non-equilibrium state as solved geometry.
    failure_problem=TractionSolver(max_iterations=1);failure_start=time.perf_counter()
    try:
        failure_problem.solve_patch(Rectangle(.0365,.025,.02,.03),.3,load_step=1,min_load_step=1)
    except Exception as exc:
        write_json(args.output/'expected_failure.json',{'expected_failure':True,'reason':str(exc),'runtime_s':time.perf_counter()-failure_start,'attempts':getattr(exc,'attempts',[]),'force_tolerance_N':failure_problem.force_tolerance,'max_iterations':1,'nodes':len(failure_problem.X),'free_dofs':len(failure_problem.free),'tetrahedra':len(failure_problem.cells)})
    else:raise AssertionError('Deliberate iteration-budget failure unexpectedly converged')
    rows=[];integration=[]
    scenarios=[('coarse_0p1',(2,2,1),.1,.0365),('coarse_0p3',(2,2,1),.3,.0365),('coarse_0p6',(2,2,1),.6,.0365),('left_0p3',(2,2,1),.3,.01825),('right_0p3',(2,2,1),.3,.05475),('medium_0p3',(4,4,2),.3,.0365),('fine_0p3',(6,6,3),.3,.0365)]
    for name,mesh,force,cx in scenarios:
        print('Solving',name,flush=True);s=TractionSolver(mesh);patch=Rectangle(cx,.025,.02,.03);start=time.perf_counter()
        load=integrate_rectangle(s.X,s.top_faces,patch,force)
        integration.append(dict(case=name,area_m2=load.area_m2,total_downward_N=-load.nodal_forces_N[:,2].sum(),centroid_x_m=load.centroid_xy_m[0],centroid_y_m=load.centroid_xy_m[1],moment_x_Nm=np.cross(s.X,load.nodal_forces_N).sum(axis=0)[0],moment_y_Nm=np.cross(s.X,load.nodal_forces_N).sum(axis=0)[1]))
        try:
            state=s.solve_patch(patch,force);d=export(s,state,args.output/name)
            assert d['free_residual_N']<=s.force_tolerance
            assert d['force_balance_N']<=len(s.X)*s.force_tolerance
            assert d['moment_balance_Nm']<=len(s.X)*s.force_tolerance*.1
            assert all(h['min_J']>0 for h in state.history)
            rows.append(dict(case=name,mesh='x'.join(map(str,mesh)),status='converged',**d))
        except Exception as exc:
            rows.append(dict(case=name,mesh='x'.join(map(str,mesh)),status='failed',reason=str(exc),runtime_s=time.perf_counter()-start))
        write_json(args.output/'cases.json',rows)
    for name,records in [('cases',rows),('integration',integration)]:
        keys=list(dict.fromkeys(k for row in records for k in row))
        with (args.output/f'{name}.csv').open('w',newline='',encoding='utf-8') as handle:
            writer=csv.DictWriter(handle,fieldnames=keys);writer.writeheader();writer.writerows(records)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    refinement=[r for r in rows if r['case'] in ['coarse_0p3','medium_0p3','fine_0p3'] and r['status']=='converged']
    fig,axes=plt.subplots(2,3,figsize=(12,7))
    for ax,key in zip(axes.ravel(),['max_downward_mm','loaded_mean_downward_mm','unloaded_mean_downward_mm','energy_J','support_reaction_N','min_J']):
        ax.plot([r['tetrahedra'] for r in refinement],[r[key] for r in refinement],'o-');ax.set(xlabel='Tetrahedra',ylabel=key.replace('_',' '));ax.grid(alpha=.3)
        if key=='support_reaction_N':ax.set_ylim(.295,.305);ax.ticklabel_format(useOffset=False)
    fig.suptitle('Synthetic 0.3 N, 20 x 30 mm centered dead traction; no extrapolated limit');fig.tight_layout();fig.savefig(args.output/'refinement.png',dpi=160);plt.close(fig)
    after=protected_hashes();write_json(args.output/'integrity.json',{'protected_file_count':len(before),'unchanged':before==after,'changed':[k for k in before if after.get(k)!=before[k]],'added':sorted(set(after)-set(before))})
    write_json(args.output/'summary.json',{'tests_passed':all(t['exit_code']==0 for t in tests),'all_scenarios_converged':all(r['status']=='converged' for r in rows),'protected_files_unchanged':before==after})
    if before!=after or any(t['exit_code'] for t in tests) or any(r['status']!='converged' for r in rows):raise SystemExit(1)


if __name__=='__main__':main()
