# Copyright 2026 NXP
#
# NXP Proprietary. This software is owned or controlled by NXP and may
# only be used strictly in accordance with the applicable license terms.
# By expressly accepting such terms or by downloading, installing,
# activating and/or otherwise using the software, you are agreeing that
# you have read, and that you agree to comply with and are bound by,
# such license terms.  If you do not agree to be bound by the applicable
# license terms, then you may not retain, install, activate or otherwise
# use the software.

"""PDF parser -- extracts text layer using PyMuPDF."""
import logging
# from io import BytesIO
from pathlib import Path

import pymupdf  # canonical import; avoids the stdout print() regression in the fitz shim (1.28+)
# import pytesseract
# from PIL import Image

from .base import Parser
from nxp.mcp.knowledge.metadata.server import MCP_SERVER_NAME

_logger = logging.getLogger(MCP_SERVER_NAME)


class PdfParser(Parser):
    """Extracts text from PDF files using PyMuPDF.

    Only the text layer is extracted (no OCR).  Scanned PDFs without a text
    layer will return an empty string and be skipped by the ingestion pipeline.
    """

    extensions: frozenset[str] = frozenset({".pdf"})

    def parse(self, path: Path) -> str:
        """Extract text layer from PDF using PyMuPDF (fast, no OCR)."""
        try:
            with pymupdf.open(str(path)) as doc:
                parts = []
                for page in doc:
                    text = page.get_text()
                    if text:
                        parts.append(text)
                return "\n".join(parts).strip()
        except Exception as e:
            _logger.error(f"Error reading PDF {path.name}: {e}")
        
    # def parse(self, path: Path, ocr_language: str = "eng") -> str:
    #     try:
    #         with pymupdf.open(str(path)) as doc:
    #             total_text = ""
    #             total_ocr_text = ""
                
    #             for page_num in range(len(doc)):
    #                 page = doc[page_num]
                    
    #                 # Extract regular text
    #                 page_text = page.get_text()
                    
    #                 # Extract and OCR images
    #                 image_texts = []
    #                 image_list = page.get_images()
                    
    #                 for _, img in enumerate(image_list):
    #                     try:
    #                         xref = img[0]
    #                         pix = pymupdf.Pixmap(doc, xref)
                            
    #                         # Skip very small images
    #                         if pix.width < 50 or pix.height < 50:
    #                             pix = None
    #                             continue
                            
    #                         # Convert to PIL Image for OCR
    #                         if pix.n - pix.alpha < 4:  # GRAY or RGB
    #                             img_data = pix.tobytes("png")
    #                         else:  # CMYK: convert to RGB first
    #                             pix1 = pymupdf.Pixmap(pymupdf.csRGB, pix)
    #                             img_data = pix1.tobytes("png")
    #                             pix1 = None
                            
    #                         # Perform OCR
    #                         with Image.open(BytesIO(img_data)) as pil_image:
    #                             ocr_text = pytesseract.image_to_string(
    #                                 pil_image, 
    #                                 lang=ocr_language,
    #                                 config='--psm 6'  # Uniform block of text
    #                             ).strip()
                                
    #                             if ocr_text:
    #                                 image_texts.append(ocr_text)
                            
    #                         pix = None
                            
    #                     except Exception as ocr_error:
    #                         _logger.warning(f"OCR failed for image in {path.name} on page {page_num + 1}: {ocr_error}")
    #                         continue
                    
    #                 # Combine all OCR text from this page
    #                 page_ocr_text = "\n".join(image_texts)
                    
    #                 total_text += page_text + "\n"
    #                 total_ocr_text += page_ocr_text + "\n"
                
    #             return f"{total_text}\n{total_ocr_text}".strip()
                
    #     except Exception as e:
    #         _logger.error(f"Error reading PDF with OCR: {e}")
    #         return ""
