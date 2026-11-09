"""CLI and exports for synthetic reference-area dead traction; SI internally."""
import argparse
import csv
import json
from pathlib import Path
import time
import numpy as np
from analysis.localized_fem.solver import TractionSolver
from analysis.localized_fem.traction import Rectangle


def write_json(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def render(problem,state,path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig=plt.figure(figsize=(9,7));ax=fig.add_subplot(projection='3d')
    triangles=state.positions[problem.boundary]*1000
    ax.add_collection3d(Poly3DCollection(triangles,facecolors='#edc944',edgecolors='#64551e',linewidths=.35,alpha=.65))
    lo,hi=state.load.clipped_bounds_xy_m*1000;z=problem.X[:,2].max()*1000
    corners=np.array([[lo[0],lo[1],z],[hi[0],lo[1],z],[hi[0],hi[1],z],[lo[0],hi[1],z],[lo[0],lo[1],z]])
    ax.plot(*corners.T,color='red',label='Reference footprint (not an indenter)')
    # Rigid backing is a visual support, not another deformable material.
    from analysis.sponge.geometry import cuboid_surface
    bottom=problem.origin.copy();bottom[2]-=.007
    vertices,faces=cuboid_surface(bottom,problem.origin+np.array([*problem.lengths[:2],0.]))
    ax.add_collection3d(Poly3DCollection(vertices[faces]*1000,facecolors='#458758',edgecolors='#245132',alpha=.4))
    ax.set(xlim=(0,73),ylim=(0,50),zlim=(0,30),xlabel='x (mm)',ylabel='y (mm)',zlabel='z (mm)',title=f'Prescribed dead traction: {state.load.force_N:g} N\nTrue displacement scale; not rigid-card contact')
    ax.set_box_aspect((73,50,30));ax.legend(loc='upper left',fontsize=8)
    fig.tight_layout();fig.savefig(path,dpi=170);plt.close(fig)


def export(problem,state,directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    np.savetxt(directory/'nodes.csv',np.column_stack([np.arange(len(problem.X)),problem.X,state.positions,state.load.nodal_forces_N]),delimiter=',',header='node,X_m,Y_m,Z_m,x_m,y_m,z_m,fx_N,fy_N,fz_N',comments='')
    np.savetxt(directory/'tetrahedra.csv',problem.cells,delimiter=',',fmt='%d',header='n0,n1,n2,n3',comments='')
    np.savetxt(directory/'boundary_triangles.csv',problem.boundary,delimiter=',',fmt='%d',header='n0,n1,n2',comments='')
    reactions=np.zeros_like(problem.X);reactions.ravel()[problem.fixed]=state.gradient.ravel()[problem.fixed]
    np.savetxt(directory/'reactions.csv',reactions,delimiter=',',header='rx_N,ry_N,rz_N',comments='')
    for name,rows in [('history',state.history),('continuation',state.attempts)]:
        if rows:
            with (directory/f'{name}.csv').open('w',newline='',encoding='utf-8') as handle:
                writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    diagnostics=problem.diagnostics(state)
    diagnostics['unloaded_mean_downward_mm']=None if not np.isfinite(diagnostics['unloaded_mean_downward_mm']) else diagnostics['unloaded_mean_downward_mm']
    diagnostics['tensile_bottom_reaction_total_N']=float(-np.minimum(reactions[problem.bottom,2],0).sum())
    diagnostics['centroid_xy_m']=state.load.centroid_xy_m.tolist()
    diagnostics['force_tolerance_N']=problem.force_tolerance
    if hasattr(state,'active_bottom'):
        np.savetxt(directory/'bottom_contact.csv',np.column_stack([problem.bottom,state.positions[problem.bottom,2]-problem.origin[2],reactions[problem.bottom,2],np.isin(problem.bottom,state.active_bottom)]),delimiter=',',header='node,gap_m,normal_reaction_N,active',comments='')
        write_json(directory/'support_iterations.json',state.support_log)
    write_json(directory/'diagnostics.json',diagnostics);render(problem,state,directory/'deformed.png')
    return diagnostics


def main():
    parser=argparse.ArgumentParser(description='Finite-area downward dead traction on frozen hyperfoam. No platen/contact or experimental validation. Rectangle is clipped to the reference 73 x 50 mm top; force is normalized over the overlap. x/y origin: lower left corner. All top DOFs free; bilateral bottom plane.')
    parser.add_argument('--force',type=float,required=True,help='Total downward force (N), nonnegative; start small')
    for name in ['patch-length','patch-width','center-x','center-y']:
        parser.add_argument('--'+name+'-mm',type=float,required=True,help='Reference coordinate/length in mm; lengths positive')
    parser.add_argument('--mesh',type=int,nargs=3,default=(2,2,1),metavar=('NX','NY','NZ'),help='Positive cell counts; NX and NY even (default 2 2 1)')
    parser.add_argument('--distribution',choices=['uniform-reference'],default='uniform-reference')
    parser.add_argument('--load-step',type=float,default=.25,help='Continuation factor increment in (0,1]')
    parser.add_argument('--output',type=Path,required=True,help='New output directory; existing paths are refused')
    args=parser.parse_args()
    if args.output.exists():parser.error('Output already exists; choose a new directory')
    if not np.isfinite(args.load_step) or not 0<args.load_step<=1:parser.error('Load step must be in (0,1]')
    try:
        rectangle=Rectangle(args.center_x_mm/1000,args.center_y_mm/1000,args.patch_length_mm/1000,args.patch_width_mm/1000)
        problem=TractionSolver(tuple(args.mesh))
        from analysis.localized_fem.traction import integrate_rectangle
        integrate_rectangle(problem.X,problem.top_faces,rectangle,args.force)
    except (ValueError,TypeError) as exc:parser.error(str(exc))
    args.output.mkdir(parents=True);write_json(args.output/'inputs.json',{**vars(args),'output':str(args.output),'material':{'mu_Pa':problem.material.mu,'alpha':problem.material.alpha,'beta':problem.material.beta},'support':'bilateral fixed normal; minimum horizontal anchors'})
    started=time.perf_counter()
    try:
        state=problem.solve_patch(rectangle,args.force,load_step=args.load_step)
        diagnostics=export(problem,state,args.output)
    except Exception as exc:
        write_json(args.output/'failure.json',{'status':'failed','reason':str(exc),'runtime_s':time.perf_counter()-started,'attempts':getattr(exc,'attempts',[]),'accepted_history':getattr(exc,'history',[]),'force_tolerance_N':problem.force_tolerance,'free_dofs':len(problem.free),'tetrahedra':len(problem.cells)})
        raise
    print(json.dumps(diagnostics,indent=2))


if __name__=='__main__':main()
