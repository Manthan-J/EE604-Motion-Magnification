import cv2
import numpy as np

def build_laplacian_pyramid(frame, levels):
    """Decomposes a video frame into a Laplacian pyramid."""
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
    """Collapses the Laplacian pyramid to reconstruct the final image."""
    current_image = pyramid[-1]
    
    for laplacian_level in reversed(pyramid[:-1]):
        current_image = cv2.pyrUp(current_image, dstsize=(laplacian_level.shape[1], laplacian_level.shape[0]))
        current_image = cv2.add(current_image, laplacian_level)
        
    return current_image

def run_baseline_test():
    print("Starting Baseline Reconstruction Test...")
    
    # 1. Load/create a single frame from a benchmark video 
    # For instant local testing without needing a video file, we generate a synthetic 
    # frame (e.g., standard 1080p resolution) with high-frequency noise.
    # To use a real image instead, uncomment the line below:
    # original_frame = cv2.imread("your_benchmark_frame.png") 
    original_frame = np.random.randint(0, 256, (1080, 1920, 3), dtype=np.uint8)
    
    # 2. Convert to float32 array
    # Eulerian processing requires float32 to capture subtle variations accurately.
    float_frame = original_frame.astype(np.float32) / 255.0
    
    # 3. Run it through build_laplacian_pyramid
    levels = 4
    pyramid = build_laplacian_pyramid(float_frame, levels=levels)
    print(f"Laplacian pyramid built with {levels} levels.")
    
    # 4. Immediately run the output through reconstruct_laplacian_pyramid
    reconstructed_frame = reconstruct_laplacian_pyramid(pyramid)
    print("Frame reconstructed from pyramid.")
    
    # 5. Subtract the reconstructed frame from the original input frame
    # Calculate the maximum absolute difference
    difference = np.abs(float_frame - reconstructed_frame)
    max_diff = np.max(difference)
    
    print("-" * 30)
    print(f"Maximum absolute difference: {max_diff:.8f}")
    
    # Evaluate against a tiny floating-point tolerance (e.g., 1e-6)
    if max_diff < 1e-6:
        print("RESULT: SUCCESS. The baseline reconstruction works flawlessly.")
    else:
        print("RESULT: FAILED. The difference is too high.")

if __name__ == "__main__":
    run_baseline_test()