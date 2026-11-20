"""Generic extraction of image bytes from authenticated Atlas DOCX exports.

Associates images with the nearest preceding stable asset heading. Neither
Google origin nor approval is asserted here; those require live connector
evidence and a separate approval check.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import re
from docx import Document
from PIL import Image

EMBED = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed'
ASSET_HEADING = re.compile(r'^\s*([A-Z][A-Z0-9]{1,12}(?:-[A-Z0-9]{1,20}){2,})\s*[—–:]')

class AtlasExtractionError(ValueError):
    pass

@dataclass(frozen=True)
class AssetBinary:
    asset_id: str
    paragraph_index: int
    media_name: str
    sha256: str
    width: int
    height: int
    format: str
    data: bytes

    def metadata(self):
        return {k: getattr(self, k) for k in ('asset_id','paragraph_index','media_name','sha256','width','height','format')}

def extract_assets(docx_path: str | Path, asset_id: str | None = None) -> list[AssetBinary]:
    doc = Document(str(docx_path))
    current = None
    found = []
    for i, p in enumerate(doc.paragraphs):
        label = p.text.strip()
        match = ASSET_HEADING.match(label)
        if match:
            current = match.group(1)
        for blip in p._p.xpath('.//a:blip'):
            if not current:
                raise AtlasExtractionError('IMAGE_WITHOUT_ASSET_HEADING')
            rid = blip.get(EMBED)
            if not rid or rid not in doc.part.rels:
                raise AtlasExtractionError('BROKEN_IMAGE_RELATION')
            part = doc.part.related_parts[rid]
            data = part.blob
            with Image.open(BytesIO(data)) as img:
                img.verify()
            with Image.open(BytesIO(data)) as img:
                width, height, fmt = img.width, img.height, img.format
            found.append(AssetBinary(current, i, Path(str(part.partname)).name,
                                     sha256(data).hexdigest(), width, height, fmt, data))
    if asset_id is not None:
        found = [x for x in found if x.asset_id == asset_id]
        if len(found) != 1:
            raise AtlasExtractionError(f'ASSET_IMAGE_MISSING_OR_AMBIGUOUS:{asset_id}:{len(found)}')
    return found
