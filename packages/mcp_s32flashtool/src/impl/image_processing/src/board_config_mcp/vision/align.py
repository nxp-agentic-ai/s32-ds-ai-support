# Copyright 2026 NXP
#
# NXP Proprietary. This software is owned or controlled by NXP and may
# only be used strictly in accordance with the applicable license terms.
# By expressly accepting such terms or by downloading, installing,
# activating and/or otherwise using the software, you are agreeing that
# you have read, and that you agree to comply with and are bound by,
# such license terms.  If you do not agree to be bound by the applicable
# license terms, then you may not retain, install, activate or otherwise
# use the software.

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Optional

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def _load_bgr(image_path: str):
    path = Path(image_path)
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")
    return img


def rotate_image_bound(image: np.ndarray, angle_deg: float) -> np.ndarray:
    h, w = image.shape[:2]
    cx, cy = w / 2.0, h / 2.0
    m = cv2.getRotationMatrix2D((cx, cy), angle_deg, 1.0)
    cos = abs(m[0, 0])
    sin = abs(m[0, 1])
    new_w = int((h * sin) + (w * cos))
    new_h = int((h * cos) + (w * sin))
    m[0, 2] += (new_w / 2) - cx
    m[1, 2] += (new_h / 2) - cy
    return cv2.warpAffine(image, m, (new_w, new_h))


def _normalized_gray(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)



def _orb_features(image: np.ndarray):
    gray = _normalized_gray(image)
    orb = cv2.ORB_create(nfeatures=3000)
    kp, des = orb.detectAndCompute(gray, None)
    return kp, des



def _sift_features(image: np.ndarray):
    if not hasattr(cv2, "SIFT_create"):
        return None, None
    gray = _normalized_gray(image)
    sift = cv2.SIFT_create(nfeatures=4000)
    kp, des = sift.detectAndCompute(gray, None)
    return kp, des


def _compute_features(image: np.ndarray):
    kp, des = _sift_features(image)
    if des is not None and kp is not None and len(kp) >= 8:
        return "sift", kp, des
    kp, des = _orb_features(image)
    return "orb", kp, des


def _match_descriptors(method: str, des_ref, des_qry):
    if method == "sift":
        matcher = cv2.FlannBasedMatcher(dict(algorithm=1, trees=5), dict(checks=50))
    else:
        matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    matches = matcher.knnMatch(des_qry, des_ref, k=2)
    good = []
    for pair in matches:
        if len(pair) < 2:
            continue
        m, n = pair
        if m.distance < 0.75 * n.distance:
            good.append(m)
    return good


def align_board_image(reference_image_path: str, query_image_path: str) -> dict:
    logger.info("align_board_image reference=%s query=%s", reference_image_path, query_image_path)
    ref = _load_bgr(reference_image_path)
    qry = _load_bgr(query_image_path)

    kp1, des1 = _orb_features(ref)
    kp2, des2 = _orb_features(qry)
    if des1 is None or des2 is None or len(kp1) < 8 or len(kp2) < 8:
        logger.warning("Full alignment failed: insufficient features ref_kp=%s qry_kp=%s", len(kp1) if kp1 is not None else 0, len(kp2) if kp2 is not None else 0)
        return {"success": False, "reason": "insufficient_features"}

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    matches = bf.knnMatch(des1, des2, k=2)
    good = []
    for pair in matches:
        if len(pair) < 2:
            continue
        m, n = pair
        if m.distance < 0.75 * n.distance:
            good.append(m)

    if len(good) < 8:
        logger.warning("Full alignment failed: insufficient matches good_matches=%s", len(good))
        return {"success": False, "reason": "insufficient_matches", "good_matches": len(good)}

    src_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)

    h, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
    if h is None or mask is None:
        logger.warning("Full alignment failed: homography_failed good_matches=%s", len(good))
        return {"success": False, "reason": "homography_failed", "good_matches": len(good)}

    inliers = int(mask.ravel().sum())
    score = float(inliers / max(len(good), 1))
    qh, qw = qry.shape[:2]
    qry_corners = np.float32([
        [0, 0],
        [qw - 1, 0],
        [qw - 1, qh - 1],
        [0, qh - 1],
    ]).reshape(-1, 1, 2)
    projected = cv2.perspectiveTransform(qry_corners, h).reshape(-1, 2)

    aligned = cv2.warpPerspective(qry, h, (ref.shape[1], ref.shape[0]))
    logger.debug("Full alignment success good_matches=%s inliers=%s score=%.4f", len(good), inliers, score)
    return {
        "success": True,
        "homography": h.tolist(),
        "good_matches": len(good),
        "inliers": inliers,
        "score": score,
        "query_size": [int(qw), int(qh)],
        "query_corners_in_reference": projected.astype(float).tolist(),
        "aligned_shape": [int(ref.shape[1]), int(ref.shape[0])],
        "aligned_bgr": aligned,
    }


def match_partial_region_features(reference_image_path: str, query_image_path: str) -> dict:
    logger.info("match_partial_region_features reference=%s query=%s", reference_image_path, query_image_path)
    ref = _load_bgr(reference_image_path)
    qry = _load_bgr(query_image_path)

    method_ref, kp_ref, des_ref = _compute_features(ref)
    method_qry, kp_qry, des_qry = _compute_features(qry)

    if des_ref is None or des_qry is None or kp_ref is None or kp_qry is None:
        logger.warning("Partial feature match failed: insufficient features")
        return {"success": False, "reason": "insufficient_features"}
    if len(kp_ref) < 8 or len(kp_qry) < 8:
        logger.warning("Partial feature match failed: insufficient keypoints ref=%s qry=%s", len(kp_ref), len(kp_qry))
        return {"success": False, "reason": "insufficient_keypoints", "ref_keypoints": len(kp_ref), "qry_keypoints": len(kp_qry)}

    method = "sift" if method_ref == "sift" and method_qry == "sift" else "orb"
    if method == "orb" and (method_ref != "orb" or method_qry != "orb"):
        method = method_ref if method_ref == method_qry else "orb"

    good = _match_descriptors(method, des_ref, des_qry)
    if len(good) < 8:
        logger.warning("Partial feature match failed: insufficient matches method=%s good_matches=%s", method, len(good))
        return {
            "success": False,
            "reason": "insufficient_matches",
            "method": method,
            "good_matches": len(good),
            "ref_keypoints": len(kp_ref),
            "qry_keypoints": len(kp_qry),
        }

    src_pts = np.float32([kp_qry[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp_ref[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

    h, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
    if h is None or mask is None:
        logger.warning("Partial feature match failed: homography_failed method=%s good_matches=%s", method, len(good))
        return {"success": False, "reason": "homography_failed", "method": method, "good_matches": len(good)}

    inliers = int(mask.ravel().sum())
    if inliers < 6:
        logger.warning("Partial feature match failed: insufficient inliers method=%s good_matches=%s inliers=%s", method, len(good), inliers)
        return {
            "success": False,
            "reason": "insufficient_inliers",
            "method": method,
            "good_matches": len(good),
            "inliers": inliers,
        }

    qh, qw = qry.shape[:2]
    qry_corners = np.float32([
        [0, 0],
        [qw - 1, 0],
        [qw - 1, qh - 1],
        [0, qh - 1],
    ]).reshape(-1, 1, 2)
    projected = cv2.perspectiveTransform(qry_corners, h).reshape(-1, 2)

    aligned = cv2.warpPerspective(qry, h, (ref.shape[1], ref.shape[0]))
    score = float(inliers / max(len(good), 1))
    logger.debug("Partial feature match success method=%s good_matches=%s inliers=%s score=%.4f", method, len(good), inliers, score)

    return {
        "success": True,
        "method": method,
        "homography": h.tolist(),
        "good_matches": len(good),
        "inliers": inliers,
        "score": score,
        "query_size": [int(qw), int(qh)],
        "query_corners_in_reference": projected.astype(float).tolist(),
        "aligned_shape": [int(ref.shape[1]), int(ref.shape[0])],
        "aligned_bgr": aligned,
    }


def align_image_to_reference(reference_image_path: str, query_image_path: str, output_path: Optional[str] = None) -> dict:
    result = align_board_image(reference_image_path, query_image_path)
    if not result.get("success"):
        return result
    result = dict(result)
    if output_path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output), result["aligned_bgr"])
        result["aligned_image_path"] = str(output)
    result.pop("aligned_bgr", None)
    return result


def save_aligned_image(reference_image_path: str, query_image_path: str, output_path: str) -> dict:
    result = align_image_to_reference(reference_image_path, query_image_path, output_path)
    if result.get("aligned_image_path") and "output_path" not in result:
        result["output_path"] = result["aligned_image_path"]
    return result


def crop_bbox_from_image(image_path: str, bbox: Iterable[int], output_path: Optional[str] = None) -> dict:
    img = Image.open(image_path).convert("RGB")
    x, y, w, h = [int(v) for v in bbox]
    crop = img.crop((x, y, x + w, y + h))
    if output_path:
        out = Path(output_path)
    else:
        src = Path(image_path)
        out = src.with_name(src.stem + f"_crop_{x}_{y}_{w}_{h}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    crop.save(out)
    return {"output_path": str(out), "size": [crop.width, crop.height]}
