"""Nominal specimen geometry; only yellow foam has FEM DOFs. SI throughout."""
from dataclasses import dataclass
import itertools
import numpy as np
from analysis.fem_solver.solver import BlockSolver
from analysis.material.hyperfoam import Hyperfoam


@dataclass(frozen=True)
class SpongeConfig:
    length: float=.073
    width: float=.050
    yellow_height: float=.020
    backing_height: float=.007
    platen_length: float=.085
    platen_width: float=.050

    def __post_init__(self):
        values=np.array([self.length,self.width,self.yellow_height,self.backing_height,self.platen_length,self.platen_width],float)
        if not np.isfinite(values).all() or np.any(values<=0):raise ValueError('Dimensions must be positive finite metres')

    @property
    def top_z(self):return self.backing_height+self.yellow_height

    @property
    def contact_area(self):return self.length*self.width

    @property
    def yellow_volume(self):return self.contact_area*self.yellow_height


def cuboid_surface(low,high):
    """Eight vertices and twelve consistently outward triangles (rigid visuals)."""
    low=np.asarray(low,float);high=np.asarray(high,float)
    vertices=np.array(list(itertools.product(*zip(low,high))))
    faces=[]
    for axis in range(3):
        other=[a for a in range(3) if a!=axis]
        for side in [0,1]:
            ids=[]
            for a,b in [(0,0),(1,0),(1,1),(0,1)]:
                bits=[0,0,0];bits[axis]=side;bits[other[0]]=a;bits[other[1]]=b
                ids.append(bits[0]*4+bits[1]*2+bits[2])
            for tri in [[ids[0],ids[1],ids[2]],[ids[0],ids[2],ids[3]]]:
                p=vertices[tri];normal=np.cross(p[1]-p[0],p[2]-p[0]);center=(low+high)/2
                if np.dot(normal,p.mean(axis=0)-center)<0:tri[1],tri[2]=tri[2],tri[1]
                faces.append(tri)
    return vertices,np.array(faces,int)


def outward_boundary(reference,cells):
    """Extract conforming FEM boundary with outward reference winding."""
    entries={}
    for cell in cells:
        for missing in range(4):
            face=[int(cell[i]) for i in range(4) if i!=missing]
            entries.setdefault(tuple(sorted(face)),[]).append((face,int(cell[missing])))
    result=[]
    for group in entries.values():
        if len(group)>2:raise ValueError('Nonmanifold face')
        if len(group)==1:
            face,opposite=group[0];p=reference[face]
            if np.dot(np.cross(p[1]-p[0],p[2]-p[0]),reference[opposite]-p[0])>0:face[1],face[2]=face[2],face[1]
            result.append(face)
    return np.asarray(result,int)


class Sponge:
    """Rigid backing + deformable yellow solid + rigid massless full-face platen.

    Green stiffness and interlayer shear are deliberately not represented.
    Platen/support constraints are infinite-plane full-face idealizations, not
    finite-footprint collision: lateral expansion can exceed rigid visual edges.
    """
    def __init__(self,config=None,subdivisions=(2,2,2),material=None):
        self.config=config if config is not None else SpongeConfig()
        c=self.config
        self.solver=BlockSolver(material if material is not None else Hyperfoam(2000,10,0),dimensions=(c.length,c.width,c.yellow_height),subdivisions=subdivisions,origin=(0,0,c.backing_height))
        self.boundary=outward_boundary(self.solver.X,self.solver.cells)
        self._backing,self.backing_faces=cuboid_surface([0,0,0],[c.length,c.width,c.backing_height])

    @property
    def backing_vertices(self):return self._backing.copy()

    def platen_vertices(self,compression=0.):
        c=self.config
        if not np.isfinite(compression) or compression<0 or compression>=c.yellow_height:raise ValueError('Invalid compression')
        lo=(c.length-c.platen_length)/2;left=(c.width-c.platen_width)/2;z=c.top_z-compression
        return np.array([[lo,left,z],[lo+c.platen_length,left,z],[lo+c.platen_length,left+c.platen_width,z],[lo,left+c.platen_width,z]])

    def solve_displacement(self,d,start=None):return self.solver.solve_displacement(d,start=start)

    def solve_force(self,force):return self.solver.solve_force(force)
