from __future__ import annotations

from pathlib import Path

import cv2
import h5py
import numpy as np
from scipy import ndimage


def load_h5(file_path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    file_path = Path(file_path)
    with h5py.File(file_path, "r") as handle:
        kspace = handle["kspace"][:]
        rss_gt = handle["reconstruction_rss"][:]
    return kspace, rss_gt


def dataset_info(file_path: str | Path) -> dict:
    kspace, rss_gt = load_h5(file_path)
    return {
        "source_path": str(file_path),
        "kspace_shape": list(kspace.shape),
        "reconstruction_shape": list(rss_gt.shape),
        "slice_count": int(kspace.shape[0]),
        "coil_count": int(kspace.shape[1]),
        "height": int(kspace.shape[2]),
        "width": int(kspace.shape[3]),
    }


def build_undersampling_mask(width: int, acceleration: int = 1, center_fraction: float = 0.08) -> np.ndarray:
    if acceleration <= 1:
        return np.ones(width, dtype=np.float32)

    center_fraction = float(np.clip(center_fraction, 0.0, 1.0))
    center_width = max(1, int(width * center_fraction))
    start = max(0, (width - center_width) // 2)
    stop = min(width, start + center_width)

    mask = np.zeros(width, dtype=np.float32)
    mask[start:stop] = 1.0
    mask[::acceleration] = 1.0
    return mask


def normalize_image(image: np.ndarray) -> np.ndarray:
    image = np.asarray(image, dtype=np.float32)
    min_value = float(image.min())
    max_value = float(image.max())
    if max_value <= min_value:
        return np.zeros_like(image, dtype=np.float32)
    return (image - min_value) / (max_value - min_value)


def to_uint8(image: np.ndarray) -> np.ndarray:
    return np.clip(normalize_image(image) * 255.0, 0, 255).astype(np.uint8)


def reconstruct_rss(kspace_slice: np.ndarray, acceleration: int = 1, center_fraction: float = 0.08) -> tuple[np.ndarray, np.ndarray]:
    if kspace_slice.ndim != 3:
        raise ValueError("Expected k-space slice shape to be (coils, height, width)")

    mask = build_undersampling_mask(kspace_slice.shape[-1], acceleration, center_fraction)
    sampled = kspace_slice * mask[np.newaxis, np.newaxis, :]
    images = np.fft.ifft2(np.fft.ifftshift(sampled, axes=(-2, -1)))
    images = np.fft.fftshift(images, axes=(-2, -1))
    rss = np.sqrt(np.sum(np.abs(images) ** 2, axis=0)).astype(np.float32)
    return rss, sampled


def frequency_spectrum(image: np.ndarray) -> np.ndarray:
    spectrum = np.fft.fftshift(np.fft.fft2(image))
    return np.log1p(np.abs(spectrum)).astype(np.float32)


def kspace_visualization(sampled_kspace: np.ndarray) -> np.ndarray:
    return np.log1p(np.abs(sampled_kspace[0])).astype(np.float32)


def radial_frequency_profile(spectrum: np.ndarray, bins: int = 64) -> dict:
    height, width = spectrum.shape
    yy, xx = np.indices((height, width))
    cy = (height - 1) / 2.0
    cx = (width - 1) / 2.0
    radius = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    radius_norm = radius / max(radius.max(), 1.0)

    edges = np.linspace(0.0, 1.0, bins + 1)
    centers = 0.5 * (edges[:-1] + edges[1:])
    values: list[float] = []

    for index in range(bins):
        mask = (radius_norm >= edges[index]) & (radius_norm < edges[index + 1])
        if np.any(mask):
            values.append(float(np.mean(spectrum[mask])))
        else:
            values.append(0.0)

    values_array = normalize_image(np.array(values, dtype=np.float32))
    peak_index = int(np.argmax(values_array))
    return {
        "x": [float(v) for v in centers],
        "y": [float(v) for v in values_array],
        "peak_frequency": float(centers[peak_index]),
        "peak_energy": float(values_array[peak_index]),
    }


def apply_noise_removal(image: np.ndarray, method: str) -> np.ndarray:
    method = method.lower()
    if method == "none":
        return image.copy()
    if method == "gaussian":
        return ndimage.gaussian_filter(image, sigma=1.0).astype(np.float32)
    if method == "median":
        return ndimage.median_filter(image, size=3).astype(np.float32)
    raise ValueError("noise_removal must be one of: none, gaussian, median")


def apply_smoothing(image: np.ndarray, method: str) -> np.ndarray:
    method = method.lower()
    if method == "none":
        return image.copy()
    if method == "blur":
        return cv2.GaussianBlur(image.astype(np.float32), (5, 5), 0)
    if method == "bilateral":
        temp = to_uint8(image)
        filtered = cv2.bilateralFilter(temp, d=7, sigmaColor=40, sigmaSpace=40)
        return normalize_image(filtered)
    raise ValueError("smoothing must be one of: none, blur, bilateral")


def apply_contrast_enhancement(image: np.ndarray, method: str) -> np.ndarray:
    method = method.lower()
    image_u8 = to_uint8(image)
    if method == "none":
        return normalize_image(image_u8)
    if method == "histogram_equalization":
        return normalize_image(cv2.equalizeHist(image_u8))
    if method == "clahe":
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return normalize_image(clahe.apply(image_u8))
    raise ValueError("contrast_enhancement must be one of: none, histogram_equalization, clahe")


def save_png(image: np.ndarray, output_dir: str | Path, stem: str) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{stem}.png"
    success = cv2.imwrite(str(output_path), to_uint8(image))
    if not success:
        raise RuntimeError(f"Failed to save image: {output_path}")
    return output_path


def analyze_mri_slice(
    file_path: str | Path,
    output_dir: str | Path,
    slice_id: int = 5,
    acceleration: int = 1,
    center_fraction: float = 0.08,
    noise_removal: str = "gaussian",
    smoothing: str = "blur",
    contrast_enhancement: str = "clahe",
) -> dict:
    kspace, rss_gt = load_h5(file_path)
    if slice_id < 0 or slice_id >= kspace.shape[0]:
        raise IndexError(f"slice_id must be between 0 and {kspace.shape[0] - 1}")

    recon, sampled_kspace = reconstruct_rss(kspace[slice_id], acceleration, center_fraction)
    recon = normalize_image(recon)
    gt = normalize_image(rss_gt[slice_id])
    kspace_image = normalize_image(kspace_visualization(sampled_kspace))
    spectrum = normalize_image(frequency_spectrum(recon))
    profile = radial_frequency_profile(spectrum)
    denoised = normalize_image(apply_noise_removal(recon, noise_removal))
    smoothed = normalize_image(apply_smoothing(denoised, smoothing))
    enhanced = normalize_image(apply_contrast_enhancement(smoothed, contrast_enhancement))

    prefix = f"{Path(file_path).stem}_slice{slice_id}_acc{acceleration}"
    saved = {
        "reconstruction_url": f"/api/files/{save_png(recon, output_dir, prefix + '_reconstruction').name}",
        "ground_truth_url": f"/api/files/{save_png(gt, output_dir, prefix + '_ground_truth').name}",
        "kspace_url": f"/api/files/{save_png(kspace_image, output_dir, prefix + '_kspace').name}",
        "frequency_spectrum_url": f"/api/files/{save_png(spectrum, output_dir, prefix + '_frequency').name}",
        "noise_removed_url": f"/api/files/{save_png(denoised, output_dir, prefix + '_noise_removed').name}",
        "smoothed_url": f"/api/files/{save_png(smoothed, output_dir, prefix + '_smoothed').name}",
        "enhanced_url": f"/api/files/{save_png(enhanced, output_dir, prefix + '_enhanced').name}",
    }

    return {
        "source_path": str(file_path),
        "slice_id": slice_id,
        "acceleration": acceleration,
        "center_fraction": center_fraction,
        "noise_removal": noise_removal,
        "smoothing": smoothing,
        "contrast_enhancement": contrast_enhancement,
        "module_1": {
            "input": "k-space data",
            "process": "2D IFFT + FFT shift + Coil Combination (RSS)",
            "output": "Reconstructed MRI Image",
        },
        "module_2": {
            "input": "MRI image",
            "process": "2D FFT",
            "output": "Frequency spectrum (k-space visualization)",
            "graph": "Radial frequency-energy profile from low to high frequencies",
        },
        "module_3": {
            "input": "MRI image",
            "process": "Noise removal + smoothing + contrast enhancement",
            "output": "Post-processed MRI image",
        },
        "frequency_profile": profile,
        **saved,
    }
