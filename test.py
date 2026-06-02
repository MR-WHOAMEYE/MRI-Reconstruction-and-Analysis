import h5py
import matplotlib.pyplot as plt

# Load the H5 file
file = h5py.File("volume_100_slice_108.h5", "r")

# Read datasets
image = file['image'][:]
mask = file['mask'][:]

# Titles
image_titles = ["FLAIR", "T1", "T1CE", "T2"]
mask_titles = ["Whole Tumor", "Tumor Core", "Enhancing Tumor"]

plt.figure(figsize=(14,8))

# Plot MRI modalities
for i in range(4):
    plt.subplot(3,4,i+1)
    plt.imshow(image[:,:,i], cmap="gray")
    plt.title(image_titles[i])
    plt.axis("off")

# Plot tumor masks
for i in range(3):
    plt.subplot(3,4,i+5)
    plt.imshow(mask[:,:,i])
    plt.title(mask_titles[i])
    plt.axis("off")

# Overlay tumor on MRI
plt.subplot(3,4,9)
plt.imshow(image[:,:,0], cmap="gray")
plt.imshow(mask[:,:,0], alpha=0.4, cmap="jet")
plt.title("Tumor Overlay (FLAIR)")
plt.axis("off")

plt.tight_layout()
plt.show()