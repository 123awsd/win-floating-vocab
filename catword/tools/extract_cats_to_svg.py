import argparse
import base64
import io
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def imread_unicode(path: Path):
    data = np.fromfile(str(path), dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def find_components(mask: np.ndarray, min_area: int, min_w: int, min_h: int):
    num, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    components = []
    for idx in range(1, num):
        x, y, w, h, area = stats[idx]
        if area < min_area or w < min_w or h < min_h:
            continue
        components.append((idx, x, y, w, h))
    components.sort(key=lambda c: (c[2], c[1]))
    return components, labels


def trim_alpha(arr: np.ndarray):
    alpha = arr[:, :, 3]
    ys, xs = np.where(alpha > 0)
    if len(xs) == 0 or len(ys) == 0:
        return arr
    x0, x1 = xs.min(), xs.max() + 1
    y0, y1 = ys.min(), ys.max() + 1
    return arr[y0:y1, x0:x1]


def quality_ok(rgba: np.ndarray):
    h, w = rgba.shape[:2]
    if h < 70 or w < 70:
        return False

    alpha = rgba[:, :, 3] > 0
    area = int(alpha.sum())
    bbox_area = h * w
    if area < 2800:
        return False

    fill_ratio = area / float(bbox_area)
    # too sparse -> likely broken strokes; too dense -> likely merged/boxy crop.
    if fill_ratio < 0.18 or fill_ratio > 0.9:
        return False

    ys, xs = np.where(alpha)
    if len(xs) == 0 or len(ys) == 0:
        return False
    span_w = xs.max() - xs.min() + 1
    span_h = ys.max() - ys.min() + 1
    aspect = span_w / float(span_h)
    if aspect < 0.38 or aspect > 1.95:
        return False

    # Ensure silhouette has meaningful upper content (avoid body-only fragments).
    top_band = alpha[: max(1, int(h * 0.2)), :]
    if top_band.sum() < area * 0.035:
        return False

    # Ensure lower content exists (avoid head-only fragments).
    bottom_band = alpha[int(h * 0.65) :, :]
    if bottom_band.sum() < area * 0.11:
        return False

    return True


def rgba_to_embedded_svg(rgba: np.ndarray, out_svg: Path):
    image = Image.fromarray(rgba, mode="RGBA")
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    payload = base64.b64encode(buf.getvalue()).decode("ascii")
    w, h = image.size
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}">'
        f'<image width="{w}" height="{h}" href="data:image/png;base64,{payload}" />'
        f"</svg>"
    )
    out_svg.write_text(svg, encoding="utf-8")


def rgba_to_png(rgba: np.ndarray, out_png: Path):
    Image.fromarray(rgba, mode="RGBA").save(out_png, format="PNG")


def robust_alpha_from_crop(crop_bgr: np.ndarray):
    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)

    # 1) Foreground ink/pixels: keep all non-white pixels.
    ink = (gray < 245).astype(np.uint8)

    # 2) Repair broken outlines (force close) so inside region won't leak out.
    h, w = ink.shape
    k = max(3, int(min(h, w) * 0.03))
    if k % 2 == 0:
        k += 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    repaired = cv2.morphologyEx(ink * 255, cv2.MORPH_CLOSE, kernel, iterations=2)
    repaired = cv2.dilate(repaired, np.ones((3, 3), np.uint8), iterations=1)
    repaired = (repaired > 0).astype(np.uint8)

    # 3) Background reconstruction by border-connectivity:
    #    white pixels connected to border are background;
    #    enclosed whites are interior details and must be kept.
    traversable = (1 - repaired).astype(np.uint8)
    num, labels, _, _ = cv2.connectedComponentsWithStats(traversable, connectivity=8)
    outside_ids = set(np.unique(labels[0, :]).tolist())
    outside_ids.update(np.unique(labels[-1, :]).tolist())
    outside_ids.update(np.unique(labels[:, 0]).tolist())
    outside_ids.update(np.unique(labels[:, -1]).tolist())
    outside = np.isin(labels, list(outside_ids))
    inside_white = (traversable == 1) & (~outside)

    alpha = np.where((ink == 1) | inside_white, 255, 0).astype(np.uint8)
    return alpha


def extract_one_image(image_path: Path, out_dir: Path, start_index: int):
    bgr = imread_unicode(image_path)
    if bgr is None:
        return start_index

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    mask = (gray < 245).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8), iterations=1)

    components, labels = find_components(mask, min_area=2500, min_w=70, min_h=70)
    rgba = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGBA)
    idx = start_index

    for comp_idx, x, y, w, h in components:
        pad = 8
        x0 = max(0, x - pad)
        y0 = max(0, y - pad)
        x1 = min(bgr.shape[1], x + w + pad)
        y1 = min(bgr.shape[0], y + h + pad)

        crop = rgba[y0:y1, x0:x1].copy()
        crop_bgr = bgr[y0:y1, x0:x1]

        local_label = labels[y0:y1, x0:x1]
        target_present = (local_label == comp_idx).any()
        if not target_present:
            continue

        alpha = robust_alpha_from_crop(crop_bgr)
        crop[:, :, 3] = alpha
        crop = trim_alpha(crop)

        if crop.shape[0] < 60 or crop.shape[1] < 60:
            continue
        if not quality_ok(crop):
            continue

        stem = f"cat_{idx:03d}"
        rgba_to_png(crop, out_dir / f"{stem}.png")
        rgba_to_embedded_svg(crop, out_dir / f"{stem}.svg")
        idx += 1

    return idx


def main():
    parser = argparse.ArgumentParser(
        description="Extract single cats from montage images with broken-outline fix."
    )
    parser.add_argument("--input-dir", default="鏈鐞嗙殑绱犳潗", help="Source image directory")
    parser.add_argument(
        "--output-dir",
        default="py绋嬪簭/assets/cattoon_v1/cats",
        help="Output directory for cat assets",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for old in output_dir.glob("cat_*.*"):
        if old.suffix.lower() in {".svg", ".png"}:
            old.unlink()

    images = sorted(
        [
            p
            for p in input_dir.iterdir()
            if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        ],
        key=lambda p: p.name.lower(),
    )

    index = 0
    for image in images:
        index = extract_one_image(image, output_dir, index)

    print(f"extracted {index} cats into: {output_dir}")


if __name__ == "__main__":
    main()

