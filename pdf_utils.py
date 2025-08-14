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
import fitz  # PyMuPDF untuk ekstraksi gambar dari PDF

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

def extract_images_from_pdf(pdf_path: str, output_dir: str) -> List[str]:
    """
    Ekstrak gambar-gambar yang sebenarnya ada di dalam PDF (bukan render halaman).
    
    Args:
        pdf_path (str): Path ke file PDF
        output_dir (str): Directory untuk menyimpan gambar hasil
        
    Returns:
        List[str]: List path gambar yang diekstrak dari PDF
    """
    try:
        # Buat direktori output jika belum ada
        os.makedirs(output_dir, exist_ok=True)
        
        # Buka PDF dengan PyMuPDF
        pdf_document = fitz.open(pdf_path)
        extracted_images = []
        
        print(f"[*] Mencari gambar di dalam PDF dengan {len(pdf_document)} halaman...")
        
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            
            # Dapatkan daftar gambar di halaman ini
            image_list = page.get_images(full=True)
            
            if image_list:
                print(f"[*] Ditemukan {len(image_list)} gambar di halaman {page_num + 1}")
            
            for img_index, img in enumerate(image_list):
                try:
                    # Get the XREF of the image
                    xref = img[0]
                    
                    # Extract the image
                    base_image = pdf_document.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    # Generate unique filename
                    filename = f"pdf_image_p{page_num + 1}_i{img_index + 1}_{uuid.uuid4().hex[:8]}.{image_ext}"
                    image_path = os.path.join(output_dir, filename)
                    
                    # Simpan gambar
                    with open(image_path, "wb") as image_file:
                        image_file.write(image_bytes)
                    
                    # Konversi ke PNG jika perlu (untuk konsistensi)
                    if image_ext.lower() != 'png':
                        try:
                            img_pil = Image.open(image_path)
                            png_filename = filename.rsplit('.', 1)[0] + '.png'
                            png_path = os.path.join(output_dir, png_filename)
                            img_pil.save(png_path, 'PNG')
                            
                            # Hapus file asli dan gunakan PNG
                            os.remove(image_path)
                            image_path = png_path
                            
                        except Exception as e:
                            print(f"[!] Warning: Gagal konversi ke PNG: {e}")
                    
                    extracted_images.append(image_path)
                    print(f"[*] Gambar diekstrak: {os.path.basename(image_path)}")
                    
                except Exception as e:
                    print(f"[!] Error mengekstrak gambar {img_index + 1} dari halaman {page_num + 1}: {e}")
                    continue
        
        pdf_document.close()
        
        if not extracted_images:
            print("[!] Tidak ada gambar ditemukan di dalam PDF")
            raise ValueError("NO_IMAGES_FOUND")
        
        print(f"[*] Total {len(extracted_images)} gambar berhasil diekstrak dari PDF")
        return extracted_images
        
    except Exception as e:
        if str(e) == "NO_IMAGES_FOUND":
            raise
        print(f"[!] Error ekstraksi gambar dari PDF: {e}")
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

def embed_watermark_to_pdf_real_images(pdf_path: str, qr_path: str, output_dir: str) -> Dict[str, Any]:
    """
    Ekstrak gambar asli dari PDF, sisipkan watermark, dan simpan hasil.
    
    Args:
        pdf_path (str): Path ke file PDF asli
        qr_path (str): Path ke QR Code untuk watermark
        output_dir (str): Directory untuk output
        
    Returns:
        Dict: Hasil proses dengan informasi gambar dan path
    """
    try:
        from lsb_steganography import embed_qr_to_image
        from qr_utils import get_detailed_pixel_info, calculate_mse_psnr
        
        # Buat direktori untuk menyimpan gambar PDF
        original_images_dir = os.path.join(output_dir, "original_images")
        watermarked_dir = os.path.join(output_dir, "watermarked_images") 
        os.makedirs(original_images_dir, exist_ok=True)
        os.makedirs(watermarked_dir, exist_ok=True)
        
        # Ekstrak gambar asli dari PDF
        print("[*] Mengekstrak gambar asli dari PDF...")
        extracted_images = extract_images_from_pdf(pdf_path, original_images_dir)
        
        if not extracted_images:
            return {
                "success": False,
                "message": "Tidak ada gambar yang ditemukan di dalam PDF",
                "error_type": "NO_IMAGES_FOUND"
            }
        
        # Get PDF info
        pdf_info = get_pdf_info(pdf_path)
        
        # Proses watermarking untuk setiap gambar
        processed_images = []
        analysis_results = []
        
        for i, image_path in enumerate(extracted_images):
            try:
                print(f"[*] Memproses watermark gambar {i+1}/{len(extracted_images)}...")
                
                # Generate path untuk gambar watermarked
                original_filename = os.path.basename(image_path)
                watermarked_filename = f"watermarked_{original_filename}"
                watermarked_path = os.path.join(watermarked_dir, watermarked_filename)
                
                # Embed watermark menggunakan LSB
                try:
                    embed_qr_to_image(image_path, qr_path, watermarked_path)
                    embed_result = os.path.exists(watermarked_path)
                except Exception as e:
                    print(f"[!] Error embedding gambar {i+1}: {e}")
                    embed_result = False
                
                if embed_result and os.path.exists(watermarked_path):
                    # Verify file was created successfully and is readable
                    try:
                        # Quick test to ensure file is readable
                        file_size = os.path.getsize(watermarked_path)
                        if file_size == 0:
                            print(f"[!] Warning: Watermarked file {watermarked_filename} is empty")
                            continue
                        
                        # Analisis pixel detail
                        original_analysis = get_detailed_pixel_info(image_path)
                        watermarked_analysis = get_detailed_pixel_info(watermarked_path)
                        
                        # Hitung MSE/PSNR
                        metrics = calculate_mse_psnr(image_path, watermarked_path)
                        
                        # Generate relative URL paths for both original and watermarked images
                        relative_dir = os.path.basename(output_dir)
                        original_relative_path = f"{relative_dir}/original_images/{original_filename}"
                        watermarked_relative_path = f"{relative_dir}/watermarked_images/{watermarked_filename}"
                        
                        processed_images.append({
                            "image_index": i + 1,
                            "original_path": image_path,  # Keep full paths for backend use
                            "watermarked_path": watermarked_path,  # Keep full paths for backend use
                            "original": f"generated/{original_relative_path}",  # Frontend URL format
                            "watermarked": f"generated/{watermarked_relative_path}",  # Frontend URL format
                            "original_filename": original_filename,
                            "watermarked_filename": watermarked_filename,
                            "url": f"/static/generated/{watermarked_relative_path}",  # Full URL
                            "file_size": file_size,
                            "exists": True,
                            "metrics": metrics  # Add the calculated metrics
                        })
                        
                        analysis_results.append({
                            "image_index": i + 1,
                            "original": original_analysis,
                            "watermarked": watermarked_analysis,
                            "metrics": metrics
                        })
                        
                        print(f"[*] Gambar {i+1} berhasil di-watermark (size: {file_size} bytes)")
                        
                    except Exception as e:
                        print(f"[!] Error verifying watermarked file {watermarked_filename}: {e}")
                        continue
                else:
                    print(f"[!] Gagal watermark gambar {i+1} - file tidak ada atau gagal dibuat")
                    
            except Exception as e:
                print(f"[!] Error memproses gambar {i+1}: {e}")
                continue
        
        if not processed_images:
            return {
                "success": False,
                "message": "Tidak ada gambar yang berhasil di-watermark",
                "error_type": "WATERMARKING_FAILED"
            }
        
        # Analisis QR Code
        qr_analysis = get_detailed_pixel_info(qr_path)
        
        # Buat PDF baru dari gambar-gambar yang sudah di-watermark
        output_pdf_path = None
        try:
            print("[*] Membuat PDF baru dari gambar watermarked...")
            output_pdf_path = os.path.join(output_dir, "watermarked_output.pdf")
            pdf_created = create_watermarked_pdf(pdf_path, watermarked_dir, output_pdf_path)
            
            if pdf_created:
                print(f"[*] PDF watermarked berhasil dibuat: {output_pdf_path}")
                # Tambahkan info ukuran file
                original_size = os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0
                new_size = os.path.getsize(output_pdf_path) if os.path.exists(output_pdf_path) else 0
                
                file_size_info = {
                    "original_size": original_size,
                    "watermarked_size": new_size,
                    "size_difference": new_size - original_size,
                    "size_change_percentage": ((new_size - original_size) / original_size * 100) if original_size > 0 else 0,
                    "original_size_kb": original_size / 1024,
                    "watermarked_size_kb": new_size / 1024,
                    "original_size_mb": original_size / (1024 * 1024),
                    "watermarked_size_mb": new_size / (1024 * 1024)
                }
            else:
                print("[!] Gagal membuat PDF watermarked")
                file_size_info = None
                
        except Exception as e:
            print(f"[!] Error membuat PDF baru: {e}")
            output_pdf_path = None
            file_size_info = None
        
        return {
            "success": True,
            "message": f"Berhasil memproses {len(processed_images)} gambar dari PDF",
            "pdf_info": pdf_info,
            "processed_images": processed_images,
            "watermarked_pdf_path": output_pdf_path,
            "file_size_info": file_size_info,
            "analysis": {
                "qr_analysis": qr_analysis,
                "image_analyses": analysis_results,
                "total_images": len(extracted_images),
                "watermarked_images": len(processed_images)
            },
            "output_directories": {
                "original_images": original_images_dir,
                "watermarked_images": watermarked_dir
            }
        }
        
    except Exception as e:
        if str(e) == "NO_IMAGES_FOUND":
            raise ValueError("NO_IMAGES_FOUND")
        print(f"[!] Error dalam embed_watermark_to_pdf_real_images: {e}")
        return {
            "success": False,
            "message": f"Error memproses PDF: {str(e)}",
            "error": str(e)
        }

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
        
        # Sort berdasarkan nomor halaman (untuk gambar PDF dengan format watermarked_pdf_image_p{n}_i{i}_{hash}.png)
        def extract_page_number(filename):
            import re
            # Cari pattern p{number}_i{number} dalam nama file
            match = re.search(r'_p(\d+)_i(\d+)_', filename)
            if match:
                page_num = int(match.group(1))
                img_num = int(match.group(2))
                return (page_num, img_num)
            # Fallback untuk format lain
            return (0, 0)
        
        image_files.sort(key=lambda x: extract_page_number(os.path.basename(x)))
        
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

def extract_watermark_from_pdf_real_images(pdf_path: str, output_dir: str) -> Dict[str, Any]:
    """
    Ekstrak watermark QR Code dari gambar-gambar asli yang ada di dalam PDF.
    
    Args:
        pdf_path (str): Path ke PDF yang akan diekstrak
        output_dir (str): Directory untuk menyimpan hasil ekstraksi
        
    Returns:
        Dict: Hasil ekstraksi dengan informasi QR Code yang ditemukan
    """
    try:
        from lsb_steganography import extract_qr_from_image
        
        # Buat direktori untuk gambar PDF dan hasil ekstraksi
        original_images_dir = os.path.join(output_dir, "original_images")
        extracted_qr_dir = os.path.join(output_dir, "extracted_qr")
        os.makedirs(original_images_dir, exist_ok=True)
        os.makedirs(extracted_qr_dir, exist_ok=True)
        
        # Ekstrak gambar asli dari PDF
        print("[*] Mengekstrak gambar asli dari PDF untuk mencari watermark...")
        extracted_images = extract_images_from_pdf(pdf_path, original_images_dir)
        
        if not extracted_images:
            return {
                "success": False,
                "message": "Tidak ada gambar yang ditemukan di dalam PDF",
                "error_type": "NO_IMAGES_FOUND"
            }
        
        # Get PDF info
        pdf_info = get_pdf_info(pdf_path)
        
        # Ekstrak watermark dari setiap gambar
        extracted_qrs = []
        
        for i, image_path in enumerate(extracted_images):
            try:
                print(f"[*] Mengekstrak watermark dari gambar {i+1}/{len(extracted_images)}...")
                
                # Generate path untuk QR hasil ekstraksi
                original_filename = os.path.basename(image_path)
                qr_filename = f"extracted_qr_from_{original_filename}"
                # Ganti ekstensi dengan .png
                qr_filename = os.path.splitext(qr_filename)[0] + ".png"
                qr_output_path = os.path.join(extracted_qr_dir, qr_filename)
                
                # Ekstrak menggunakan LSB
                try:
                    extract_qr_from_image(image_path, qr_output_path)
                    success = os.path.exists(qr_output_path)
                except Exception as e:
                    print(f"[!] Error ekstraksi gambar {i+1}: {e}")
                    success = False
                
                if success and os.path.exists(qr_output_path):
                    # Verifikasi bahwa hasil ekstraksi adalah gambar valid
                    try:
                        img = Image.open(qr_output_path)
                        # Cek apakah gambar tidak kosong
                        if img.size[0] > 0 and img.size[1] > 0:
                            file_size = os.path.getsize(qr_output_path)
                            relative_dir = os.path.basename(output_dir)
                            relative_path = f"{relative_dir}/extracted_qr/{qr_filename}"
                            
                            extracted_qrs.append({
                                "image_index": i + 1,
                                "original_image": original_filename,
                                "filename": qr_filename,
                                "url": f"/static/generated/{relative_path}",
                                "original": f"generated/{relative_dir}/original_images/{original_filename}",  # Add frontend format
                                "watermarked": f"generated/{relative_path}",  # QR result as "watermarked"
                                "path": qr_output_path,
                                "file_size": file_size,
                                "exists": True
                            })
                            print(f"[*] QR Code berhasil diekstrak dari gambar {i+1} (size: {file_size} bytes)")
                        else:
                            print(f"[!] QR Code kosong dari gambar {i+1}")
                            os.remove(qr_output_path)
                    except Exception as e:
                        print(f"[!] File hasil ekstraksi tidak valid untuk gambar {i+1}: {e}")
                        if os.path.exists(qr_output_path):
                            os.remove(qr_output_path)
                else:
                    print(f"[*] Tidak ada watermark ditemukan di gambar {i+1}")
                    
            except Exception as e:
                print(f"[!] Error mengekstrak gambar {i+1}: {e}")
                continue
        
        return {
            "success": True,
            "message": f"Proses ekstraksi selesai. Ditemukan {len(extracted_qrs)} QR Code dari {len(extracted_images)} gambar",
            "pdf_info": pdf_info,
            "extracted_qrs": extracted_qrs,
            "total_images": len(extracted_images),
            "qr_found": len(extracted_qrs)
        }
        
    except Exception as e:
        if str(e) == "NO_IMAGES_FOUND":
            raise ValueError("NO_IMAGES_FOUND")
        print(f"[!] Error dalam extract_watermark_from_pdf_real_images: {e}")
        return {
            "success": False,
            "message": f"Error mengekstrak watermark dari PDF: {str(e)}",
            "error": str(e)
        }

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
                                "url": f"/static/generated/{os.path.basename(output_dir)}/extracted_qr/{qr_filename}",
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

def convert_pdf_to_docx(pdf_path: str, docx_output_path: str) -> Dict[str, Any]:
    """
    Konversi PDF ke DOCX menggunakan pdf2docx.
    
    Args:
        pdf_path (str): Path ke file PDF
        docx_output_path (str): Path output file DOCX
        
    Returns:
        Dict: Hasil konversi dengan status dan informasi
    """
    try:
        from pdf2docx import Converter
        
        print(f"[*] Mengkonversi PDF ke DOCX: {pdf_path} -> {docx_output_path}")
        
        # Buat converter
        cv = Converter(pdf_path)
        
        # Konversi ke DOCX
        cv.convert(docx_output_path, start=0, end=None)
        cv.close()
        
        # Verifikasi file hasil
        if os.path.exists(docx_output_path):
            file_size = os.path.getsize(docx_output_path)
            print(f"[*] Konversi berhasil. File DOCX: {file_size} bytes")
            
            return {
                "success": True,
                "message": "PDF berhasil dikonversi ke DOCX",
                "docx_path": docx_output_path,
                "file_size": file_size
            }
        else:
            return {
                "success": False,
                "message": "File DOCX tidak terbuat setelah konversi",
                "error_type": "OUTPUT_FILE_NOT_CREATED"
            }
            
    except Exception as e:
        print(f"[!] Error konversi PDF ke DOCX: {e}")
        return {
            "success": False,
            "message": f"Gagal konversi PDF ke DOCX: {str(e)}",
            "error": str(e),
            "error_type": "CONVERSION_ERROR"
        }

def convert_docx_to_pdf(docx_path: str, pdf_output_path: str) -> Dict[str, Any]:
    """
    Konversi DOCX ke PDF menggunakan docx2pdf.
    
    Args:
        docx_path (str): Path ke file DOCX
        pdf_output_path (str): Path output file PDF
        
    Returns:
        Dict: Hasil konversi dengan status dan informasi
    """
    try:
        from docx2pdf import convert
        
        print(f"[*] Mengkonversi DOCX ke PDF: {docx_path} -> {pdf_output_path}")
        
        # Konversi DOCX ke PDF
        convert(docx_path, pdf_output_path)
        
        # Verifikasi file hasil
        if os.path.exists(pdf_output_path):
            file_size = os.path.getsize(pdf_output_path)
            print(f"[*] Konversi berhasil. File PDF: {file_size} bytes")
            
            return {
                "success": True,
                "message": "DOCX berhasil dikonversi ke PDF",
                "pdf_path": pdf_output_path,
                "file_size": file_size
            }
        else:
            return {
                "success": False,
                "message": "File PDF tidak terbuat setelah konversi",
                "error_type": "OUTPUT_FILE_NOT_CREATED"
            }
            
    except Exception as e:
        print(f"[!] Error konversi DOCX ke PDF: {e}")
        return {
            "success": False,
            "message": f"Gagal konversi DOCX ke PDF: {str(e)}",
            "error": str(e),
            "error_type": "CONVERSION_ERROR"
        }

def embed_watermark_to_pdf_via_docx(pdf_path: str, qr_path: str, output_pdf_path: str) -> Dict[str, Any]:
    """
    Embed watermark ke PDF melalui konversi PDF -> DOCX -> watermark -> PDF.
    
    Args:
        pdf_path (str): Path ke file PDF asli
        qr_path (str): Path ke QR Code untuk watermark
        output_pdf_path (str): Path output PDF watermarked
        
    Returns:
        Dict: Hasil proses dengan informasi lengkap
    """
    try:
        from main import embed_watermark_to_docx
        
        # Generate temporary paths
        temp_docx_path = pdf_path.replace('.pdf', '_temp.docx')
        watermarked_docx_path = pdf_path.replace('.pdf', '_watermarked.docx')
        
        print("[*] Memulai proses watermark PDF via DOCX...")
        
        # Step 1: PDF -> DOCX
        print("[*] Step 1: Konversi PDF ke DOCX")
        pdf_to_docx_result = convert_pdf_to_docx(pdf_path, temp_docx_path)
        
        if not pdf_to_docx_result.get("success"):
            return {
                "success": False,
                "message": f"Gagal konversi PDF ke DOCX: {pdf_to_docx_result.get('message', 'Unknown error')}",
                "error_type": "PDF_TO_DOCX_FAILED",
                "step": "pdf_to_docx"
            }
        
        # Step 2: Embed watermark ke DOCX
        print("[*] Step 2: Embed watermark ke DOCX")
        try:
            watermark_result = embed_watermark_to_docx(temp_docx_path, qr_path, watermarked_docx_path)
            
            if not watermark_result.get("success"):
                return {
                    "success": False,
                    "message": f"Gagal embed watermark ke DOCX: {watermark_result.get('message', 'Unknown error')}",
                    "error_type": "WATERMARK_EMBED_FAILED",
                    "step": "watermark_embed"
                }
                
        except ValueError as ve:
            if str(ve) == "NO_IMAGES_FOUND":
                return {
                    "success": False,
                    "message": "Dokumen tidak mengandung gambar untuk watermark",
                    "error_type": "NO_IMAGES_FOUND",
                    "step": "watermark_embed"
                }
            else:
                return {
                    "success": False,
                    "message": f"Error embed watermark: {str(ve)}",
                    "error_type": "WATERMARK_EMBED_ERROR",
                    "step": "watermark_embed"
                }
        
        # Step 3: DOCX -> PDF
        print("[*] Step 3: Konversi DOCX watermarked ke PDF")
        docx_to_pdf_result = convert_docx_to_pdf(watermarked_docx_path, output_pdf_path)
        
        if not docx_to_pdf_result.get("success"):
            return {
                "success": False,
                "message": f"Gagal konversi DOCX ke PDF: {docx_to_pdf_result.get('message', 'Unknown error')}",
                "error_type": "DOCX_TO_PDF_FAILED",
                "step": "docx_to_pdf"
            }
        
        # Cleanup temporary files
        try:
            if os.path.exists(temp_docx_path):
                os.remove(temp_docx_path)
            if os.path.exists(watermarked_docx_path):
                os.remove(watermarked_docx_path)
        except Exception as e:
            print(f"[!] Warning: Gagal hapus file temporary: {e}")
        
        # Get file size info
        original_size = os.path.getsize(pdf_path)
        processed_size = os.path.getsize(output_pdf_path)
        
        return {
            "success": True,
            "message": "PDF berhasil di-watermark via DOCX conversion",
            "processed_images": watermark_result.get("processed_images", []),
            "qr_image": watermark_result.get("qr_image", ""),
            "public_dir": watermark_result.get("public_dir", ""),
            "qr_info": watermark_result.get("qr_info", None),
            "analysis": {
                "qr_analysis": watermark_result.get("qr_analysis", {}),
                "image_analyses": watermark_result.get("image_analyses", []),
                "detailed_metrics": watermark_result.get("detailed_metrics", [])
            },
            "file_size_info": {
                "original_size": original_size,
                "processed_size": processed_size,
                "size_difference": processed_size - original_size,
                "size_change_percentage": ((processed_size - original_size) / original_size) * 100 if original_size > 0 else 0
            },
            "method": "pdf_via_docx"
        }
        
    except Exception as e:
        print(f"[!] Error dalam embed_watermark_to_pdf_via_docx: {e}")
        
        # Cleanup on error
        try:
            if 'temp_docx_path' in locals() and os.path.exists(temp_docx_path):
                os.remove(temp_docx_path)
            if 'watermarked_docx_path' in locals() and os.path.exists(watermarked_docx_path):
                os.remove(watermarked_docx_path)
        except Exception:
            pass
        
        return {
            "success": False,
            "message": f"Error proses watermark PDF via DOCX: {str(e)}",
            "error": str(e),
            "error_type": "GENERAL_ERROR"
        }

def extract_watermark_from_pdf_via_docx(pdf_path: str, output_dir: str) -> Dict[str, Any]:
    """
    Ekstrak watermark dari PDF melalui konversi PDF -> DOCX -> ekstrak -> hasil.
    
    Args:
        pdf_path (str): Path ke PDF yang akan diekstrak
        output_dir (str): Directory untuk menyimpan hasil ekstraksi
        
    Returns:
        Dict: Hasil ekstraksi dengan informasi QR Code yang ditemukan
    """
    try:
        from main import extract_images_from_docx
        from lsb_steganography import extract_qr_from_image
        
        # Generate temporary path
        temp_docx_path = os.path.join(output_dir, "temp_for_extraction.docx")
        extracted_images_dir = os.path.join(output_dir, "extracted_images")
        extracted_qr_dir = os.path.join(output_dir, "extracted_qr")
        
        os.makedirs(extracted_images_dir, exist_ok=True)
        os.makedirs(extracted_qr_dir, exist_ok=True)
        
        print("[*] Memulai proses ekstraksi PDF via DOCX...")
        
        # Step 1: PDF -> DOCX
        print("[*] Step 1: Konversi PDF ke DOCX")
        pdf_to_docx_result = convert_pdf_to_docx(pdf_path, temp_docx_path)
        
        if not pdf_to_docx_result.get("success"):
            return {
                "success": False,
                "message": f"Gagal konversi PDF ke DOCX: {pdf_to_docx_result.get('message', 'Unknown error')}",
                "error_type": "PDF_TO_DOCX_FAILED"
            }
        
        # Step 2: Ekstrak gambar dari DOCX
        print("[*] Step 2: Ekstrak gambar dari DOCX")
        extracted_images = extract_images_from_docx(temp_docx_path, extracted_images_dir)
        
        if not extracted_images:
            # Cleanup
            if os.path.exists(temp_docx_path):
                os.remove(temp_docx_path)
            
            return {
                "success": False,
                "message": "Tidak ada gambar ditemukan dalam dokumen",
                "error_type": "NO_IMAGES_FOUND"
            }
        
        # Step 3: Ekstrak watermark dari setiap gambar
        print(f"[*] Step 3: Ekstrak watermark dari {len(extracted_images)} gambar")
        extracted_qrs = []
        
        for i, image_path in enumerate(extracted_images):
            try:
                qr_filename = f"extracted_qr_{i+1}_{uuid.uuid4().hex[:8]}.png"
                qr_output_path = os.path.join(extracted_qr_dir, qr_filename)
                
                # Ekstrak menggunakan LSB
                extract_qr_from_image(image_path, qr_output_path)
                
                if os.path.exists(qr_output_path):
                    # Verifikasi gambar valid
                    try:
                        img = Image.open(qr_output_path)
                        if img.size[0] > 0 and img.size[1] > 0:
                            extracted_qrs.append({
                                "image_index": i + 1,
                                "filename": qr_filename,
                                "url": f"/static/generated/{os.path.basename(output_dir)}/extracted_qr/{qr_filename}",
                                "path": qr_output_path
                            })
                            print(f"[*] QR Code berhasil diekstrak dari gambar {i+1}")
                        else:
                            os.remove(qr_output_path)
                    except Exception as e:
                        print(f"[!] File hasil ekstraksi tidak valid untuk gambar {i+1}: {e}")
                        if os.path.exists(qr_output_path):
                            os.remove(qr_output_path)
                else:
                    print(f"[*] Tidak ada watermark ditemukan di gambar {i+1}")
                    
            except Exception as e:
                print(f"[!] Error mengekstrak gambar {i+1}: {e}")
                continue
        
        # Cleanup temporary DOCX
        if os.path.exists(temp_docx_path):
            os.remove(temp_docx_path)
        
        # Get PDF info
        pdf_info = get_pdf_info(pdf_path)
        
        return {
            "success": True,
            "message": f"Proses ekstraksi selesai via DOCX. Ditemukan {len(extracted_qrs)} QR Code dari {len(extracted_images)} gambar",
            "pdf_info": pdf_info,
            "extracted_qrs": extracted_qrs,
            "total_images": len(extracted_images),
            "qr_found": len(extracted_qrs),
            "method": "pdf_via_docx"
        }
        
    except Exception as e:
        print(f"[!] Error dalam extract_watermark_from_pdf_via_docx: {e}")
        
        # Cleanup on error
        try:
            if 'temp_docx_path' in locals() and os.path.exists(temp_docx_path):
                os.remove(temp_docx_path)
        except Exception:
            pass
        
        return {
            "success": False,
            "message": f"Error ekstraksi PDF via DOCX: {str(e)}",
            "error": str(e),
            "error_type": "GENERAL_ERROR"
        }

# --- End of pdf_utils.py ---