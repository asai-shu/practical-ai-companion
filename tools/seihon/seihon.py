"""見開きスキャンPDFを、影を消して左右のページに分け、読みやすいPDFにまとめる。

使い方: python3 seihon.py 入力.pdf 出力.pdf
"""
import io
import sys

import cv2
import img2pdf
import numpy as np
import pymupdf


def page_images(pdf_path):
    doc = pymupdf.open(pdf_path)
    for page in doc:
        xref = page.get_images()[0][0]
        data = doc.extract_image(xref)["image"]
        img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_GRAYSCALE)
        yield img


def find_gutter(gray):
    """見開きのとじ目（中央付近でいちばん暗い縦の列）を探す。"""
    h, w = gray.shape
    lo, hi = int(w * 0.4), int(w * 0.6)
    cols = cv2.blur(gray, (25, 1))[int(h * 0.1):int(h * 0.9), lo:hi].mean(axis=0)
    return lo + int(np.argmin(cols))


def remove_shadow(gray):
    """文字を消した「背景」を推定し、それで割って影や紙の色むらを消す。"""
    bg = cv2.dilate(gray, np.ones((15, 15), np.uint8))
    bg = cv2.medianBlur(bg, 51)
    norm = cv2.divide(gray, bg, scale=255)
    # 薄いグレーは白に、文字は少し濃く
    lut = np.clip((np.arange(256) - 60) * 255.0 / (225 - 60), 0, 255)
    lut = (255 * (lut / 255) ** 1.4).astype(np.uint8)
    return cv2.LUT(norm, lut)


def deskew(img):
    """文字の行がいちばん水平になる角度（±3度）を探して回転する。"""
    small = cv2.resize(img, None, fx=0.25, fy=0.25)
    ink = (small < 128).astype(np.uint8)
    best, best_score = 0.0, -1
    h, w = ink.shape
    for a in np.arange(-3, 3.01, 0.1):
        m = cv2.getRotationMatrix2D((w / 2, h / 2), a, 1)
        rows = cv2.warpAffine(ink, m, (w, h)).sum(axis=1).astype(float)
        score = np.var(rows)
        if score > best_score:
            best, best_score = a, score
    if abs(best) < 0.05:
        return img
    h, w = img.shape
    m = cv2.getRotationMatrix2D((w / 2, h / 2), best, 1)
    return cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_CUBIC, borderValue=255)


def main(src, dst):
    pages = []
    for gray in page_images(src):
        g = find_gutter(gray)
        for half in (gray[:, :g], gray[:, g:]):
            out = deskew(remove_shadow(half))
            # 本の端の影が残りやすい外周を白くする（本文には届かない幅）
            mh, mw = int(out.shape[0] * 0.02), int(out.shape[1] * 0.025)
            out[:mh, :] = 255; out[-mh:, :] = 255; out[:, :mw] = 255; out[:, -mw:] = 255
            ok, buf = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, 85])
            pages.append(buf.tobytes())
    with open(dst, "wb") as f:
        f.write(img2pdf.convert(pages, layout_fun=img2pdf.get_fixed_dpi_layout_fun((300, 300))))
    print(dst, len(pages), "pages")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
