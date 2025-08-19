import json
from typing import List, Optional, Tuple

import cv2
import numpy as np
from detectron2 import model_zoo
from detectron2.config import get_cfg
from detectron2.data import MetadataCatalog
from detectron2.engine import DefaultPredictor


def get_class_names(annotation_file: str) -> List[str]:
    """Load class names from a COCO-format JSON file."""
    with open(annotation_file, "r") as f:
        dataset = json.load(f)
    categories = dataset.get("categories", [])
    class_names = [cat["name"] for cat in categories]
    return class_names


def setup_predictor(
    model_weights_path: str,
    config_file: str = "COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml",
    threshold: float = 0.9,
    class_names: Optional[List[str]] = None,
) -> DefaultPredictor:
    """
    Configure and initialize the Detectron2 predictor.
    """
    # Update MetadataCatalog
    if class_names:
        MetadataCatalog.get("my_dataset").thing_classes = class_names

    # Configuration setup
    cfg = get_cfg()
    cfg.merge_from_file(model_zoo.get_config_file(config_file))
    cfg.MODEL.WEIGHTS = model_weights_path
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = threshold
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = len(class_names) if class_names else 0

    return DefaultPredictor(cfg)


def predict_and_get_coordinates(
    predictor: DefaultPredictor,
    image_path: str,
    class_names: List[str],
) -> List[dict]:
    """
    Perform prediction on an image and return a list of dictionaries for each instance,
    including the segmentation coordinates and class name.

    Args:
        predictor (DefaultPredictor): The Detectron2 predictor.
        image_path (str): Path to the input image.
        class_names (List[str]): List of class names corresponding to model predictions.

    Returns:
        List[dict]: A list of dictionaries, each containing:
            - "coordinates": List of tuples representing the segmentation coordinates.
            - "class_name": The predicted class name.
    """
    # Load image
    image = cv2.imread(image_path)

    # Perform prediction
    outputs = predictor(image)

    # Extract the coordinates of the segmented regions
    instances = outputs["instances"].to("cpu")
    segmentation_results = []

    for i in range(len(instances)):
        # Extract the mask for the instance
        mask = (
            instances.pred_masks[i].numpy().astype("uint8")
        )  # Convert to uint8 for contours

        # Get the predicted class index and name
        class_index = int(instances.pred_classes[i])
        class_name = class_names[class_index]

        # Find contours (external only to avoid nested polygons)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Process each contour
        for contour in contours:
            # Simplify the contour (optional)
            epsilon = 0.001 * cv2.arcLength(
                contour, True
            )  # Adjust epsilon for simplification
            simplified_contour = cv2.approxPolyDP(contour, epsilon, True)

            # Convert to list of tuples
            coordinates = [tuple(point[0]) for point in simplified_contour]

            # Append the result with class name
            segmentation_results.append(
                {
                    "coordinates": coordinates,
                    "class_name": class_name,
                }
            )

    # Return the list of segmentation results
    return segmentation_results


def save_region_as_image(
    region: List[Tuple[int, int]],
    image_path: str,
    output_path: str = "regions_only.png",
) -> str:
    """
    Generate a new image that contains only the regions specified,
    with the background removed (transparent or black).
    """
    # Load the original image
    original_image = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)

    # Create an empty mask with the same size as the original image
    height, width = original_image.shape[:2]
    mask = np.zeros((height, width), dtype=np.uint8)

    # Draw each region on the mask
    points = np.array(region, dtype=np.int32)
    cv2.fillPoly(mask, [points], 255)  # Fill the region with white

    # Create a new image with only the regions
    result = cv2.bitwise_and(original_image, original_image, mask=mask)

    # Add transparency if the original image does not have it
    if original_image.shape[2] == 3:  # If no alpha channel
        b, g, r = cv2.split(result)
        alpha = mask  # Use the mask as the alpha channel
        result = cv2.merge([b, g, r, alpha])
    else:
        # Apply mask directly to the alpha channel if present
        result[:, :, 3] = mask

    # Save the generated image
    cv2.imwrite(output_path, result)
    return output_path
