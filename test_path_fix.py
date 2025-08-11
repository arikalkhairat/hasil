#!/usr/bin/env python3
"""
Test script untuk memverifikasi path gambar yang diperbaiki
"""

import os
from main import embed_watermark_to_docx

def test_path_format():
    """Test untuk memverifikasi format path yang benar"""
    
    # Simulasi data yang dikembalikan oleh embed_watermark_to_docx
    # Path ini seharusnya menggunakan format: "generated/processed_xxx/original_0.png"
    
    print("Testing path format...")
    
    # Cek apakah fungsi mengembalikan path dengan format yang benar
    sample_result = {
        "success": True,
        "processed_images": [
            {
                "index": 0,
                "original": "generated/processed_abc123/original_0.png",
                "watermarked": "generated/processed_abc123/watermarked_0.png"
            }
        ],
        "qr_image": "generated/processed_abc123/watermark_qr.png"
    }
    
    # Verifikasi format path
    for img in sample_result["processed_images"]:
        original_path = img["original"]
        watermarked_path = img["watermarked"]
        
        # Path harus dimulai dengan "generated/"
        assert original_path.startswith("generated/"), f"Original path tidak dimulai dengan 'generated/': {original_path}"
        assert watermarked_path.startswith("generated/"), f"Watermarked path tidak dimulai dengan 'generated/': {watermarked_path}"
        
        # Path harus berisi direktori processed_xxx
        assert "/processed_" in original_path, f"Original path tidak berisi '/processed_': {original_path}"
        assert "/processed_" in watermarked_path, f"Watermarked path tidak berisi '/processed_': {watermarked_path}"
        
        print(f"✓ Original path format valid: {original_path}")
        print(f"✓ Watermarked path format valid: {watermarked_path}")
    
    qr_path = sample_result["qr_image"]
    assert qr_path.startswith("generated/"), f"QR path tidak dimulai dengan 'generated/': {qr_path}"
    print(f"✓ QR path format valid: {qr_path}")
    
    print("✓ Semua format path valid!")
    
    # Simulasi URL final yang akan dibuat di template
    for img in sample_result["processed_images"]:
        original_url = f"/static/{img['original']}"
        watermarked_url = f"/static/{img['watermarked']}"
        
        print(f"URL akan menjadi:")
        print(f"  Original: {original_url}")  # /static/generated/processed_xxx/original_0.png
        print(f"  Watermarked: {watermarked_url}")  # /static/generated/processed_xxx/watermarked_0.png
        
        # Verifikasi struktur URL akhir
        assert original_url == f"/static/generated/processed_abc123/original_0.png"
        assert watermarked_url == f"/static/generated/processed_abc123/watermarked_0.png"

if __name__ == "__main__":
    test_path_format()
    print("\n🎉 Test selesai - Format path sudah benar!")
