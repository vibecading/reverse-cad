"""Read lengths off a scanned measured drawing.

usage:
  python -I sheet.py ruler sheet.png x0 y0 x1 y1 out.png [--zoom 2]
      crop with pixel rulers on the top and left edges, for reading positions
  python -I sheet.py profile sheet.png row|col AT FROM TO [--width 4] [--dark 80]
      dark lines crossed by a strip: "row 1700 380 600" walks x from 380 to 600
      along y = 1700 and prints every pixel darker than --dark (0-255 scale)
  python -I sheet.py scale PX FEET [PX FEET ...]
      px per foot from known lengths (a scale bar, a dimension string);
      give at least one across the sheet and one down it, they can differ
  python -I sheet.py length PX --pxft S [--m]
      a measured pixel length in feet-inches (and metres with --m)

Scans are rarely square: on the Robie House HABS sheets the scale is 19.98
px/ft across and 19.66 px/ft down. Measure both before reading anything.
"""
import sys


def ft_in(ft):
    sign = '-' if ft < 0 else ''
    ft = abs(ft)
    f = int(ft)
    i = round((ft - f) * 12)
    if i == 12:
        f, i = f + 1, 0
    return "%s%d'-%d\"" % (sign, f, i)


def opt(args, k, d, cast=float):
    return cast(args[args.index(k) + 1]) if k in args else d


def main():
    a = sys.argv[1:]
    cmd = a[0]
    if cmd == 'ruler':
        import cv2
        src, (x0, y0, x1, y1), out = a[1], map(int, a[2:6]), a[6]
        s = opt(a, '--zoom', 1, int)
        im = cv2.imread(src)
        c = cv2.resize(im[y0:y1, x0:x1], None, fx=s, fy=s, interpolation=cv2.INTER_NEAREST)
        for y in range(y0 - y0 % 10 + 10, y1, 10):
            cv2.line(c, (0, (y - y0) * s), (10 if y % 50 else 25, (y - y0) * s), (0, 0, 255), 1)
            if y % 50 == 0:
                cv2.putText(c, str(y), (27, (y - y0) * s + 5), 0, 0.45, (0, 0, 255), 1)
        for x in range(x0 - x0 % 10 + 10, x1, 10):
            cv2.line(c, ((x - x0) * s, 0), ((x - x0) * s, 10 if x % 50 else 25), (255, 0, 0), 1)
            if x % 50 == 0:
                cv2.putText(c, str(x), ((x - x0) * s + 2, 38), 0, 0.45, (255, 0, 0), 1)
        cv2.imwrite(out, c)
    elif cmd == 'profile':
        import cv2
        src, kind, at, lo, hi = a[1], a[2], int(a[3]), int(a[4]), int(a[5])
        w, dark = opt(a, '--width', 4, int), opt(a, '--dark', 80)
        im = cv2.imread(src, 0)
        strip = im[at:at + w, lo:hi].mean(0) if kind == 'row' else im[lo:hi, at:at + w].mean(1)
        hits = [(lo + i, int(255 - v)) for i, v in enumerate(strip) if 255 - v > dark]
        # group adjacent pixels into lines and print their centres
        groups, cur = [], []
        for p, v in hits:
            if cur and p - cur[-1][0] > 1:
                groups.append(cur)
                cur = []
            cur.append((p, v))
        if cur:
            groups.append(cur)
        for g in groups:
            c = sum(p * v for p, v in g) / sum(v for _, v in g)
            print('%8.1f  width %d  darkness %d' % (c, len(g), max(v for _, v in g)))
    elif cmd == 'scale':
        vals = list(map(float, a[1:]))
        for px, ft in zip(vals[::2], vals[1::2]):
            print('%8.1f px / %7.3f ft = %.3f px/ft' % (px, ft, px / ft))
    elif cmd == 'length':
        px, s = float(a[1]), opt(a, '--pxft', None)
        ft = px / s
        print(ft_in(ft), '(%.3f ft)' % ft, '= %.3f m' % (ft * 0.3048) if '--m' in a else '')


if __name__ == '__main__':
    main()
