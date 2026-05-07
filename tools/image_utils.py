import base64
import httpx
from typing import Optional
from schemas.output_schemas import ImageArtifact

BALI_IMAGES = {
    "uluwatu_cliffs": {
        "url": "https://images.unsplash.com/photo-1537996194471-e657df975ab4?w=800",
        "caption": "Uluwatu cliffs at sunset, Bali",
        "source": "Unsplash",
    },
    "single_fin": {
        "url": "https://images.unsplash.com/photo-1539367628448-4bc5c9d171c8?w=800",
        "caption": "Single Fin Beach Club, Uluwatu",
        "source": "Unsplash",
    },
    "karma_kandara": {
        "url": "https://images.unsplash.com/photo-1571896349842-33c89424de2d?w=800",
        "caption": "Karma Kandara Resort pool, Uluwatu",
        "source": "Unsplash",
    },
    "bali_rice": {
        "url": "https://images.unsplash.com/photo-1555400038-63f5ba517a47?w=800",
        "caption": "Tegallalang rice terraces, Ubud",
        "source": "Unsplash",
    },
    "bali_temple": {
        "url": "https://images.unsplash.com/photo-1604928141064-207cea6f571f?w=800",
        "caption": "Tanah Lot temple at sunset",
        "source": "Unsplash",
    },
    "cafe_bali": {
        "url": "https://images.unsplash.com/photo-1600093463592-8e36ae95ef56?w=800",
        "caption": "Aesthetic café in Canggu, Bali",
        "source": "Unsplash",
    },
    "beach_club": {
        "url": "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=800",
        "caption": "Rooftop beach club overlooking the ocean",
        "source": "Unsplash",
    },
    "seminyak_sunset": {
        "url": "https://images.unsplash.com/photo-1559628233-100c798642d5?w=800",
        "caption": "Seminyak beach sunset, Bali",
        "source": "Unsplash",
    },
    "villa_pool": {
        "url": "https://images.unsplash.com/photo-1582610116397-edb72e301a85?w=800",
        "caption": "Private infinity pool villa, Bali",
        "source": "Unsplash",
    },
    "alila_villas": {
        "url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800",
        "caption": "Alila Villas Uluwatu, infinity pool",
        "source": "Unsplash",
    },
    "waterbom": {
        "url": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=800",
        "caption": "Water park fun, Bali",
        "source": "Unsplash",
    },
    "warung_food": {
        "url": "https://images.unsplash.com/photo-1512058564366-18510be2db19?w=800",
        "caption": "Traditional Balinese warung food",
        "source": "Unsplash",
    },
}


def fetch_image_as_base64(url: str, timeout: int = 10) -> Optional[str]:
    """Fetch an image from a URL and return as base64 string."""
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return base64.b64encode(resp.content).decode("utf-8")
    except Exception:
        return None


def build_image_artifact(key: str) -> ImageArtifact:
    """Build an ImageArtifact from the predefined Bali image library."""
    meta = BALI_IMAGES.get(key, {
        "url": "https://images.unsplash.com/photo-1537996194471-e657df975ab4?w=800",
        "caption": "Bali destination",
        "source": "Unsplash",
    })
    url = meta["url"]
    b64 = fetch_image_as_base64(url) or ""
    return ImageArtifact(
        imageUrl=url,
        base64=b64,
        mimeType="image/jpeg",
        source=meta["source"],
        caption=meta["caption"],
    )


def build_image_artifact_from_url(url: str, caption: str, source: str = "Web") -> ImageArtifact:
    """Build an ImageArtifact from any URL."""
    b64 = fetch_image_as_base64(url) or ""
    return ImageArtifact(
        imageUrl=url,
        base64=b64,
        mimeType="image/jpeg",
        source=source,
        caption=caption,
    )
