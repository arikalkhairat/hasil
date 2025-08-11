# File: pdf_utils.py
# Deskripsi: Utility functions untuk memproses PDF dan konversi ke gambar

import os
import tempfile
import shutil
from typing import List, Tuple, Dict, Any
from pdf2image import convert_from_path
from PIL import Image
import pypdf
from pypdf import PdfReader, PdfWriter
import uuid
import cv2
import numpy as np

def convert_pdf_to_images(pdf_path: str, output_dir: str, dpi: int = 300) -> List[str]:
    """
    Konversi PDF ke gambar-gambar (satu gambar per halaman).
    
    Args:
        pdf_path (str): Path ke file PDF
        output_dir (str): Directory untuk menyimpan gambar hasil
        dpi (int): DPI untuk konversi (default: 300)
        
    Returns:
        List[str]: List path gambar yang dihasilkan
    """
    try:
        # Buat direktori output jika belum ada
        os.makedirs(output_dir, exist_ok=True)
        
        # Konversi PDF ke images
        images = convert_from_path(pdf_path, dpi=dpi)
        
        image_paths = []
        for i, image in enumerate(images):
            # Generate unique filename untuk setiap halaman
            filename = f"page_{i+1}_{uuid.uuid4().hex[:8]}.png"
            image_path = os.path.join(output_dir, filename)
            
            # Simpan sebagai PNG
            image.save(image_path, 'PNG')
            image_paths.append(image_path)
            print(f"[*] Halaman {i+1} disimpan: {image_path}")
        
        print(f"[*] PDF berhasil dikonversi ke {len(image_paths)} gambar")
        return image_paths
        
    except Exception as e:
        print(f"[!] Error konversi PDF ke gambar: {e}")
        raise

def get_pdf_info(pdf_path: str) -> Dict[str, Any]:
    """
    Mendapatkan informasi dasar dari file PDF.
    
    Args:
        pdf_path (str): Path ke file PDF
        
    Returns:
        Dict: Informasi PDF (jumlah halaman, ukuran file, dll)
    """
    try:
        # Baca PDF
        reader = PdfReader(pdf_path)
        
        # Informasi dasar
        info = {
            "pages": len(reader.pages),
            "file_size_bytes": os.path.getsize(pdf_path),
            "file_size_kb": round(os.path.getsize(pdf_path) / 1024, 2),
            "file_size_mb": round(os.path.getsize(pdf_path) / (1024 * 1024), 2),
            "encrypted": reader.is_encrypted,
            "title": None,
            "author": None,
            "subject": None,
            "creator": None
        }
        
        # Metadata jika tersedia
        if reader.metadata:
            info["title"] = reader.metadata.get('/Title', 'N/A')
            info["author"] = reader.metadata.get('/Author', 'N/A')
            info["subject"] = reader.metadata.get('/Subject', 'N/A')
            info["creator"] = reader.metadata.get('/Creator', 'N/A')
        
        # Informasi halaman pertama untuk estimasi ukuran
        if len(reader.pages) > 0:
            page = reader.pages[0]
            mediabox = page.mediabox
            info["page_width"] = float(mediabox.width)
            info["page_height"] = float(mediabox.height)
            info["page_size"] = f"{mediabox.width} × {mediabox.height} pts"
        
        return info
        
    except Exception as e:
        print(f"[!] Error membaca info PDF: {e}")
        return {"error": str(e)}

def embed_watermark_to_pdf_images(pdf_path: str, qr_path: str, output_dir: str, dpi: int = 300) -> Dict[str, Any]:
    """
    Ekstrak gambar dari PDF, sisipkan watermark, dan siapkan untuk rekonstruksi PDF.
    
    Args:
        pdf_path (str): Path ke file PDF asli
        qr_path (str): Path ke QR Code untuk watermark
        output_dir (str): Directory untuk output
        dpi (int): DPI untuk konversi PDF ke gambar
        
    Returns:
        Dict: Hasil proses dengan informasi gambar dan path
    """
    try:
        from lsb_steganography import embed_qr_to_image
        from qr_utils import get_detailed_pixel_info, calculate_mse_psnr
        
        # Buat direktori untuk menyimpan gambar PDF
        pdf_images_dir = os.path.join(output_dir, "pdf_pages")
        watermarked_dir = os.path.join(output_dir, "watermarked_pages") 
        os.makedirs(pdf_images_dir, exist_ok=True)
        os.makedirs(watermarked_dir, exist_ok=True)
        
        # Konversi PDF ke gambar
        print("[*] Mengkonversi PDF ke gambar...")
        page_images = convert_pdf_to_images(pdf_path, pdf_images_dir, dpi)
        
        if not page_images:
            return {
                "success": False,
                "message": "Tidak ada halaman yang berhasil diekstrak dari PDF",
                "error_type": "NO_PAGES_EXTRACTED"
            }
        
        # Get PDF info
        pdf_info = get_pdf_info(pdf_path)
        
        # Proses watermarking untuk setiap halaman
        processed_images = []
        analysis_results = []
        
        for i, page_path in enumerate(page_images):
            try:
                print(f"[*] Memproses watermark halaman {i+1}...")
                
                # Generate path untuk gambar watermarked
                watermarked_filename = f"watermarked_page_{i+1}_{uuid.uuid4().hex[:8]}.png"
                watermarked_path = os.path.join(watermarked_dir, watermarked_filename)
                
                # Embed watermark menggunakan LSB
                try:
                    embed_qr_to_image(page_path, qr_path, watermarked_path)
                    embed_result = os.path.exists(watermarked_path)
                except Exception as e:
                    print(f"[!] Error embedding halaman {i+1}: {e}")
                    embed_result = False
                
                if embed_result:
                    # Analisis pixel detail
                    original_analysis = get_detailed_pixel_info(page_path)
                    watermarked_analysis = get_detailed_pixel_info(watermarked_path)
                    
                    # Hitung MSE/PSNR
                    metrics = calculate_mse_psnr(page_path, watermarked_path)
                    
                    processed_images.append({
                        "page_number": i + 1,
                        "original_path": page_path,
                        "watermarked_path": watermarked_path,
                        "original_filename": os.path.basename(page_path),
                        "watermarked_filename": watermarked_filename
                    })
                    
                    analysis_results.append({
                        "page_number": i + 1,
                        "original": original_analysis,
                        "watermarked": watermarked_analysis,
                        "metrics": metrics
                    })
                    
                    print(f"[*] Halaman {i+1} berhasil di-watermark")
                else:
                    print(f"[!] Gagal watermark halaman {i+1}")
                    
            except Exception as e:
                print(f"[!] Error memproses halaman {i+1}: {e}")
                continue
        
        if not processed_images:
            return {
                "success": False,
                "message": "Tidak ada halaman yang berhasil di-watermark",
                "error_type": "WATERMARKING_FAILED"
            }
        
        # Analisis QR Code
        qr_analysis = get_detailed_pixel_info(qr_path)
        
        return {
            "success": True,
            "message": f"Berhasil memproses {len(processed_images)} halaman PDF",
            "pdf_info": pdf_info,
            "processed_images": processed_images,
            "analysis": {
                "qr_analysis": qr_analysis,
                "page_analyses": analysis_results,
                "total_pages": len(page_images),
                "watermarked_pages": len(processed_images)
            },
            "output_directories": {
                "original_pages": pdf_images_dir,
                "watermarked_pages": watermarked_dir
            }
        }
        
    except Exception as e:
        print(f"[!] Error dalam embed_watermark_to_pdf_images: {e}")
        return {
            "success": False,
            "message": f"Error memproses PDF: {str(e)}",
            "error": str(e)
        }

def create_watermarked_pdf(original_pdf_path: str, watermarked_images_dir: str, output_pdf_path: str, dpi: int = 300) -> bool:
    """
    Membuat PDF baru dari gambar-gambar yang sudah di-watermark.
    
    Args:
        original_pdf_path (str): Path PDF asli untuk referensi ukuran
        watermarked_images_dir (str): Directory berisi gambar watermarked
        output_pdf_path (str): Path output PDF baru
        dpi (int): DPI yang digunakan untuk konversi
        
    Returns:
        bool: True jika berhasil, False jika gagal
    """
    try:
        # Ambil semua file gambar watermarked
        image_files = []
        for filename in os.listdir(watermarked_images_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                image_files.append(os.path.join(watermarked_images_dir, filename))
        
        if not image_files:
            print("[!] Tidak ada gambar watermarked ditemukan")
            return False
        
        # Sort berdasarkan nomor halaman
        image_files.sort()
        
        # Konversi gambar ke PDF
        images = []
        for img_path in image_files:
            img = Image.open(img_path)
            # Konversi ke RGB jika perlu
            if img.mode != 'RGB':
                img = img.convert('RGB')
            images.append(img)
        
        if images:
            # Simpan sebagai PDF
            images[0].save(output_pdf_path, save_all=True, append_images=images[1:], 
                          resolution=dpi, quality=95)
            print(f"[*] PDF watermarked berhasil dibuat: {output_pdf_path}")
            return True
        else:
            print("[!] Tidak ada gambar valid untuk dikonversi ke PDF")
            return False
        
    except Exception as e:
        print(f"[!] Error membuat PDF watermarked: {e}")
        return False

def extract_watermark_from_pdf(pdf_path: str, output_dir: str, dpi: int = 300) -> Dict[str, Any]:
    """
    Ekstrak watermark QR Code dari halaman-halaman PDF.
    
    Args:
        pdf_path (str): Path ke PDF yang akan diekstrak
        output_dir (str): Directory untuk menyimpan hasil ekstraksi
        dpi (int): DPI untuk konversi PDF ke gambar
        
    Returns:
        Dict: Hasil ekstraksi dengan informasi QR Code yang ditemukan
    """
    try:
        from lsb_steganography import extract_qr_from_image
        
        # Buat direktori untuk gambar PDF dan hasil ekstraksi
        pdf_images_dir = os.path.join(output_dir, "pdf_pages_extract")
        extracted_dir = os.path.join(output_dir, "extracted_qr")
        os.makedirs(pdf_images_dir, exist_ok=True)
        os.makedirs(extracted_dir, exist_ok=True)
        
        # Konversi PDF ke gambar
        print("[*] Mengkonversi PDF ke gambar untuk ekstraksi...")
        page_images = convert_pdf_to_images(pdf_path, pdf_images_dir, dpi)
        
        if not page_images:
            return {
                "success": False,
                "message": "Tidak ada halaman yang berhasil diekstrak dari PDF",
                "error_type": "NO_PAGES_EXTRACTED"
            }
        
        # Get PDF info
        pdf_info = get_pdf_info(pdf_path)
        
        # Ekstrak watermark dari setiap halaman
        extracted_qrs = []
        
        for i, page_path in enumerate(page_images):
            try:
                print(f"[*] Mengekstrak watermark dari halaman {i+1}...")
                
                # Generate path untuk QR hasil ekstraksi
                qr_filename = f"extracted_qr_page_{i+1}_{uuid.uuid4().hex[:8]}.png"
                qr_output_path = os.path.join(extracted_dir, qr_filename)
                
                # Ekstrak menggunakan LSB
                try:
                    extract_qr_from_image(page_path, qr_output_path)
                    success = os.path.exists(qr_output_path)
                except Exception as e:
                    print(f"[!] Error ekstraksi halaman {i+1}: {e}")
                    success = False
                
                if success and os.path.exists(qr_output_path):
                    # Verifikasi bahwa hasil ekstraksi adalah gambar valid
                    try:
                        img = Image.open(qr_output_path)
                        # Cek apakah gambar tidak kosong
                        if img.size[0] > 0 and img.size[1] > 0:
                            extracted_qrs.append({
                                "page_number": i + 1,
                                "filename": qr_filename,
                                "url": f"/static/generated/{os.path.basename(output_dir)}/{qr_filename}",
                                "path": qr_output_path
                            })
                            print(f"[*] QR Code berhasil diekstrak dari halaman {i+1}")
                        else:
                            os.remove(qr_output_path)
                    except Exception as e:
                        print(f"[!] File hasil ekstraksi tidak valid untuk halaman {i+1}: {e}")
                        if os.path.exists(qr_output_path):
                            os.remove(qr_output_path)
                else:
                    print(f"[*] Tidak ada watermark ditemukan di halaman {i+1}")
                    
            except Exception as e:
                print(f"[!] Error mengekstrak halaman {i+1}: {e}")
                continue
        
        return {
            "success": True,
            "message": f"Proses ekstraksi selesai. Ditemukan {len(extracted_qrs)} QR Code dari {len(page_images)} halaman",
            "pdf_info": pdf_info,
            "extracted_qrs": extracted_qrs,
            "total_pages": len(page_images),
            "qr_found": len(extracted_qrs)
        }
        
    except Exception as e:
        print(f"[!] Error dalam extract_watermark_from_pdf: {e}")
        return {
            "success": False,
            "message": f"Error mengekstrak watermark dari PDF: {str(e)}",
            "error": str(e)
        }

# --- End of pdf_utils.py ---