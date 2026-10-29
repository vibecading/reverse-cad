# Put the active Rhino viewport on the solved camera and capture it at the photo's size.
# Run inside Rhino 8 (Python 3) with RESULT (solve.py output), SIZE (w, h) and OUT (png path) in globals.
# The frustum is set from the focal length in pixels, so the capture is pixel-aligned with the photo.
import Rhino
import Rhino.Geometry as rg
import System

doc = __rhino_doc__
cam = RESULT['camera']
W, H = SIZE
f = cam['f_px']
view = doc.Views.ActiveView
vp = view.ActiveViewport
if vp.IsParallelProjection:
    vp.ChangeToPerspectiveProjection(True, 50.0)
vi = Rhino.DocObjects.ViewportInfo(vp)
pos = rg.Point3d(*cam['pos'])
tgt = rg.Point3d(*cam['target'])
vi.SetCameraLocation(pos)
vi.SetCameraDirection(tgt - pos)
vi.SetCameraUp(rg.Vector3d(*cam['up']))
n = 0.5
cx, cy = RESULT.get('principal_point', (W / 2, H / 2))  # off centre for shift-lens photos
vi.SetFrustum(-n * cx / f, n * (W - cx) / f, -n * (H - cy) / f, n * cy / f, n, 1000.0)
vi.TargetPoint = tgt
vp.SetViewProjection(vi, True)
vp.DisplayMode = Rhino.Display.DisplayModeDescription.FindByName('Shaded')
view.Redraw()
Rhino.RhinoApp.Wait()
cap = Rhino.Display.ViewCapture()
cap.Width, cap.Height = W, H
cap.ScaleScreenItems = False
cap.DrawAxes = cap.DrawGrid = cap.DrawGridAxes = False
cap.CaptureToBitmap(view).Save(OUT, System.Drawing.Imaging.ImageFormat.Png)
print('captured', OUT, 'lens', round(vp.Camera35mmLensLength, 2))
