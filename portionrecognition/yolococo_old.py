import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import os
import glob
from pathlib import Path
import torch
from torchvision.ops import box_iou

# Deep learning imports
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    print("Warning: YOLOv8 not available. Install with: pip install ultralytics")
    YOLO_AVAILABLE = False

try:
    from detectron2 import model_zoo
    from detectron2.engine import DefaultPredictor
    from detectron2.config import get_cfg
    from detectron2.utils.visualizer import Visualizer
    from detectron2.data import MetadataCatalog
    DETECTRON2_AVAILABLE = True
except ImportError:
    print("Warning: Detectron2 not available.")
    print("  Option 1 (Build from source): pip install 'git+https://github.com/facebookresearch/detectron2.git'")
    print("  Option 2 (Continue with YOLO only): The program will work fine with just YOLO")
    DETECTRON2_AVAILABLE = False

# COCO food-related categories (category IDs)
FOOD_CATEGORIES = {
    'banana': 46, 'apple': 47, 'sandwich': 48, 'orange': 49, 'broccoli': 50,
    'carrot': 51, 'hot dog': 52, 'pizza': 53, 'donut': 54, 'cake': 55,
    'bowl': 45, 'cup': 41, 'fork': 42, 'knife': 43, 'spoon': 44
}

class MLFoodDetector:
    def __init__(self, use_yolo=True, use_detectron2=True):
        """Initialize both YOLO and Detectron2 models"""
        self.use_yolo = use_yolo and YOLO_AVAILABLE
        self.use_detectron2 = use_detectron2 and DETECTRON2_AVAILABLE
        
        if not self.use_yolo and not self.use_detectron2:
            raise RuntimeError("Neither YOLO nor Detectron2 is available. Please install at least one.")
        
        # Initialize YOLO
        if self.use_yolo:
            try:
                print("Loading YOLOv8 model...")
                self.yolo_model = YOLO('yolov8m.pt')  # medium model for balance
                print("YOLOv8 loaded successfully")
            except Exception as e:
                print(f"Failed to load YOLO: {e}")
                self.use_yolo = False
        
        # Initialize Detectron2
        if self.use_detectron2:
            try:
                print("Loading Detectron2 model...")
                cfg = get_cfg()
                cfg.merge_from_file(model_zoo.get_config_file(
                    "COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"
                ))
                cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.5
                cfg.MODEL.WEIGHTS = model_zoo.get_checkpoint_url(
                    "COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"
                )
                cfg.MODEL.DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
                self.detectron2_predictor = DefaultPredictor(cfg)
                self.detectron2_metadata = MetadataCatalog.get(cfg.DATASETS.TRAIN[0])
                print(f"Detectron2 loaded successfully (using {cfg.MODEL.DEVICE})")
            except Exception as e:
                print(f"Failed to load Detectron2: {e}")
                self.use_detectron2 = False
    
    def detect_with_yolo(self, image):
        """Detect objects using YOLO and create segmentation mask"""
        results = self.yolo_model(image, verbose=False)[0]
        
        mask = np.zeros(image.shape[:2], dtype=np.uint8)
        detections = []
        
        if results.boxes is not None:
            boxes = results.boxes.xyxy.cpu().numpy()
            classes = results.boxes.cls.cpu().numpy().astype(int)
            confidences = results.boxes.conf.cpu().numpy()
            
            for box, cls, conf in zip(boxes, classes, confidences):
                class_name = results.names[cls]
                # Check if it's a food-related item
                if class_name in FOOD_CATEGORIES or conf > 0.6:
                    x1, y1, x2, y2 = map(int, box)
                    # Create a filled rectangle in the mask
                    mask[y1:y2, x1:x2] = 1
                    detections.append({
                        'class': class_name,
                        'confidence': conf,
                        'box': box
                    })
        
        return mask, detections
    
    def detect_with_detectron2(self, image):
        """Detect objects using Detectron2 with instance segmentation"""
        outputs = self.detectron2_predictor(image)
        
        instances = outputs["instances"].to("cpu")
        mask = np.zeros(image.shape[:2], dtype=np.uint8)
        detections = []
        
        if len(instances) > 0:
            pred_classes = instances.pred_classes.numpy()
            scores = instances.scores.numpy()
            
            # Check if masks are available
            if instances.has("pred_masks"):
                pred_masks = instances.pred_masks.numpy()
                
                for i, (cls, score, pred_mask) in enumerate(zip(pred_classes, scores, pred_masks)):
                    class_name = self.detectron2_metadata.thing_classes[cls]
                    
                    # Focus on food-related items
                    if class_name in FOOD_CATEGORIES or score > 0.7:
                        mask = np.logical_or(mask, pred_mask).astype(np.uint8)
                        detections.append({
                            'class': class_name,
                            'confidence': score,
                            'mask_area': np.sum(pred_mask)
                        })
            else:
                # Fallback to bounding boxes if masks not available
                boxes = instances.pred_boxes.tensor.numpy()
                for box, cls, score in zip(boxes, pred_classes, scores):
                    class_name = self.detectron2_metadata.thing_classes[cls]
                    if class_name in FOOD_CATEGORIES or score > 0.7:
                        x1, y1, x2, y2 = map(int, box)
                        mask[y1:y2, x1:x2] = 1
                        detections.append({
                            'class': class_name,
                            'confidence': score,
                            'box': box
                        })
        
        return mask, detections
    
    def detect_food(self, image):
        """Combine YOLO and Detectron2 results for robust detection"""
        combined_mask = np.zeros(image.shape[:2], dtype=np.uint8)
        all_detections = []
        
        # Try YOLO
        if self.use_yolo:
            try:
                yolo_mask, yolo_detections = self.detect_with_yolo(image)
                combined_mask = np.logical_or(combined_mask, yolo_mask).astype(np.uint8)
                all_detections.extend([{'model': 'YOLO', **d} for d in yolo_detections])
            except Exception as e:
                print(f"YOLO detection failed: {e}")
        
        # Try Detectron2
        if self.use_detectron2:
            try:
                det2_mask, det2_detections = self.detect_with_detectron2(image)
                combined_mask = np.logical_or(combined_mask, det2_mask).astype(np.uint8)
                all_detections.extend([{'model': 'Detectron2', **d} for d in det2_detections])
            except Exception as e:
                print(f"Detectron2 detection failed: {e}")
        
        # Refine the mask with morphological operations
        kernel = np.ones((5, 5), np.uint8)
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)
        
        return combined_mask, all_detections

def load_image(path, target_size=None):
    """Load and optionally resize an image"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Image not found: {path}")
    
    img = cv2.imread(path)
    if img is None:
        raise ValueError(f"Could not load image: {path}")
    
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    if target_size:
        resized = cv2.resize(img, target_size)
        return resized, img
    
    return img, img

def calculate_portion_consumed(before_path, after_path, detector):
    """Calculate how much food was consumed between before and after images"""
    try:
        # Load images at original size for better detection
        before_img, _ = load_image(before_path)
        after_img, _ = load_image(after_path)
        
        # Ensure images are the same size
        if before_img.shape != after_img.shape:
            print("Warning: Images are different sizes. Resizing to match...")
            h, w = min(before_img.shape[0], after_img.shape[0]), min(before_img.shape[1], after_img.shape[1])
            before_img = cv2.resize(before_img, (w, h))
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
            print("  Warning: No food detected in 'before' image")
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
        det_text += f"{i}. {det['class']} "
        det_text += f"({det['confidence']:.2f}) "
        det_text += f"[{det['model']}]\n"
    ax7.text(0.1, 0.5, det_text, fontsize=10, verticalalignment='center',
             family='monospace', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))
    
    ax8 = fig.add_subplot(gs[2, 1])
    ax8.axis('off')
    det_text = "AFTER DETECTIONS:\n\n"
    for i, det in enumerate(after_detections[:5], 1):
        det_text += f"{i}. {det['class']} "
        det_text += f"({det['confidence']:.2f}) "
        det_text += f"[{det['model']}]\n"
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
    summary += f"Models Used:\n"
    models = set(d['model'] for d in before_detections + after_detections)
    for model in models:
        summary += f"  • {model}\n"
    
    ax9.text(0.05, 0.5, summary, fontsize=11, verticalalignment='center',
             family='monospace', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.suptitle(f"Food Portion Analysis: {portion:.1f}% Consumed", 
                 fontsize=18, fontweight='bold', y=0.98)
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"  Saved visualization to: {save_path}")
    
    plt.close(fig)  # Close figure instead of showing it

def find_image_pairs(folder="before_after"):
    """Find matching before/after image pairs"""
    if not os.path.exists(folder):
        return []
    
    pairs = []
    seen = set()  # Track processed files to avoid duplicates
    extensions = ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']
    
    # Find all before images
    before_files = []
    for ext in extensions:
        before_files.extend(glob.glob(os.path.join(folder, f"*_before{ext}")))
    
    for before_file in before_files:
        # Skip if we've already processed this base name
        base_name = os.path.splitext(os.path.basename(before_file))[0].replace('_before', '')
        if base_name in seen:
            continue
        
        # Try different after file patterns
        base = before_file.replace('_before.', '_after.')
        if not os.path.exists(base):
            base = before_file.replace('_before', '_after')
        
        # Try different extensions
        for ext in extensions:
            after_file = Path(base).with_suffix(ext)
            if after_file.exists():
                pairs.append((before_file, str(after_file)))
                seen.add(base_name)
                break
    
    return pairs

def main():
    print("=" * 70)
    print("FOOD PORTION DETECTION SYSTEM")
    print("Using YOLO & Detectron2 with COCO-trained models")
    print("=" * 70)
    
    # Check availability
    print(f"\nYOLO available: {YOLO_AVAILABLE}")
    print(f"Detectron2 available: {DETECTRON2_AVAILABLE}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    
    if not YOLO_AVAILABLE and not DETECTRON2_AVAILABLE:
        print("\nERROR: Neither YOLO nor Detectron2 is installed!")
        print("Install with:")
        print("  pip install ultralytics")
        print("  pip install detectron2 -f https://dl.fbaipublicfiles.com/detectron2/wheels/cu118/torch2.0/index.html")
        return
    
    # Create output folder
    output_folder = "yolococo_results"
    os.makedirs(output_folder, exist_ok=True)
    print(f"\nOutput folder: {output_folder}")
    
    # Initialize detector
    try:
        detector = MLFoodDetector()
    except Exception as e:
        print(f"\nFailed to initialize detector: {e}")
        return
    
    # Find image pairs
    test_cases = find_image_pairs()
    
    if not test_cases:
        print("\nNo image pairs found!")
        print("Expected format: before_after/plate1_before.jpg, before_after/plate1_after.jpg")
        print("Supported extensions: jpg, jpeg, png")
        return
    
    print(f"\nFound {len(test_cases)} image pair(s)\n")
    
    # Process each pair
    results = []
    for i, (before_path, after_path) in enumerate(test_cases, 1):
        print(f"{'─' * 70}")
        print(f"Analyzing pair {i}/{len(test_cases)}")
        print(f"  Before: {os.path.basename(before_path)}")
        print(f"  After:  {os.path.basename(after_path)}")
        
        result = calculate_portion_consumed(before_path, after_path, detector)
        portion = result[0]
        
        if portion is not None:
            print(f"  ✓ Result: {portion:.1f}% consumed")
            results.append((os.path.basename(before_path), portion))
            
            # Save visualization
            base_name = os.path.basename(before_path).replace('_before', '_result')
            base_name = os.path.splitext(base_name)[0] + '.png'
            save_path = os.path.join(output_folder, base_name)
            
            visualize_results(*result, save_path=save_path)
        else:
            print("  ✗ Analysis failed")
            results.append((os.path.basename(before_path), "Failed"))
        print()  # Extra newline for readability
    
    # Final summary
    print(f"{'═' * 70}")
    print("FINAL RESULTS SUMMARY")
    print(f"{'═' * 70}")
    for filename, result in results:
        if isinstance(result, (int, float)):
            bar = '█' * int(result / 5) + '░' * (20 - int(result / 5))
            print(f"{filename:30s} {result:5.1f}% [{bar}]")
        else:
            print(f"{filename:30s} {result}")
    
    print(f"\n✓ All visualizations saved to: {output_folder}/")
    print(f"{'═' * 70}\n")

if __name__ == "__main__":
    main()