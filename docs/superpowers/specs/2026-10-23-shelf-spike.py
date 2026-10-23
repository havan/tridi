# Reference only: the throwaway spike whose look the user approved (2026-10-23).
# Not product code; see 2026-10-23-shelf-design.md.
# Throwaway spike: one shelf with the proposed default look.
# X = width, Y = depth (out from the wall at y=0), Z = up (shelf top at z=0).
import os
import FreeCAD as App
import Part
import Mesh
from FreeCAD import Vector as V

OUT = os.path.dirname(os.path.abspath(__file__))

W, D = 200.0, 100.0          # width, depth
T_SHELF, T_PLATE = 5.0, 4.0  # slab and back plate thickness
DROP = 55.0                  # back plate below the shelf underside
SPLASH = 18.0                # short back plate above the shelf, for the top screws
T_GUSSET, G_DEPTH, WEB = 5.0, 75.0, 6.0
EDGE_R = 2.0
NOTCH_R = 15.0
SCREW_D, HEAD_D = 4.5, 8.5


def box(x0, y0, z0, dx, dy, dz):
    return Part.makeBox(dx, dy, dz, V(x0, y0, z0))


shelf = box(0, 0, -T_SHELF, W, D, T_SHELF)
shelf = shelf.makeFillet(EDGE_R, [e for e in shelf.Edges
                                  if abs(e.BoundBox.YMin - D) < 1e-6 and abs(e.BoundBox.YMax - D) < 1e-6])

plate = box(0, 0, -T_SHELF - DROP, W, T_PLATE, DROP + T_SHELF + SPLASH)
plate = plate.makeFillet(EDGE_R, [e for e in plate.Edges
                                  if abs(e.BoundBox.YMin - T_PLATE) < 1e-6 and abs(e.BoundBox.YMax - T_PLATE) < 1e-6])


def gusset(x):
    # Rectangle under the shelf minus an ellipse centred on its outer-lower corner:
    # a curved bracket that keeps a WEB-wide strip along the shelf and along the plate.
    gd, gh = G_DEPTH, DROP
    rect = Part.makePlane(gd, gh, V(0, 0, 0))
    ell = Part.Ellipse(V(gd, gh, 0), gd - WEB, gh - WEB)  # major axis along u (gd > gh)
    face = rect.cut(Part.Face(Part.Wire(ell.toShape())))
    solid = face.extrude(V(0, 0, T_GUSSET))
    # 2D (u = depth, v = distance below shelf) -> world: rotate so u->+Y, v->-Z, extrusion->+X
    m = App.Matrix(0, 0, 1, x,
                   1, 0, 0, T_PLATE,
                   0, -1, 0, -T_SHELF,
                   0, 0, 0, 1)
    return solid.transformGeometry(m)


inset = W / 6
body = shelf.fuse([plate, gusset(inset - T_GUSSET / 2), gusset(W - inset - T_GUSSET / 2)])

# Quarter-circle cable notch in the back-left corner, through shelf and plate
notch = Part.makeCylinder(NOTCH_R, 400, V(0, 0, -200), V(0, 0, 1))
body = body.cut(notch)


def countersunk(x, z):
    hole = Part.makeCylinder(SCREW_D / 2, 20, V(x, -5, z), V(0, 1, 0))
    sink = Part.makeCone(SCREW_D / 2, HEAD_D / 2, (HEAD_D - SCREW_D) / 2,
                         V(x, T_PLATE - (HEAD_D - SCREW_D) / 2, z), V(0, 1, 0))
    return hole.fuse(sink)


for x in (W * 0.35, W * 0.65):
    body = body.cut(countersunk(x, SPLASH / 2))
    body = body.cut(countersunk(x, -T_SHELF - DROP + 10))

body = body.removeSplitter()
assert body.isValid()

doc = App.newDocument("shelf_spike")
Part.show(body, "shelf")
doc.recompute()
doc.saveAs(os.path.join(OUT, "shelf_spike.FCStd"))
body.exportStl(os.path.join(OUT, "shelf_spike.stl"))
print("volume cm3:", round(body.Volume / 1000, 1), "bbox:", body.BoundBox)

# Quick shaded render for a look without the GUI
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

pts, tris = body.tessellate(0.2)
P = np.array([[p.x, p.y, p.z] for p in pts])
T = np.array(tris)
light = np.array([0.4, 0.6, 0.7]); light /= np.linalg.norm(light)
for name, elev, azim in (("front", 22, 55), ("below", -22, 125)):
    fig = plt.figure(figsize=(8, 6), dpi=110)
    ax = fig.add_subplot(projection="3d")
    tri = P[T]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    shade = 0.35 + 0.65 * np.abs(n @ light)
    col = np.outer(shade, [0.85, 0.82, 0.76])
    ax.add_collection3d(Poly3DCollection(tri, facecolors=col, edgecolor="none"))
    ax.set_xlim(0, W); ax.set_ylim(-50, 150); ax.set_zlim(-120, 80)
    ax.set_box_aspect((W, 200, 200))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    fig.savefig(os.path.join(OUT, f"shelf_spike_{name}.png"), bbox_inches="tight")
    plt.close(fig)
