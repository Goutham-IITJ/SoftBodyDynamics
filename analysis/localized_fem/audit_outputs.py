"""Re-evaluate saved equilibria without repeating nonlinear solves."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from analysis.localized_fem.solver import TractionSolver
from analysis.localized_fem.traction import Rectangle,integrate_rectangle


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path);args=parser.parse_args()
    rows=json.loads((args.directory/'cases.json').read_text());checks=[]
    for row in rows:
        assert row['status']=='converged'
        s=TractionSolver(tuple(map(int,row['mesh'].split('x'))));folder=args.directory/row['case']
        data=np.loadtxt(folder/'nodes.csv',delimiter=',',skiprows=1);x=data[:,4:7];f=data[:,7:10]
        np.testing.assert_allclose(data[:,1:4],s.X,atol=1e-16)
        np.testing.assert_array_equal(np.loadtxt(folder/'tetrahedra.csv',delimiter=',',skiprows=1,dtype=int),s.cells)
        q=((x-s.X)/s.H).ravel()[s.free];potential,g,assembled,reconstructed,residual=s.objective(q,0,f)
        np.testing.assert_allclose(reconstructed,x,atol=1e-16)
        centroid=row['centroid_xy_m'];load=integrate_rectangle(s.X,s.top_faces,Rectangle(*centroid,.02,.03),row['force_N'])
        np.testing.assert_allclose(f,load.nodal_forces_N,atol=1e-14)
        reactions=np.loadtxt(folder/'reactions.csv',delimiter=',',skiprows=1)
        expected=np.zeros_like(s.X);expected.ravel()[s.fixed]=residual.ravel()[s.fixed]
        np.testing.assert_allclose(reactions,expected,atol=1e-13)
        force_balance=np.max(abs((reactions+f).sum(axis=0)))
        moment_balance=np.max(abs(np.cross(x,reactions+f).sum(axis=0)))
        free_residual=np.max(abs(residual.ravel()[s.free]));min_J=min(e.J for e in assembled.elements)
        assert free_residual<=s.force_tolerance
        assert force_balance<=len(s.X)*s.force_tolerance
        assert moment_balance<=len(s.X)*s.force_tolerance*.1
        assert min_J>0
        np.testing.assert_allclose(assembled.energy,row['energy_J'],rtol=1e-10,atol=1e-15)
        np.testing.assert_allclose(potential*s.scale,row['potential_J'],rtol=1e-10,atol=1e-15)
        with (folder/'history.csv').open() as handle:assert all(float(h['min_J'])>0 for h in csv.DictReader(handle))
        checks.append(dict(case=row['case'],free_residual_N=float(free_residual),force_balance_N=float(force_balance),moment_balance_Nm=float(moment_balance),min_J=float(min_J)))
    print(json.dumps({'status':'PASS','re_evaluated_saved_equilibria':checks},indent=2))


if __name__=='__main__':main()
