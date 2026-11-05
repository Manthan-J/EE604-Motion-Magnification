import cv2
import numpy as np
import time

# --- Your Module Functions ---
def build_laplacian_pyramid(frame, levels):
    current_frame = frame.copy()
    pyramid = []
    for _ in range(levels):
        gaussian_down = cv2.pyrDown(current_frame)
        gaussian_up = cv2.pyrUp(gaussian_down, dstsize=(current_frame.shape[1], current_frame.shape[0]))
        laplacian_level = cv2.subtract(current_frame, gaussian_up)
        pyramid.append(laplacian_level)
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

# --- The Ablation Test ---
def run_ablation_test():
    print("Starting High-Alpha Ablation Test...")
    
    # 1. Create a synthetic baseline frame (gray background with a sharp dark edge)
    frame1 = np.ones((400, 400, 3), dtype=np.float32) * 0.5
    frame1[150:250, 150:250] = 0.2
    
    # Add subtle high-frequency noise (to simulate real camera sensor noise)
    noise = np.random.normal(0, 0.005, frame1.shape).astype(np.float32)
    frame1 = np.clip(frame1 + noise, 0, 1)
    
    # 2. Create a second frame with a microscopic, invisible shift (e.g., 1 pixel intensity change)
    frame2 = frame1.copy()
    frame2[150:250, 150:151] = 0.5
    
    # 3. Build spatial pyramids
    pyr1 = build_laplacian_pyramid(frame1, levels=4)
    pyr2 = build_laplacian_pyramid(frame2, levels=4)
    
    # 4. Simulate Temporal Amplification (Member 2's future job)
    alpha = 150.0  # Massive amplification factor to intentionally break the linear bounds
    amplified_pyr = []
    for l1, l2 in zip(pyr1, pyr2):
        delta = l2 - l1
        amplified_band = l1 + (delta * alpha)
        amplified_pyr.append(amplified_band)
        
    # 5. Reconstruct the amplified frame
    reconstructed = reconstruct_laplacian_pyramid(amplified_pyr)
    
    # 6. Apply Ablation Toggle (Standard EVM vs. Your Contribution)
    start_time = time.time()
    
    # Output A: Baseline (Toggle OFF - should have severe noise and ringing)
    output_baseline = suppress_artifacts(reconstructed, artifact_suppression=False)
    
    # Output B: Filtered (Toggle ON - should smooth noise but keep edges)
    output_filtered = suppress_artifacts(reconstructed, artifact_suppression=True, 
                                         d=9, sigma_color=0.15, sigma_space=9)
    
    runtime = time.time() - start_time
    print(f"Artifact Suppression Runtime: {runtime:.4f} seconds")
    
    # Save outputs to visually inspect the clipped intensities and ringing
    cv2.imwrite("ablation_0_original.png", (frame1 * 255).astype(np.uint8))
    cv2.imwrite("ablation_1_baseline_artifacts.png", (np.clip(output_baseline, 0, 1) * 255).astype(np.uint8))
    cv2.imwrite("ablation_2_suppressed_clean.png", (np.clip(output_filtered, 0, 1) * 255).astype(np.uint8))
    
    print("Test complete. Check your folder for the three ablation PNG images.")

if __name__ == "__main__":
    run_ablation_test()