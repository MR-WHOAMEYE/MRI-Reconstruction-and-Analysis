from __future__ import annotations

import argparse

import matplotlib.pyplot as plt
import numpy as np

from mri_pipeline import load_h5, reconstruct_rss


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview MRI FFT reconstruction from the H5 file.")
    parser.add_argument("--file", default="2022061006_FLAIR01.h5")
    parser.add_argument("--slice", dest="slice_id", type=int, default=5)
    parser.add_argument("--acceleration", type=int, default=1)
    parser.add_argument("--center-fraction", type=float, default=0.08)
    args = parser.parse_args()

    kspace, rss_gt = load_h5(args.file)
    k = kspace[args.slice_id, 0]
    recon = reconstruct_rss(
        kspace_slice=kspace[args.slice_id],
        acceleration=args.acceleration,
        center_fraction=args.center_fraction,
    )
    recon = recon / np.max(recon)
    gt = rss_gt[args.slice_id]

    plt.figure(figsize=(12, 6))

    plt.subplot(1, 3, 1)
    plt.imshow(np.log(np.abs(k) + 1), cmap="gray")
    plt.title("k-space (log)")
    plt.axis("off")

    plt.subplot(1, 3, 2)
    plt.imshow(recon, cmap="gray")
    plt.title("FFT Reconstruction")
    plt.axis("off")

    plt.subplot(1, 3, 3)
    plt.imshow(gt, cmap="gray")
    plt.title("Ground Truth (RSS)")
    plt.axis("off")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
