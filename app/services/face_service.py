import os
import base64
import uuid

from deepface import DeepFace



FACE_DATA_DIR = os.path.join(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(__file__)
        )
    ),
    "face_data"
)


def save_face_image(voter_number, image_data, filename=None):

    # Create face_data directory if it doesn't exist
    os.makedirs(FACE_DATA_DIR, exist_ok=True)

    # Remove base64 header
    if "," in image_data:
        image_data = image_data.split(",", 1)[1]

    # Decode image
    image_bytes = base64.b64decode(image_data)

    # File name
    if filename is None:
        filename = f"{voter_number}.jpg"

    filepath = os.path.join(
        FACE_DATA_DIR,
        filename
    )

    # Save image
    with open(filepath, "wb") as file:
        file.write(image_bytes)

    return filepath

def find_duplicate_face(captured_image_path, exclude_voter_number=None):
    """
    Find whether a captured face matches an existing voter.
    Stop registration if comparison fails.
    """
    if not os.path.exists(captured_image_path):
        raise FileNotFoundError("Captured face image not found.")

    if not os.path.isdir(FACE_DATA_DIR):
        raise RuntimeError(
            "Registered face data directory is missing."
        )

    for filename in os.listdir(FACE_DATA_DIR):
        if not filename.lower().endswith(".jpg"):
            continue

        if filename.lower().startswith("temp_"):
            continue

        registered_voter_number = os.path.splitext(filename)[0]

        if registered_voter_number == exclude_voter_number:
            continue

        registered_image_path = os.path.join(
            FACE_DATA_DIR,
            filename
        )

        try:
            result = DeepFace.verify(
                img1_path=registered_image_path,
                img2_path=captured_image_path,
                model_name="VGG-Face",
                detector_backend="opencv",
                distance_metric="cosine",
                enforce_detection=True
            )
        except Exception as error:
            raise RuntimeError(
                "Face comparison failed. Registration cannot continue."
            ) from error

        if result.get("verified"):
            return registered_voter_number

    return None

def verify_face(voter_number, captured_image_path):

    registered_image_path = os.path.join(
        FACE_DATA_DIR,
        f"{voter_number}.jpg"
    )

    if not os.path.exists(registered_image_path):
        return {
            "verified": False,
            "message": "Registered face not found."
        }

    if not os.path.exists(captured_image_path):
        return {
            "verified": False,
            "message": "Captured face image not found."
        }

    try:

        result = DeepFace.verify(
            img1_path=registered_image_path,
            img2_path=captured_image_path,
            model_name="VGG-Face",
            detector_backend="opencv",
            distance_metric="cosine",
            enforce_detection=True
        )

        return {
            "verified": result["verified"],
            "distance": result["distance"],
            "confidence": result.get("confidence", 0),
            "message": (
                "Face verification successful."
                if result["verified"]
                else "Face verification failed."
            )
        }

    except Exception as error:

        return {
            "verified": False,
            "message": f"Face verification error: {error}"
        }


def create_temporary_face_path(voter_number):

    filename = f"temp_{voter_number}_{uuid.uuid4().hex}.jpg"

    return os.path.join(
        FACE_DATA_DIR,
        filename
    )
