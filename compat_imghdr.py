#!/usr/bin/env python3
"""
Compatibility layer for the imghdr module removed in Python 3.13

This module provides a minimal implementation of the imghdr functionality
needed by python-telegram-bot when running on Python 3.13+
"""

import io
import os

def what(file, h=None):
    """
    Determine the type of image contained in a file or byte stream.
    
    This is a simplified version of the original imghdr.what() function
    that only supports the most common image formats used with Telegram.
    
    Args:
        file: A filename (string), a file object, or a bytes object.
        h: An optional bytes object containing the header of the file.
        
    Returns:
        A string describing the image type if recognized, or None if not recognized.
    """
    if h is None:
        if isinstance(file, (bytes, bytearray)):
            h = file[:32]
        elif isinstance(file, str):
            try:
                with open(file, 'rb') as fp:
                    h = fp.read(32)
            except OSError:
                return None
        elif isinstance(file, io.IOBase) and hasattr(file, 'read'):
            h = file.read(32)
            file.seek(0)  # Reset file pointer
        else:
            return None

    # Check for JPEG
    if h[0:2] == b'\xff\xd8':
        return 'jpeg'
    
    # Check for PNG
    if h[:8] == b'\x89PNG\r\n\x1a\n':
        return 'png'
    
    # Check for GIF
    if h[:6] in (b'GIF87a', b'GIF89a'):
        return 'gif'
    
    # Check for WebP
    if h[:4] == b'RIFF' and h[8:12] == b'WEBP':
        return 'webp'
    
    # Check for TIFF
    if h[:2] in (b'MM', b'II'):
        return 'tiff'
    
    # Check for BMP
    if h[:2] == b'BM':
        return 'bmp'
    
    return None
