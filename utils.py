import re

def sanitize_filename(filename):
    """Sanitize a filename for safe use in the OS and ffmpeg"""
    sanitized = re.sub(r'[#<>:"/\\|&?*;()$\[\]\'\n\t"]', '_', filename)
    sanitized = re.sub(r'_+', '_', sanitized)
    sanitized = re.sub(r'[\x00-\x1F\x7F]', '', sanitized)
    return sanitized.strip(' _')
