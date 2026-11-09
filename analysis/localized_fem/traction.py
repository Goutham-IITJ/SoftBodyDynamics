"""Exact reference-triangle integration of rectangular uniform dead traction."""
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class Rectangle:
    center_x: float
    center_y: float
    length: float
    width: float

    def __post_init__(self):
        values=np.asarray([self.center_x,self.center_y,self.length,self.width])
        if np.iscomplexobj(values) or not np.isfinite(values).all() or self.length<=0 or self.width<=0:
            raise ValueError('Patch center must be finite; lengths must be positive finite metres')

    @property
    def bounds(self):
        return np.array([[self.center_x-self.length/2,self.center_y-self.width/2],
                         [self.center_x+self.length/2,self.center_y+self.width/2]])


def clip_polygon(polygon,bounds):
    """Sutherland-Hodgman convex clipping in xy, including crossing triangles."""
    points=[np.asarray(p,float) for p in polygon]
    for axis,level,sign in [(0,bounds[0,0],1),(0,bounds[1,0],-1),(1,bounds[0,1],1),(1,bounds[1,1],-1)]:
        if not points:break
        result=[];previous=points[-1];a=sign*(previous[axis]-level)
        for current in points:
            b=sign*(current[axis]-level)
            if (a>=0)!=(b>=0):result.append(previous+(current-previous)*a/(a-b))
            if b>=0:result.append(current)
            previous=current;a=b
        points=result
    return np.asarray(points)


@dataclass(frozen=True)
class Traction:
    force_N: float
    area_m2: float
    pressure_Pa: float
    centroid_xy_m: np.ndarray
    clipped_bounds_xy_m: np.ndarray
    nodal_forces_N: np.ndarray
    shape_integrals_m2: np.ndarray
    whole_top_integrals_m2: np.ndarray
    intersected_triangles: int


def integrate_rectangle(reference,top_triangles,rectangle,force):
    """Integrate f_a=-F/A * integral_patch N_a dA * e_z on reference faces.

    Linear N_a is integrated exactly on a fan triangulation of each clipped
    polygon. No nearest-node rule, empirical surrogate or follower pressure.
    """
    X=np.asarray(reference,float);faces=np.asarray(top_triangles)
    if X.ndim!=2 or X.shape[1]!=3 or not np.isfinite(X).all():raise ValueError('Invalid reference nodes')
    if faces.ndim!=2 or faces.shape[1]!=3 or faces.dtype.kind not in 'iu' or len(faces)==0:raise ValueError('Require top triangles')
    if np.any(faces<0) or np.any(faces>=len(X)) or any(len(set(f))!=3 for f in faces):raise ValueError('Invalid face connectivity')
    if not np.isfinite(force) or force<0:raise ValueError('Force must be finite nonnegative newtons')
    z=X[faces,2]
    if np.ptp(z)>1e-12:raise ValueError('Only a horizontal reference top surface is supported')
    whole=np.zeros(len(X));weights=np.zeros(len(X));area=0.;first=np.zeros(2);intersections=0
    for face in faces:
        xy=X[face,:2];det=np.linalg.det((xy[1:]-xy[0]).T);A=abs(det)/2
        if A<=0:raise ValueError('Degenerate surface triangle')
        whole[face]+=A/3
        clipped=clip_polygon(xy,rectangle.bounds)
        if len(clipped)<3:continue
        inverse=np.linalg.inv(np.column_stack([xy,np.ones(3)]))
        part=0.
        for i in range(1,len(clipped)-1):
            tri=np.array([clipped[0],clipped[i],clipped[i+1]])
            a=abs(float(np.linalg.det((tri[1:]-tri[0]).T)))/2
            if a==0:continue
            N=np.column_stack([tri,np.ones(3)])@inverse
            weights[face]+=a*N.mean(axis=0);area+=a;part+=a;first+=a*tri.mean(axis=0)
        intersections+=part>0
    footprint=np.array([X[faces,:2].min(axis=(0,1)),X[faces,:2].max(axis=(0,1))])
    bounds=np.array([np.maximum(footprint[0],rectangle.bounds[0]),np.minimum(footprint[1],rectangle.bounds[1])])
    expected=float(np.prod(np.maximum(0.,bounds[1]-bounds[0])))
    if expected<=0 or area<=0:raise ValueError('Patch has zero overlap with the reference top')
    if not np.isclose(area,expected,rtol=1e-11,atol=1e-18):raise ValueError('Surface faces do not cover the rectangle intersection exactly')
    if np.min(weights)<-1e-15:raise ValueError('Invalid negative integrated shape weight')
    pressure=float(force)/area;loads=np.zeros_like(X);loads[:,2]=-pressure*weights
    return Traction(float(force),area,pressure,first/area,bounds,loads,weights,whole,int(intersections))
