import cv2
import numpy as np

def build_laplacian_pyramid(src, levels=3):
    """
    Decomposes a video frame into a Laplacian pyramid for spatial frequency separation.
    
    Args:
        src (ndarray): The input video frame.
        levels (int): The number of pyramid levels.
        
    Returns:
        list: Spatial bands ending with the lowest-frequency Gaussian base image.
    """
    # CRITICAL FIX: Force float32 to prevent cv2.subtract from clipping negative Laplacian values to 0
    current_frame = src.astype(np.float32)
    pyramid = []
    
    for _ in range(levels):
        gaussian_down = cv2.pyrDown(current_frame)
        gaussian_up = cv2.pyrUp(gaussian_down, dstsize=(current_frame.shape[1], current_frame.shape[0]))
        
        # Use standard NumPy subtraction to allow negative pixel variations
        laplacian_level = current_frame - gaussian_up
        pyramid.append(laplacian_level)
        
        current_frame = gaussian_down
        
    # Append the final lowest-frequency Gaussian image for lossless reconstruction
    pyramid.append(current_frame)
    
    return pyramid


def reconstruct_laplacian_pyramid(pyramid):
    """
    Collapses the Laplacian pyramid to reconstruct the final image.
    
    Args:
        pyramid (list): The modified spatial bands.
        
    Returns:
        ndarray: The reconstructed output frame.
    """
    current_image = pyramid[-1]
    
    for laplacian_level in reversed(pyramid[:-1]):
        current_image = cv2.pyrUp(current_image, dstsize=(laplacian_level.shape[1], laplacian_level.shape[0]))
        # Use standard NumPy addition
        current_image = current_image + laplacian_level
        
    return current_image


def suppress_artifacts(image, artifact_suppression=True, d=5, sigma_color=0.1, sigma_space=5):
    """
    Applies optional edge-preserving bilateral smoothing to reduce ringing 
    and false-color clipping caused by high amplification factors.
    
    Args:
        image (ndarray): The reconstructed magnified frame.
        artifact_suppression (bool): Feature toggle for the ablation study.
        d (int): Diameter of each pixel neighborhood.
        sigma_color (float): Filter sigma in the color space. 
        sigma_space (float): Filter sigma in the coordinate space.
        
    Returns:
        ndarray: The filtered image.
    """
    if not artifact_suppression:
        return image
    
    # Bilateral filter requires float32 inputs
    filtered = cv2.bilateralFilter(image.astype(np.float32), d, sigma_color, sigma_space)
    return filtered