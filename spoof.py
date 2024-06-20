import cv2
import numpy as np
from skimage.feature import local_binary_pattern


def detect_spoof(image_path):
    # Load the image
    image = cv2.imread(image_path)

    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Compute LBP
    radius = 3
    n_points = 8 * radius
    lbp_image = local_binary_pattern(gray, n_points, radius, method='uniform')

    # Calculate LBP histogram
    hist, _ = np.histogram(lbp_image.ravel(), bins=np.arange(0, n_points + 3), range=(0, n_points + 2))

    # Define thresholds for spoofed vs real faces based on histogram analysis
    spoof_threshold = 5000000  # Adjust as needed

    print(np.sum(hist))

    # Check if the histogram value is below the spoof threshold
    if np.sum(hist) > spoof_threshold:
        return "Real Face"
    else:
        return "Spoofed Face"


# Example usage
image_path = "/Users/abhijeetmulik/Desktop/test.jpg"
result = detect_spoof(image_path)
print("Result:", result)

