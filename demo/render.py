"""Consistent Matplotlib rendering of actual FEM node arrays; no kinematic replay."""
import itertools
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection,Line3DCollection

BG='#f7f8fa';BLUE='#1865ad';YELLOW='#f4c944';GREEN='#21834b'


def mesh_axes(ax,sponge,positions,displacement):
    table=np.array([[-.01,-.008,0],[.083,-.008,0],[.083,.058,0],[-.01,.058,0]])*1000
    ax.add_collection3d(Poly3DCollection([table],facecolors='#aeb8c4',alpha=.15))
    back=sponge.backing_vertices*1000
    ax.add_collection3d(Poly3DCollection(back[sponge.backing_faces],facecolors=GREEN,edgecolors='#145331',linewidths=.6))
    nodes=positions*1000
    ax.add_collection3d(Poly3DCollection(nodes[sponge.boundary],facecolors=YELLOW,edgecolors='#95791c',linewidths=.5,alpha=.85))
    edges=sorted({tuple(sorted(e)) for c in sponge.solver.cells for e in itertools.combinations(c,2)})
    ax.add_collection3d(Line3DCollection(nodes[np.array(edges)],colors='#8c7320',linewidths=.4,alpha=.35))
    ax.add_collection3d(Poly3DCollection([sponge.platen_vertices(displacement)*1000],facecolors='#9bbbd5',edgecolors='#325d81',alpha=.5,linewidths=1))
    ax.set(xlim=(-8,81),ylim=(-3,54),zlim=(0,30),xlabel='x (mm)',ylabel='y (mm)',zlabel='z (mm)')
    ax.set_box_aspect((89,57,30));ax.view_init(elev=24,azim=-62);ax.set_proj_type('ortho');ax.set_facecolor(BG)
    ax.tick_params(labelsize=8,pad=0)


def image_array(fig):
    fig.canvas.draw();array=np.asarray(fig.canvas.buffer_rgba())[:,:,:3].copy();plt.close(fig)
    return array


def header(fig,title,subtitle):
    fig.text(.04,.935,title,fontsize=22,weight='bold',color='#15283b')
    fig.text(.04,.89,subtitle,fontsize=11,color='#4d5d70')
    fig.text(.04,.035,'SoftBodyDynamics  |  Frozen Stage 5 primary  |  Quasi-static equilibrium, no physical playback timescale',fontsize=10,color='#4d5d70')


def equilibrium_frame(sponge,state,force,index,total,path,marker,title):
    fig=plt.figure(figsize=(12.8,7.2),dpi=100,facecolor=BG)
    header(fig,title,'mu = 6999.815 Pa | alpha = 10 | beta = 0 | 73 x 50 x 20 mm yellow + 7 mm rigid backing')
    ax=fig.add_axes([.015,.12,.59,.71],projection='3d');mesh_axes(ax,sponge,state.positions,state.displacement)
    graph=fig.add_axes([.68,.39,.28,.38]);graph.set_facecolor('white')
    graph.plot([r[0] for r in path],[r[1] for r in path],color=BLUE,lw=2,label='Solved FEM loading path')
    graph.scatter([force],[1000*state.displacement],s=65,color='#df6b26',zorder=5)
    graph.set(xlim=(0,11.2),ylim=(0,12),xlabel='Applied force (N)',ylabel='Compression (mm)')
    graph.grid(alpha=.2);graph.tick_params(labelsize=9)
    fig.text(.68,.29,f'Force  {force:.3f} N     Compression  {1000*state.displacement:.3f} mm',fontsize=11,weight='bold')
    fig.text(.68,.245,f'Equilibrium step {index+1}/{total}   |   {marker}',fontsize=10)
    fig.text(.68,.195,f'min J = {state.min_J:.4f}   |   free residual = {state.free_residual:.1e} N',fontsize=9)
    fig.text(.68,.12,'Yellow: FEM solid   Green: rigid backing\nBlue: massless full-face card; no friction',fontsize=10,linespacing=1.6)
    return image_array(fig)


def comparison_frame(sponge,state,volume,image,frame_info,observations):
    fig=plt.figure(figsize=(12.8,7.2),dpi=100,facecolor=BG)
    role='HELD OUT FROM THIS FEM FIT' if volume==750 else 'CALIBRATION LOAD (cycle 1)'
    header(fig,f'Real specimen and frozen FEM  |  {volume} ml',role+'  |  Retrospective comparison; no timing or pixel registration claim')
    ax=fig.add_axes([.025,.31,.49,.46]);ax.imshow(image);ax.axis('off')
    fig.text(.04,.285,f'Real cycle 1: frame {frame_info["frame"]}, t = {frame_info["time_s"]:.3f} s',fontsize=10)
    ax=fig.add_axes([.55,.22,.43,.60],projection='3d');mesh_axes(ax,sponge,state.positions,state.displacement)
    predicted=state.displacement*1000
    fig.text(.04,.205,f'Settled-hold medians: {observations[0]:.3f} / {observations[1]:.3f} mm (cycles 1 / 2)',fontsize=13)
    fig.text(.04,.153,f'FEM equilibrium: {predicted:.3f} mm   |   Errors: {predicted-observations[0]:+.3f} / {predicted-observations[1]:+.3f} mm',fontsize=13,color=BLUE)
    fig.text(.04,.10,'Optical medians describe hold windows, not this individual frame.\nReal visible color layers differ from nominal 20/7 mm geometry; lateral response is not validated.',fontsize=10,color='#4d5d70')
    return image_array(fig)


def text_frame(title,lines):
    fig=plt.figure(figsize=(12.8,7.2),dpi=100,facecolor=BG)
    header(fig,title,'Observation-calibrated mechanics | Reproducible equilibrium prediction')
    for y,(text,size,color) in zip(np.linspace(.76,.17,len(lines)),lines):fig.text(.06,y,text,fontsize=size,color=color,linespacing=1.5)
    return image_array(fig)
