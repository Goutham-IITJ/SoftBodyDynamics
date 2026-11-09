"""Usable entry point: frozen full-face solver or experimental patch traction."""
import argparse
from pathlib import Path
from types import SimpleNamespace
import json
import time
import numpy as np
from analysis.localized_fem.simulate import export,write_json,render
from analysis.localized_fem.support import UnilateralSolver
from analysis.localized_fem.solver import TractionSolver
from analysis.localized_fem.traction import Rectangle,integrate_rectangle


def sequence(problem,states,directory,kind):
    """Only converged equilibrium coordinates; reverse path is hyperelastic unloading."""
    from PIL import Image
    directory=Path(directory);directory.mkdir()
    frames=[];manifest=[]
    indices=list(range(len(states)))+list(range(len(states)-2,-1,-1))
    for i,k in enumerate(indices):
        point=states[k];path=directory/f'frame_{i:03d}.png'
        state=SimpleNamespace(positions=point['positions'],load=SimpleNamespace(force_N=point['force_N'],clipped_bounds_xy_m=np.array([[0.,0.],[.073,.05]]) if kind=='full-face' else problem.sequence_bounds))
        render(problem,state,path)
        # Full-face scene must not be mislabeled as a traction approximation.
        if kind=='full-face':
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            from mpl_toolkits.mplot3d.art3d import Poly3DCollection
            fig=plt.figure(figsize=(8,6));ax=fig.add_subplot(projection='3d')
            ax.add_collection3d(Poly3DCollection(point['positions'][problem.boundary]*1000,facecolors='#edc944',edgecolors='#64551e',linewidths=.35))
            ax.set(xlim=(0,73),ylim=(0,50),zlim=(0,30),xlabel='x mm',ylabel='y mm',zlabel='z mm',title=f'Frozen full-face platen: {point["force_N"]:g} N\nQuasi-static equilibria; not recovery timing')
            ax.set_box_aspect((73,50,30));fig.tight_layout();fig.savefig(path,dpi=130);plt.close(fig)
        with Image.open(path) as im:frames.append(im.convert('RGB').copy())
        manifest.append(dict(frame=i,solved_state=k,force_N=point['force_N'],branch='loading' if i<len(states) else 'reversible_unloading'))
    np.savez_compressed(directory/'solved_states.npz',positions=np.array([s['positions'] for s in states]),force_N=np.array([s['force_N'] for s in states]))
    frames[0].save(directory/'loading_unloading.gif',save_all=True,append_images=frames[1:],duration=450,loop=0)
    write_json(directory/'frames.json',dict(note='Discrete solved equilibria; reverse path reuses the same reversible hyperelastic states. Playback time is arbitrary, no dynamics or identified recovery.',frames=manifest))


def full_face(force,output,make_sequence):
    from demo.model import configuration,new_sponge,solve
    from analysis.sponge.geometry import outward_boundary
    config=configuration();sponge=new_sponge(config);problem=sponge.solver
    problem.boundary=outward_boundary(problem.X,problem.cells)
    forces=[0.,force*.25,force*.5,force*.75,force] if make_sequence else [force]
    states=[];started=time.perf_counter()
    for value in forces:
        state=solve(sponge,value);states.append(dict(force_N=value,positions=state.positions.copy()))
    loads=np.zeros_like(problem.X);loads[problem.top,2]=state.gradient[problem.top,2]
    reactions=np.zeros_like(problem.X);reactions[problem.bottom,2]=state.gradient[problem.bottom,2]
    for node,axis in problem.anchors:reactions[node,axis]=state.gradient[node,axis]
    np.savetxt(output/'nodes.csv',np.column_stack([np.arange(len(problem.X)),problem.X,state.positions,loads]),delimiter=',',header='node,X_m,Y_m,Z_m,x_m,y_m,z_m,fx_N,fy_N,fz_N',comments='')
    np.savetxt(output/'tetrahedra.csv',problem.cells,delimiter=',',fmt='%d',header='n0,n1,n2,n3',comments='')
    np.savetxt(output/'boundary_triangles.csv',problem.boundary,delimiter=',',fmt='%d',header='n0,n1,n2',comments='')
    np.savetxt(output/'reactions.csv',reactions,delimiter=',',header='rx_N,ry_N,rz_N',comments='')
    d=dict(mode='frozen full-face platen',force_N=force,compression_mm=state.displacement*1000,free_residual_N=state.free_residual,min_J=state.min_J,support_reaction_N=state.bottom_reaction,force_balance_N=float(np.max(abs((reactions+loads).sum(axis=0)))),moment_balance_Nm=float(np.max(abs(np.cross(state.positions,reactions+loads).sum(axis=0)))),runtime_s=time.perf_counter()-started,iterations=state.iterations,termination=state.termination,mesh=list(config['subdivisions']),note='Platen reactions define applied nodal distribution; this is not prescribed uniform patch traction.')
    write_json(output/'diagnostics.json',d)
    # This renderer also provides the final static image, without touching baseline media.
    sequence(problem,states if make_sequence else [states[-1]],output/'sequence','full-face')
    from shutil import copyfile
    copyfile(output/'sequence'/f'frame_{len(states)-1:03d}.png',output/'deformed.png')
    return d


def main():
    parser=argparse.ArgumentParser(description='Frozen full-face FEM or EXPERIMENTAL rectangular reference dead traction. No rigid-card/finger contact or damping. Outputs are exclusive-create.')
    commands=parser.add_subparsers(dest='mode',required=True)
    for mode in ['full-face','localized']:
        p=commands.add_parser(mode,help='Frozen horizontal full-face platen' if mode=='full-face' else 'Experimental prescribed patch traction, not a rigid card')
        p.add_argument('--force',type=float,required=True,help='Total downward force, N')
        p.add_argument('--output',type=Path,required=True,help='New output directory')
        p.add_argument('--sequence',action='store_true',help='Render actual solved equilibrium loading and reversible unloading states; not physical timing')
        if mode=='localized':
            for name in ['patch-length','patch-width','center-x','center-y']:p.add_argument('--'+name+'-mm',type=float,required=True)
            p.add_argument('--mesh',nargs=3,type=int,default=[4,4,2],metavar=('NX','NY','NZ'),help='Cells in x/y/z, even positive x/y; default 4 4 2 is EXPERIMENTAL, not mesh-converged')
            p.add_argument('--support',choices=['unilateral','bilateral'],default='unilateral',help='Unilateral frictionless bottom plane (default); bilateral reproduces Phase 7B')
            p.add_argument('--load-step',type=float,default=.25,help='Continuation increment (0,1], no automatic retry after failure')
            p.add_argument('--time-limit-s',type=float,default=180.,help='Bound nonlinear solve time; checked once per iteration, default 180 s')
    args=parser.parse_args()
    if args.output.exists():parser.error('Output already exists; use a new directory')
    if not np.isfinite(args.force) or args.force<0:parser.error('Force must be finite and nonnegative')
    try:
        if args.mode=='localized':
            if not np.isfinite(args.time_limit_s) or args.time_limit_s<=0:raise ValueError('Time limit must be positive finite seconds')
            if not 0<args.load_step<=1:raise ValueError('Load step must be in (0,1]')
            patch=Rectangle(args.center_x_mm/1000,args.center_y_mm/1000,args.patch_length_mm/1000,args.patch_width_mm/1000)
            problem=(UnilateralSolver if args.support=='unilateral' else TractionSolver)(tuple(args.mesh))
            load=integrate_rectangle(problem.X,problem.top_faces,patch,args.force)
        else:
            from demo.model import configuration
            configuration()
    except (ValueError,TypeError) as exc:parser.error(str(exc))
    args.output.mkdir(parents=True)
    write_json(args.output/'inputs.json',{**vars(args),'output':str(args.output),'material':{'mu_Pa':6999.814990181902,'alpha':10,'beta':0},'capability':'frozen full-face platen' if args.mode=='full-face' else 'EXPERIMENTAL prescribed reference dead traction; NOT rigid-card contact'})
    started=time.perf_counter()
    try:
        if args.mode=='localized':
            problem.deadline=started+args.time_limit_s
            state=problem.solve_patch(patch,args.force,load_step=args.load_step,min_load_step=args.load_step)
            d=export(problem,state,args.output)
            d['experimental']=True;write_json(args.output/'diagnostics.json',d)
            if args.sequence:
                problem.sequence_bounds=load.clipped_bounds_xy_m
                sequence(problem,state.solved_states,args.output/'sequence','localized')
        else:d=full_face(args.force,args.output,args.sequence)
    except Exception as exc:
        write_json(args.output/'failure.json',dict(status='failed',reason=str(exc),runtime_s=time.perf_counter()-started,attempts=getattr(exc,'attempts',[]),support_iterations=getattr(locals().get('problem'),'support_log',[])))
        parser.exit(1,f'Failed: {exc}. See {args.output / "failure.json"}\n')
    print(json.dumps(d,indent=2))


if __name__=='__main__':main()
