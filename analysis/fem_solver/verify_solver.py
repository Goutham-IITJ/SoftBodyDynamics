"""Stage 3 synthetic verification driver. Writes only fem_solver/verification."""
from pathlib import Path
import sys
if __package__ in (None,''):sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import csv,json,hashlib,platform,time
import numpy as np
from scipy.optimize import brentq
from analysis.material.hyperfoam import Hyperfoam
from analysis.fem_solver.solver import BlockSolver


def table(path,rows):
    with path.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def run():
    here=Path(__file__).resolve().parent;out=here/'verification';out.mkdir(exist_ok=True)
    protected=list((here.parent/'material').rglob('*'))+list((here.parent/'fem').rglob('*'))+list((here.parent/'outputs').rglob('*.csv'))
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    hashes={str(p):sha(p) for p in protected if p.is_file()}
    results=[];histories=[];outer=[];attempts=[];constraints=[];jacobians=[];positions=[]
    t=time.perf_counter()
    for label,alpha,beta in [('primary',10,0),('shape',20,0),('coupled',10,.125)]:
        m=Hyperfoam(2000,alpha,beta)
        for n in [1,2]:
            solver=BlockSolver(m,subdivisions=(n,n,n));meta=dict(scenario=label,alpha=alpha,beta=beta,mu_Pa=2000,subdivisions=n,nodes=len(solver.X),elements=len(solver.cells))
            for dof in solver.fixed:
                node,axis=divmod(dof,3)
                role='table_z' if axis==2 and node in solver.bottom else ('platen_z' if axis==2 else 'rigid_body_anchor')
                constraints.append(dict(scenario=label,subdivisions=n,node=node,axis='xyz'[axis],role=role,reference_coordinate_m=solver.X[node,axis],displacement_rule='-d' if role=='platen_z' else '0'))
            def record(mode,request,r):
                lam=1-r.displacement/solver.H;F,W,P,sigma,tan=m.free_uniaxial(lam)
                analytical_reaction=-np.prod(solver.lengths[:2])*P[2,2]
                analytical_energy=solver.assembly.reference_volume*W
                exact=solver.X@F.T
                full=solver.assembly.evaluate(r.positions,m)
                F_error=max(np.linalg.norm(s.F-F) for s in full.elements)
                lateral=np.ptp(r.positions,axis=0)[:2]/solver.lengths[:2]
                constraint_load=np.zeros_like(solver.X);constraint_load.ravel()[solver.fixed]=r.gradient.ravel()[solver.fixed]
                resultant=np.linalg.norm(constraint_load.sum(axis=0))
                anchor=max(abs(r.gradient[node,axis]) for node,axis in solver.anchors)
                row={**meta,'mode':mode,'request':request,'displacement_m':r.displacement,'reaction_N':r.top_reaction,'bottom_reaction_N':r.bottom_reaction,'analytical_reaction_N':analytical_reaction,'reaction_error_N':r.top_reaction-analytical_reaction,'energy_J':r.energy,'analytical_energy_J':analytical_energy,'energy_relative_error':abs(r.energy-analytical_energy)/max(abs(analytical_energy),1e-15),'lateral_x':lateral[0],'lateral_y':lateral[1],'analytical_lateral':F[0,0],'max_position_error_m':np.max(abs(r.positions-exact)),'F_error':F_error,'free_residual_N':r.free_residual,'constraint_resultant_N':resultant,'anchor_reaction_max_N':anchor,'min_J':r.min_J,'max_J':r.max_J,'analytical_J':np.linalg.det(F),'iterations':r.iterations,'termination':r.termination}
                if mode=='force':
                    root=brentq(lambda l:-np.prod(solver.lengths[:2])*m.free_uniaxial(l)[2][2,2]-request,.35,1)
                    row['analytical_displacement_m']=solver.H*(1-root)
                    row['displacement_error_m']=r.displacement-row['analytical_displacement_m']
                    row['target_balance_error_N']=r.top_reaction-request
                    assert abs(row['displacement_error_m'])<2e-8
                    assert abs(row['target_balance_error_N'])<2e-7
                else:
                    row['analytical_displacement_m']=r.displacement;row['displacement_error_m']=0.;row['target_balance_error_N']=0.
                assert r.termination=='converged_free_force_residual' and r.min_J>0
                assert row['max_position_error_m']<2e-8 and F_error<1e-5
                assert abs(row['reaction_error_N'])<2e-7 and resultant<5e-7 and anchor<2e-7
                assert row['energy_relative_error']<1e-8 and r.free_residual<=1.01e-8
                results.append(row)
                for h in r.history:histories.append({'scenario':label,'subdivisions':n,'mode':mode,'request':request,'platen_displacement_m':r.displacement,**h})
                for e,s in enumerate(full.elements):jacobians.append(dict(scenario=label,subdivisions=n,mode=mode,request=request,element=e,J=s.J))
                if mode=='prescribed' and request==.004:
                    for i,(a,b) in enumerate(zip(solver.X,r.positions)):
                        positions.append(dict(scenario=label,subdivisions=n,node=i,X_m=a[0],Y_m=a[1],Z_m=a[2],x_m=b[0],y_m=b[1],z_m=b[2]))
            previous=None
            for d in [0.,.001,.002,.003,.004]:
                r=solver.solve_displacement(d,start=previous);record('prescribed',d,r);previous=r
            reactions=[];displacements=[]
            for target in [.05,.1,.2,.3]:
                r=solver.solve_force(target);record('force',target,r);reactions.append(r.top_reaction);displacements.append(r.displacement)
            assert np.all(np.diff(displacements)>0) and np.all(np.diff(reactions)>0)
            outer.extend(dict(scenario=label,subdivisions=n,**r) for r in solver.force_history)
            attempts.extend(dict(scenario=label,subdivisions=n,**r) for r in solver.continuation_attempts)
            print(label,n,'verified',flush=True)
    for filename,rows in [('equilibria',results),('iterations',histories),('force_root_history',outer),('continuation_attempts',attempts),('constraints',constraints),('element_jacobians',jacobians),('deformed_nodes',positions)]:table(out/(filename+'.csv'),rows)
    # Compare separately solved resolutions, rather than comparing two imposed affine fields.
    comparison=[]
    for label in ['primary','shape','coupled']:
        for mode,requests in [('prescribed',[0.,.001,.002,.003,.004]),('force',[.05,.1,.2,.3])]:
            for request in requests:
                a,b=[r for r in results if r['scenario']==label and r['mode']==mode and r['request']==request]
                comparison.append(dict(scenario=label,mode=mode,request=request,displacement_difference_m=b['displacement_m']-a['displacement_m'],reaction_difference_N=b['reaction_N']-a['reaction_N'],energy_difference_J=b['energy_J']-a['energy_J']))
    table(out/'mesh_comparison.csv',comparison)
    assert all(sha(Path(p))==h for p,h in hashes.items())
    summary=dict(equilibrium_cases=len(results),all_converged=True,max_free_residual_N=max(r['free_residual_N'] for r in results),max_position_error_m=max(r['max_position_error_m'] for r in results),max_analytical_reaction_error_N=max(abs(r['reaction_error_N']) for r in results),max_energy_relative_error=max(r['energy_relative_error'] for r in results),max_constraint_resultant_N=max(r['constraint_resultant_N'] for r in results),max_force_control_displacement_error_m=max(abs(r['displacement_error_m']) for r in results),max_target_force_error_N=max(abs(r['target_balance_error_N']) for r in results),min_J=min(r['min_J'] for r in results),max_mesh_displacement_difference_m=max(abs(r['displacement_difference_m']) for r in comparison),max_mesh_reaction_difference_N=max(abs(r['reaction_difference_N']) for r in comparison),continuation_retries=sum(r['status']=='failed_retry_smaller_increment' for r in attempts),elapsed_s=time.perf_counter()-t,python=platform.python_version(),protected_files_unchanged=True,protected_sha256=hashes,source_sha256={p.name:sha(p) for p in here.glob('*.py')})
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(2,2,figsize=(11,8))
    for label,alpha,beta in [('primary',10,0),('shape',20,0),('coupled',10,.125)]:
        material=Hyperfoam(2000,alpha,beta);compression=np.linspace(0,.006,100)
        axs[0,0].plot(compression*1000,[-.0006*material.free_uniaxial(1-d/.01)[2][2,2] for d in compression],label=label+' analytic')
        for n,marker in [(1,'o'),(2,'x')]:
            rows=[r for r in results if r['scenario']==label and r['subdivisions']==n]
            axs[0,0].scatter([r['displacement_m']*1000 for r in rows],[r['reaction_N'] for r in rows],marker=marker,s=18)
            axs[0,1].plot([r['displacement_m']*1000 for r in rows],[r['lateral_x'] for r in rows],marker, label=f'{label}, n={n}')
            axs[1,0].plot([r['displacement_m']*1000 for r in rows],[abs(r['reaction_N']-r['bottom_reaction_N']) for r in rows],marker)
            axs[1,1].plot([r['displacement_m']*1000 for r in rows],[r['min_J'] for r in rows],marker)
    axs[0,0].set(xlabel='Platen compression [mm]',ylabel='Compressive reaction [N]');axs[0,0].legend(fontsize=8)
    axs[0,1].set(xlabel='Platen compression [mm]',ylabel='Lateral stretch');axs[0,1].legend(fontsize=7)
    axs[1,0].set(xlabel='Platen compression [mm]',ylabel='Top-bottom imbalance [N]')
    axs[1,1].set(xlabel='Platen compression [mm]',ylabel='Minimum element J')
    for ax in axs.flat:ax.grid(alpha=.2)
    fig.suptitle('Solved synthetic equilibria: o = 6 tetrahedra; x = 48 tetrahedra')
    fig.tight_layout();fig.savefig(out/'equilibrium_checks.png',dpi=160);plt.close(fig)
    print(json.dumps({k:v for k,v in summary.items() if k not in ['protected_sha256','source_sha256']},indent=2))


if __name__=='__main__':run()
