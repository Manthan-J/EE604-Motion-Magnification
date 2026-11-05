import cv2
import numpy as np

# --- Your Module Functions ---
def build_laplacian_pyramid(frame, levels):
    current_frame = frame.copy()
    pyramid = []
    for _ in range(levels):
        gaussian_down = cv2.pyrDown(current_frame)
        gaussian_up = cv2.pyrUp(gaussian_down, dstsize=(current_frame.shape[1], current_frame.shape[0]))
        pyramid.append(cv2.subtract(current_frame, gaussian_up))
        current_frame = gaussian_down
    pyramid.append(current_frame)
    return pyramid

def reconstruct_laplacian_pyramid(pyramid):
    current_image = pyramid[-1]
    for laplacian_level in reversed(pyramid[:-1]):
        current_image = cv2.pyrUp(current_image, dstsize=(laplacian_level.shape[1], laplacian_level.shape[0]))
        current_image = cv2.add(current_image, laplacian_level)
    return current_image

def suppress_artifacts(image, artifact_suppression=True, d=5, sigma_color=0.1, sigma_space=5):
    if not artifact_suppression:
        return image
    return cv2.bilateralFilter(image.astype(np.float32), d, sigma_color, sigma_space)

# --- The Failure Case Test ---
def run_failure_test():
    print("Starting Failure Case Test...")
    
    # 1. Create baseline frame
    frame1 = np.ones((400, 400, 3), dtype=np.float32) * 0.5
    frame1[150:250, 150:250] = 0.2  # Dark square
    
    # 2. Create a second frame with a MASSIVE shift (5 pixels)
    # This violates the small-motion assumption of EVM
    frame2 = np.ones((400, 400, 3), dtype=np.float32) * 0.5
    frame2[150:250, 155:255] = 0.2  
    
    pyr1 = build_laplacian_pyramid(frame1, levels=4)
    pyr2 = build_laplacian_pyramid(frame2, levels=4)
    
    # 3. Apply standard amplification
    alpha = 20.0
    amplified_pyr = []
    for l1, l2 in zip(pyr1, pyr2):
        amplified_pyr.append(l1 + ((l2 - l1) * alpha))
        
    reconstructed = reconstruct_laplacian_pyramid(amplified_pyr)
    
    # 4. Apply OVERLY AGGRESSIVE artifact suppression to try and fix the severe ghosting
    # We push sigma_color and sigma_space to extreme values
    output_failure = suppress_artifacts(reconstructed, artifact_suppression=True, 
                                        d=15, sigma_color=1.0, sigma_space=25)
    
    cv2.imwrite("failure_0_baseline.png", (np.clip(reconstruct_laplacian_pyramid(amplified_pyr), 0, 1) * 255).astype(np.uint8))
    cv2.imwrite("failure_1_suppressed.png", (np.clip(output_failure, 0, 1) * 255).astype(np.uint8))
    print("Test complete. Check failure_0_baseline.png and failure_1_suppressed.png.")

if __name__ == "__main__":
    run_failure_test()