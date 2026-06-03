import cloudinary
import cloudinary.uploader
import os
from dotenv import load_dotenv

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=True
)


def upload_member_photo(file_stream, member_id: str) -> tuple[str | None, str | None]:
    """
    Upload a member photo to Cloudinary.
    Returns (url, error).
    """
    try:
        result = cloudinary.uploader.upload(
            file_stream,
            folder='cerp/members',
            public_id=member_id,
            overwrite=True,
            resource_type='image',
            transformation=[
                {'width': 400, 'height': 400, 'crop': 'fill', 'gravity': 'face'}
            ]
        )
        return result['secure_url'], None
    except Exception as e:
        return None, str(e)


def delete_member_photo(member_id: str) -> tuple[bool, str | None]:
    """Delete a member photo from Cloudinary."""
    try:
        cloudinary.uploader.destroy(f'cerp/members/{member_id}')
        return True, None
    except Exception as e:
        return False, str(e)
