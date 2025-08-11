#!/usr/bin/env python3
# Test script untuk membuat PDF sederhana untuk testing

from PIL import Image, ImageDraw, ImageFont
import os

def create_test_pdf():
    """Membuat PDF test sederhana dengan gambar"""
    try:
        # Buat gambar test
        width, height = 800, 600
        
        # Buat gambar dengan background putih
        img = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(img)
        
        # Gambar beberapa shapes dan text
        draw.rectangle([50, 50, width-50, height-50], outline='black', width=3)
        draw.rectangle([100, 100, 300, 200], fill='lightblue', outline='blue')
        draw.rectangle([400, 300, 600, 400], fill='lightgreen', outline='green')
        
        # Tambah text (tanpa font khusus untuk kompatibilitas)
        draw.text((120, 130), "Test PDF Document", fill='black')
        draw.text((420, 330), "Sample Image Area", fill='black')
        draw.text((200, 500), "For LSB Watermarking Test", fill='gray')
        
        # Simpan sebagai PDF
        pdf_path = '/workspaces/hasil/static/uploads/test_document.pdf'
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        
        # Konversi ke PDF
        img.save(pdf_path, 'PDF', quality=95)
        print(f"[*] Test PDF berhasil dibuat: {pdf_path}")
        
        return pdf_path
        
    except Exception as e:
        print(f"[!] Error membuat test PDF: {e}")
        return None

if __name__ == "__main__":
    create_test_pdf()