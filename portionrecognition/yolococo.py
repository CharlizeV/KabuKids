import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import os
import glob
from pathlib import Path

# Deep learning imports
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    print("Warning: YOLOv8 not available. Install with: pip install ultralytics")
    YOLO_AVAILABLE = False

# COCO food-related categories (category IDs)
# This helps the model focus on relevant items
FOOD_CATEGORIES = {
    'banana': 46, 'apple': 47, 'sandwich': 48, 'orange': 49, 'broccoli': 50,
    'carrot': 51, 'hot dog': 52, 'pizza': 53, 'donut': 54, 'cake': 55,
    'bowl': 45, 'cup': 41, 'fork': 42, 'knife': 43, 'spoon': 44
}

class YOLOFoodDetector:
    def __init__(self):
        """Initialize the YOLO model"""
        if not YOLO_AVAILABLE:
            raise RuntimeError("YOLO (ultralytics) is not available. Please install it.")
        
        # Initialize YOLO
        try:
            print("Loading YOLOv8 model...")
            self.yolo_model = YOLO('yolov8m.pt')  # medium model
            print("YOLOv8 loaded successfully")
        except Exception as e:
            print(f"Failed to load YOLO model: {e}")
            raise RuntimeError(f"YOLO model loading failed: {e}")
    
    def detect_food(self, image):
        """
        Detect food items using YOLOv8, create a segmentation mask,
        and refine the mask.
        """
        try:
            results = self.yolo_model(image, verbose=False)[0]
        except Exception as e:
            print(f"YOLO detection failed: {e}")
            return np.zeros(image.shape[:2], dtype=np.uint8), []

        mask = np.zeros(image.shape[:2], dtype=np.uint8)
        detections = []
        
        if results.boxes is not None:
            boxes = results.boxes.xyxy.cpu().numpy()
            classes = results.boxes.cls.cpu().numpy().astype(int)
            confidences = results.boxes.conf.cpu().numpy()
            
            for box, cls, conf in zip(boxes, classes, confidences):
                class_name = results.names[cls]
                # Check if it's a food-related item or has high confidence
                if class_name in FOOD_CATEGORIES or conf > 0.6:
                    x1, y1, x2, y2 = map(int, box)
                    # Create a filled rectangle in the mask
                    mask[y1:y2, x1:x2] = 1
                    detections.append({
                        'class': class_name,
                        'confidence': conf,
                        'box': box
                    })
        
        # Refine the mask with morphological operations to fill holes
        kernel = np.ones((5, 5), np.uint8)
        final_mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        final_mask = cv2.morphologyEx(final_mask, cv2.MORPH_OPEN, kernel)
        
        return final_mask, detections

def load_image(path):
    """Load and optionally resize an image"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Image not found: {path}")
    
    img = cv2.imread(path)
    if img is None:
        raise ValueError(f"Could not load image: {path}")
    
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    return img

def calculate_portion_consumed(before_path, after_path, detector):
    """Calculate how much food was consumed between before and after images"""
    try:
        # Load images
        before_img = load_image(before_path)
        after_img = load_image(after_path)
        
        # Ensure images are the same size
        if before_img.shape != after_img.shape:
            print("Warning: Images are different sizes. Resizing 'after' image to match 'before'...")
            h, w = before_img.shape[:2]
            after_img = cv2.resize(after_img, (w, h))
        
        print("  Detecting food in 'before' image...")
        before_mask, before_detections = detector.detect_food(before_img)
        
        print("  Detecting food in 'after' image...")
        after_mask, after_detections = detector.detect_food(after_img)
        
        before_area = np.sum(before_mask > 0)
        after_area = np.sum(after_mask > 0)
        
        print(f"  Detected items (before): {len(before_detections)}")
        print(f"  Detected items (after): {len(after_detections)}")
        
        if before_area == 0:
            print("  Warning: No food detected in 'before' image. Cannot calculate consumption.")
            return 0, before_img, after_img, before_mask, after_mask, before_detections, after_detections
        
        consumed_area = max(0, before_area - after_area)
        portion_consumed = (consumed_area / before_area) * 100
        portion_consumed = np.clip(portion_consumed, 0, 100)
        
        return portion_consumed, before_img, after_img, before_mask, after_mask, before_detections, after_detections
        
    except Exception as e:
        print(f"  Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None, None, None, None, None

def visualize_results(portion, before_img, after_img, before_mask, after_mask, 
                     before_detections, after_detections, save_path=None):
    """Create comprehensive visualization of detection results"""
    if portion is None:
        print("Cannot visualize - analysis failed")
        return
    
    fig = plt.figure(figsize=(18, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
    
    # Original images
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.imshow(before_img)
    ax1.set_title("Before Eating", fontsize=12, fontweight='bold')
    ax1.axis('off')
    
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.imshow(after_img)
    ax2.set_title("After Eating", fontsize=12, fontweight='bold')
    ax2.axis('off')
    
    # Difference
    ax3 = fig.add_subplot(gs[0, 2])
    diff = np.abs(before_img.astype(float) - after_img.astype(float))
    ax3.imshow(diff.astype(np.uint8))
    ax3.set_title("Pixel Difference", fontsize=12, fontweight='bold')
    ax3.axis('off')
    
    # Detection masks
    ax4 = fig.add_subplot(gs[1, 0])
    ax4.imshow(before_img)
    ax4.imshow(before_mask, cmap='Reds', alpha=0.5)
    ax4.set_title(f"Before Detection\n{np.sum(before_mask):,} pixels", 
                  fontsize=12, fontweight='bold')
    ax4.axis('off')
    
    ax5 = fig.add_subplot(gs[1, 1])
    ax5.imshow(after_img)
    ax5.imshow(after_mask, cmap='Reds', alpha=0.5)
    ax5.set_title(f"After Detection\n{np.sum(after_mask):,} pixels", 
                  fontsize=12, fontweight='bold')
    ax5.axis('off')
    
    # Consumed area visualization
    ax6 = fig.add_subplot(gs[1, 2])
    consumed_mask = np.maximum(0, before_mask.astype(int) - after_mask.astype(int))
    ax6.imshow(before_img)
    ax6.imshow(consumed_mask, cmap='Greens', alpha=0.6)
    ax6.set_title(f"Consumed Area\n{np.sum(consumed_mask):,} pixels", 
                  fontsize=12, fontweight='bold')
    ax6.axis('off')
    
    # Detection details
    ax7 = fig.add_subplot(gs[2, 0])
    ax7.axis('off')
    det_text = "BEFORE DETECTIONS:\n\n"
    for i, det in enumerate(before_detections[:5], 1):
        det_text += f"{i}. {det['class']} ({det['confidence']:.2f})\n"
    ax7.text(0.1, 0.5, det_text, fontsize=10, verticalalignment='center',
             family='monospace', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))
    
    ax8 = fig.add_subplot(gs[2, 1])
    ax8.axis('off')
    det_text = "AFTER DETECTIONS:\n\n"
    for i, det in enumerate(after_detections[:5], 1):
        det_text += f"{i}. {det['class']} ({det['confidence']:.2f})\n"
    ax8.text(0.1, 0.5, det_text, fontsize=10, verticalalignment='center',
             family='monospace', bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7))
    
    # Summary statistics
    ax9 = fig.add_subplot(gs[2, 2])
    ax9.axis('off')
    consumed_pixels = max(0, np.sum(before_mask) - np.sum(after_mask))
    summary = f"═══ ANALYSIS SUMMARY ═══\n\n"
    summary += f"Before:    {np.sum(before_mask):>8,} px\n"
    summary += f"After:     {np.sum(after_mask):>8,} px\n"
    summary += f"Consumed:  {consumed_pixels:>8,} px\n"
    summary += f"─────────────────────────\n"
    summary += f"Portion Eaten:  {portion:>5.1f}%\n"
    summary += f"Remaining:      {100-portion:>5.1f}%\n\n"
    summary += f"Model Used:\n  • YOLOv8\n"
    
    ax9.text(0.05, 0.5, summary, fontsize=11, verticalalignment='center',
             family='monospace', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.suptitle(f"Food Portion Analysis: {portion:.1f}% Consumed", 
                 fontsize=18, fontweight='bold', y=0.98)
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"  Saved visualization to: {save_path}")
    
    plt.close(fig)  # Close figure to save memory

def find_image_pairs(folder="before_after"):
    """Find matching before/after image pairs"""
    if not os.path.exists(folder):
        return []
    
    pairs = []
    seen = set()  # Track processed files to avoid duplicates
    extensions = ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']
    
    # Find all "before" images
    before_files = []
    for ext in extensions:
        before_files.extend(glob.glob(os.path.join(folder, f"*_before{ext}")))
    
    for before_file in before_files:
        # Get a unique base name
        base_name = os.path.splitext(os.path.basename(before_file))[0].replace('_before', '')
        if base_name in seen:
            continue
        
        # Try to find a matching "after" file
        base = before_file.replace('_before.', '_after.')
        if not os.path.exists(base):
            base = before_file.replace('_before', '_after')
        
        # Check different extensions for the "after" file
        for ext in extensions:
            after_file = Path(base).with_suffix(ext)
            if after_file.exists():
                pairs.append((before_file, str(after_file)))
                seen.add(base_name)
                break
    
    return pairs

def main():
    print("Starting Food Portion Detection System...")
    
    # Check availability
    print(f"YOLO available: {YOLO_AVAILABLE}")
    
    if not YOLO_AVAILABLE:
        print("\nERROR: YOLO (ultralytics) is not installed!")
        print("Install with: pip install ultralytics")
        return
    
    # Create output folder
    output_folder = "yolococo_results"
    os.makedirs(output_folder, exist_ok=True)
    print(f"Output folder: {output_folder}")
    
    # Initialize detector
    try:
        detector = YOLOFoodDetector()
    except Exception as e:
        print(f"\nFailed to initialize detector: {e}")
        return
    
    # Find image pairs
    image_folder = "before_after"
    test_cases = find_image_pairs(image_folder)
    
    if not test_cases:
        print(f"\nNo image pairs found in folder: '{image_folder}'")
        print("Expected format: plate1_before.jpg, plate1_after.jpg")
        print("Supported extensions: .jpg, .jpeg, .png")
        return
    
    print(f"\nFound {len(test_cases)} image pair(s)\n")
    
    # Process each pair
    results = []
    for i, (before_path, after_path) in enumerate(test_cases, 1):
        print(f"{'─' * 70}")
        print(f"Analyzing pair {i}/{len(test_cases)}")
        print(f"  Before: {os.path.basename(before_path)}")
        print(f"  After:  {os.path.basename(after_path)}")
        
        result_tuple = calculate_portion_consumed(before_path, after_path, detector)
        portion = result_tuple[0]
        
        if portion is not None:
            print(f"  ✓ Result: {portion:.1f}% consumed")
            results.append((os.path.basename(before_path), portion))
            
            # Save visualization
            base_name = os.path.basename(before_path).replace('_before', '_result')
            base_name = os.path.splitext(base_name)[0] + '.png'
            save_path = os.path.join(output_folder, base_name)
            
            visualize_results(*result_tuple, save_path=save_path)
        else:
            print("  ✗ Analysis failed")
            results.append((os.path.basename(before_path), "Failed"))
        print()  # Extra newline
    
    # Final summary
    print(f"\n{'=' * 70}")
    print("FINAL RESULTS SUMMARY")
    print(f"{'=' * 70}")
    for filename, result in results:
        if isinstance(result, (int, float)):
            # Create a simple 20-char bar
            bar = '█' * int(result / 5) + '░' * (20 - int(result / 5))
            print(f"{filename:30s} {result:5.1f}% [{bar}]")
        else:
            print(f"{filename:30s} {result}")
    
    print(f"\n✓ All visualizations saved to: {output_folder}/")
    print(f"{'=' * 70}\n")

if __name__ == "__main__":
    main()