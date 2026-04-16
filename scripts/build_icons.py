"""
One-shot builder: downloads Minecraft icons, upscales with nearest-neighbor
to 256x256, writes to stats/assets/icons/. Uses pure Python stdlib.

Run once after changing the ICONS dict below. Commit the output PNGs.
"""

import struct
import zlib
import sys
from pathlib import Path
from urllib.request import urlopen, Request

_MI = 'https://cdn.jsdelivr.net/gh/InventivetalentDev/minecraft-assets@1.21.5/assets/minecraft/textures/item/'
_MB = 'https://cdn.jsdelivr.net/gh/InventivetalentDev/minecraft-assets@1.21.5/assets/minecraft/textures/block/'
# Wiki "Special:FilePath" auto-redirects to the thumbnail at the requested width.
# Files listed in WIKI_HIRES exist as native 300x300 3D renders (not pixel art upscales).
_WIKI_THUMB = 'https://minecraft.wiki/wiki/Special:FilePath/{filename}?width=256'

# name -> (source_url, expected_native_size)
# Icons at native 16x16 get ×16 upscale, at 32x32 get ×8 — all end at 256x256.
ICONS = {
    # Items (16x16 native)
    'diamond_pickaxe': (_MI + 'diamond_pickaxe.png', 16),
    'diamond_axe': (_MI + 'diamond_axe.png', 16),
    'diamond_sword': (_MI + 'diamond_sword.png', 16),
    'netherite_sword': (_MI + 'netherite_sword.png', 16),
    'iron_sword': (_MI + 'iron_sword.png', 16),
    'iron_chestplate': (_MI + 'iron_chestplate.png', 16),
    'bow': (_MI + 'bow.png', 16),
    'crossbow': (_MI + 'crossbow_standby.png', 16),
    'elytra': (_MI + 'elytra.png', 16),
    'fishing_rod': (_MI + 'fishing_rod.png', 16),
    'diamond': (_MI + 'diamond.png', 16),
    'blaze_rod': (_MI + 'blaze_rod.png', 16),
    'ender_pearl': (_MI + 'ender_pearl.png', 16),
    'emerald': (_MI + 'emerald.png', 16),
    'nether_star': (_MI + 'nether_star.png', 16),
    'golden_apple': (_MI + 'golden_apple.png', 16),
    'paper': (_MI + 'paper.png', 16),
    'saddle': (_MI + 'saddle.png', 16),
    'clock': (_MI + 'clock_00.png', 16),
    'compass': (_MI + 'compass_00.png', 16),
    'filled_map': (_MI + 'filled_map.png', 16),
    'enchanted_book': (_MI + 'enchanted_book.png', 16),
    'feather': (_MI + 'feather.png', 16),
    'wheat': (_MI + 'wheat.png', 16),
    'wheat_seeds': (_MI + 'wheat_seeds.png', 16),
    'rabbit_foot': (_MI + 'rabbit_foot.png', 16),
    'leather_boots': (_MI + 'leather_boots.png', 16),
    'diamond_boots': (_MI + 'diamond_boots.png', 16),
    'gold_ingot': (_MI + 'gold_ingot.png', 16),
    'iron_ingot': (_MI + 'iron_ingot.png', 16),
    'copper_ingot': (_MI + 'copper_ingot.png', 16),
    'rotten_flesh': (_MI + 'rotten_flesh.png', 16),
    'totem_of_undying': (_MI + 'totem_of_undying.png', 16),
    'oak_boat': (_MI + 'oak_boat.png', 16),
    'egg': (_MI + 'egg.png', 16),
    'cod': (_MI + 'cod.png', 16),
    'oak_door': (_MI + 'oak_door.png', 16),
    # Blocks (16x16 native)
    'torch': (_MB + 'torch.png', 16),
    'oak_sapling': (_MB + 'oak_sapling.png', 16),
}

# Wiki hi-res 3D renders — saved as-is (no upscale). Filenames include
# version suffix because the wiki stores per-version renders.
# Shield.png is front+back stacked vertically; we crop to the top half.
WIKI_HIRES = {
    'shield': 'Shield.png',
    'skeleton_skull': 'Skeleton_Skull.png',
    'oak_planks': 'Oak_Planks.png',
    'netherrack': 'Netherrack.png',
    'ancient_debris': 'Ancient_Debris.png',
    'crafting_table': 'Crafting_Table_JE4_BE3.png',
    'chest': 'Chest.png',
    'white_bed': 'White_Bed_JE3_BE3.png',
    'anvil': 'Anvil_JE3_BE3.png',
    'tnt': 'TNT.png',
    'target': 'Target.png',
}

TARGET_SIZE = 256
OUT_DIR = Path(__file__).resolve().parent.parent / 'stats' / 'assets' / 'icons'

BPP = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}


def parse_png(data):
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('Not a PNG')
    pos = 8
    width = height = bit_depth = color_type = None
    palette = None
    trns = None
    idat = []
    while pos < len(data):
        length = struct.unpack('>I', data[pos:pos + 4])[0]
        ctype = data[pos + 4:pos + 8]
        content = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if ctype == b'IHDR':
            width, height, bit_depth, color_type = struct.unpack('>IIBB', content[:10])
            compression, filter_m, interlace = struct.unpack('BBB', content[10:13])
            if compression != 0 or filter_m != 0 or interlace != 0:
                raise ValueError('Unsupported PNG encoding')
        elif ctype == b'PLTE':
            palette = content
        elif ctype == b'tRNS':
            trns = content
        elif ctype == b'IDAT':
            idat.append(content)
        elif ctype == b'IEND':
            break
    raw = zlib.decompress(b''.join(idat))
    return width, height, bit_depth, color_type, palette, trns, raw


def unfilter(raw, width, height, bpp, row_len):
    out = bytearray(row_len * height)
    prev = bytearray(row_len)
    pos = 0
    for y in range(height):
        ft = raw[pos]
        pos += 1
        row = bytearray(raw[pos:pos + row_len])
        pos += row_len
        if ft == 0:
            pass
        elif ft == 1:  # Sub
            for x in range(bpp, row_len):
                row[x] = (row[x] + row[x - bpp]) & 0xFF
        elif ft == 2:  # Up
            for x in range(row_len):
                row[x] = (row[x] + prev[x]) & 0xFF
        elif ft == 3:  # Average
            for x in range(row_len):
                a = row[x - bpp] if x >= bpp else 0
                row[x] = (row[x] + (a + prev[x]) // 2) & 0xFF
        elif ft == 4:  # Paeth
            for x in range(row_len):
                a = row[x - bpp] if x >= bpp else 0
                b = prev[x]
                c = prev[x - bpp] if x >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                row[x] = (row[x] + pr) & 0xFF
        else:
            raise ValueError(f'Unknown filter {ft}')
        out[y * row_len:(y + 1) * row_len] = row
        prev = row
    return bytes(out)


def unpack_indices(pixels, width, height, bit_depth):
    """Unpack sub-byte palette indices (bit_depth < 8) to one index per byte."""
    if bit_depth == 8:
        return pixels
    row_bytes_in = (width * bit_depth + 7) // 8
    out = bytearray(width * height)
    mask = (1 << bit_depth) - 1
    per_byte = 8 // bit_depth
    for y in range(height):
        src = pixels[y * row_bytes_in:(y + 1) * row_bytes_in]
        dst_off = y * width
        for x in range(width):
            byte_idx = x // per_byte
            shift = 8 - bit_depth - (x % per_byte) * bit_depth
            out[dst_off + x] = (src[byte_idx] >> shift) & mask
    return bytes(out)


def to_rgba(pixels, w, h, bit_depth, color_type, palette, trns):
    n = w * h
    out = bytearray(n * 4)
    if color_type == 6:
        if bit_depth != 8:
            raise ValueError(f'RGBA bit_depth {bit_depth} unsupported')
        return pixels
    if color_type == 2:
        if bit_depth != 8:
            raise ValueError(f'RGB bit_depth {bit_depth} unsupported')
        for i in range(n):
            out[i * 4:i * 4 + 3] = pixels[i * 3:i * 3 + 3]
            out[i * 4 + 3] = 255
    elif color_type == 3:
        indices = unpack_indices(pixels, w, h, bit_depth)
        for i in range(n):
            idx = indices[i]
            out[i * 4:i * 4 + 3] = palette[idx * 3:idx * 3 + 3]
            out[i * 4 + 3] = trns[idx] if trns and idx < len(trns) else 255
    elif color_type == 4:
        if bit_depth != 8:
            raise ValueError(f'GrayA bit_depth {bit_depth} unsupported')
        for i in range(n):
            g = pixels[i * 2]
            out[i * 4:i * 4 + 3] = bytes([g, g, g])
            out[i * 4 + 3] = pixels[i * 2 + 1]
    elif color_type == 0:
        if bit_depth != 8:
            raise ValueError(f'Gray bit_depth {bit_depth} unsupported')
        for i in range(n):
            g = pixels[i]
            out[i * 4:i * 4 + 3] = bytes([g, g, g])
            out[i * 4 + 3] = 255
    else:
        raise ValueError(f'Unsupported color type {color_type}')
    return bytes(out)


def upscale_nn(rgba, width, height, factor):
    new_w = width * factor
    row_bytes_src = width * 4
    row_bytes_dst = new_w * 4
    out = bytearray(row_bytes_dst * height * factor)
    for sy in range(height):
        src_row = rgba[sy * row_bytes_src:(sy + 1) * row_bytes_src]
        expanded = bytearray(row_bytes_dst)
        for sx in range(width):
            px = src_row[sx * 4:sx * 4 + 4]
            base = sx * factor * 4
            for k in range(factor):
                expanded[base + k * 4:base + k * 4 + 4] = px
        for k in range(factor):
            out[(sy * factor + k) * row_bytes_dst:(sy * factor + k + 1) * row_bytes_dst] = expanded
    return bytes(out), new_w, height * factor


def write_rgba_png(pixels, width, height):
    row_len = width * 4
    filtered = bytearray()
    for y in range(height):
        filtered.append(0)
        filtered.extend(pixels[y * row_len:(y + 1) * row_len])
    idat = zlib.compress(bytes(filtered), 9)

    def chunk(ctype, data):
        crc = zlib.crc32(ctype + data)
        return struct.pack('>I', len(data)) + ctype + data + struct.pack('>I', crc)

    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
    png += chunk(b'IDAT', idat)
    png += chunk(b'IEND', b'')
    return png


def upscale_png_bytes(data, factor):
    w, h, bd, ct, pal, trns, raw = parse_png(data)
    samples = BPP[ct]  # samples per pixel
    bits_per_pixel = samples * bd
    bpp = max(1, bits_per_pixel // 8)  # for filter purposes
    row_len = (w * bits_per_pixel + 7) // 8
    pixels = unfilter(raw, w, h, bpp, row_len)
    rgba = to_rgba(pixels, w, h, bd, ct, pal, trns)
    up, nw, nh = upscale_nn(rgba, w, h, factor)
    return write_rgba_png(up, nw, nh), w, h


def decode_to_rgba(data):
    w, h, bd, ct, pal, trns, raw = parse_png(data)
    samples = BPP[ct]
    bpp = max(1, samples * bd // 8)
    row_len = (w * samples * bd + 7) // 8
    pixels = unfilter(raw, w, h, bpp, row_len)
    return to_rgba(pixels, w, h, bd, ct, pal, trns), w, h


def find_bbox(rgba, w, h, alpha_threshold=16):
    min_x, min_y, max_x, max_y = w, h, -1, -1
    for y in range(h):
        row_off = y * w * 4
        for x in range(w):
            if rgba[row_off + x * 4 + 3] > alpha_threshold:
                if x < min_x:
                    min_x = x
                if y < min_y:
                    min_y = y
                if x > max_x:
                    max_x = x
                if y > max_y:
                    max_y = y
    if max_x < 0:
        return 0, 0, w, h
    return min_x, min_y, max_x + 1, max_y + 1


def normalize_to_ratio(rgba, w, h, target_ratio=0.85, out_size=256):
    """Crop to opaque bbox, recenter on a square transparent canvas so that
    max(bbox_w, bbox_h) == target_ratio * out_size. Nearest-neighbor resample."""
    x0, y0, x1, y1 = find_bbox(rgba, w, h)
    bw, bh = x1 - x0, y1 - y0
    if bw == 0 or bh == 0:
        return rgba, w, h
    scale = (target_ratio * out_size) / max(bw, bh)
    new_bw = max(1, round(bw * scale))
    new_bh = max(1, round(bh * scale))
    content = bytearray(new_bw * new_bh * 4)
    for ny in range(new_bh):
        sy = y0 + min(bh - 1, int(ny * bh / new_bh))
        src_row_off = sy * w * 4
        dst_row_off = ny * new_bw * 4
        for nx in range(new_bw):
            sx = x0 + min(bw - 1, int(nx * bw / new_bw))
            content[dst_row_off + nx * 4:dst_row_off + nx * 4 + 4] = rgba[src_row_off + sx * 4:src_row_off + sx * 4 + 4]
    canvas = bytearray(out_size * out_size * 4)
    dx = (out_size - new_bw) // 2
    dy = (out_size - new_bh) // 2
    for ny in range(new_bh):
        dst_off = ((dy + ny) * out_size + dx) * 4
        src_off = ny * new_bw * 4
        canvas[dst_off:dst_off + new_bw * 4] = content[src_off:src_off + new_bw * 4]
    return bytes(canvas), out_size, out_size


def fetch(url):
    req = Request(url, headers={'User-Agent': 'minecraft-stats-dashboard-builder/1.0'})
    with urlopen(req, timeout=30) as r:
        return r.read()


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    errors = []
    total = len(ICONS) + len(WIKI_HIRES)
    # Native low-res textures: nearest-neighbor upscale to 256x256.
    for name, (url, expected_native) in ICONS.items():
        out_path = OUT_DIR / f'{name}.png'
        if out_path.exists():
            print(f'[SKIP] {name} (already exists)')
            continue
        try:
            print(f'[FETCH] {name} <- {url}')
            data = fetch(url)
            factor = TARGET_SIZE // expected_native
            png_bytes, src_w, src_h = upscale_png_bytes(data, factor)
            if src_w != expected_native or src_h != expected_native:
                print(f'  [WARN] {name}: expected {expected_native}x{expected_native}, got {src_w}x{src_h}')
            out_path.write_bytes(png_bytes)
            print(f'  -> {out_path.relative_to(OUT_DIR.parent.parent.parent)} ({len(png_bytes)} bytes)')
        except Exception as e:
            print(f'  [ERR] {name}: {e}')
            errors.append((name, e))
    # Wiki hi-res 3D renders: saved as-is from Special:FilePath thumbnail.
    # Non-square results are cropped to their top square (e.g. shield shows front+back stacked).
    for name, filename in WIKI_HIRES.items():
        out_path = OUT_DIR / f'{name}.png'
        if out_path.exists():
            print(f'[SKIP] {name} (already exists)')
            continue
        url = _WIKI_THUMB.format(filename=filename)
        try:
            print(f'[FETCH] {name} <- {url}')
            data = fetch(url)
            w, h, bd, ct, pal, trns, raw = parse_png(data)
            if w != h:
                # Tall/wide images (e.g. shield = front+back stacked): take top half,
                # then pass through — normalize pass will auto-center to square.
                samples = BPP[ct]
                bpp = max(1, samples * bd // 8)
                row_len = (w * samples * bd + 7) // 8
                pixels = unfilter(raw, w, h, bpp, row_len)
                rgba = to_rgba(pixels, w, h, bd, ct, pal, trns)
                keep_h = h // 2 if h > w else h
                keep_w = w // 2 if w > h else w
                cropped = bytearray(keep_w * keep_h * 4)
                for y in range(keep_h):
                    cropped[y * keep_w * 4:(y + 1) * keep_w * 4] = rgba[y * w * 4:y * w * 4 + keep_w * 4]
                data = write_rgba_png(bytes(cropped), keep_w, keep_h)
                print(f'  (cropped {w}x{h} -> {keep_w}x{keep_h})')
            out_path.write_bytes(data)
            print(f'  -> {out_path.relative_to(OUT_DIR.parent.parent.parent)} ({len(data)} bytes)')
        except Exception as e:
            print(f'  [ERR] {name}: {e}')
            errors.append((name, e))
    # Post-process: normalize every icon so opaque content occupies the same
    # fraction of its canvas. Without this, 3D block renders (edge-to-edge)
    # appear massively larger than 2D sprites (padded).
    print('\n[NORMALIZE] Re-centering all icons to consistent content ratio...')
    for png_path in sorted(OUT_DIR.glob('*.png')):
        try:
            data = png_path.read_bytes()
            rgba, w, h = decode_to_rgba(data)
            new_rgba, nw, nh = normalize_to_ratio(rgba, w, h, target_ratio=0.85, out_size=TARGET_SIZE)
            png_path.write_bytes(write_rgba_png(new_rgba, nw, nh))
        except Exception as e:
            print(f'  [ERR] {png_path.name}: {e}')
    print(f'\n[DONE] {total - len(errors)}/{total} icons ready in {OUT_DIR}')
    if errors:
        print(f'[FAILED] {len(errors)}:')
        for name, e in errors:
            print(f'  - {name}: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
