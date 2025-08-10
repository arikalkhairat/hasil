# File: qr_utils.py
# Deskripsi: Fungsi utilitas untuk membuat dan membaca QR Code.

import qrcode
import cv2
from PIL import Image
import os
import zlib
import time
import numpy as np

def generate_qr(data: str, output_path: str):
    """
    Membuat citra QR Code dari data teks dan menyimpannya ke file.

    Args:
        data (str): Data teks yang akan dikodekan.
        output_path (str): Path file untuk menyimpan citra QR Code (misal, 'qrcode.png').

    Raises:
        Exception: Jika terjadi error saat pembuatan QR Code.
    """
    try:
        # Membuat instance QRCode
        qr = qrcode.QRCode(
            version=1, # Kontrol ukuran QR Code (1-40), None untuk otomatis
            error_correction=qrcode.constants.ERROR_CORRECT_L, # Tingkat koreksi error (L, M, Q, H)
            box_size=10, # Ukuran setiap kotak (piksel) dalam QR Code
            border=4, # Lebar border di sekitar QR Code (minimum 4 menurut standar)
        )
        # Menambahkan data ke QR Code
        qr.add_data(data)
        qr.make(fit=True) # fit=True menyesuaikan ukuran QR Code dengan data

        # Membuat citra dari objek QRCode
        img = qr.make_image(fill_color="black", back_color="white")
        # Menyimpan citra ke file
        img.save(output_path)
        print(f"[*] QR Code berhasil dibuat dan disimpan di: {output_path}")
    except Exception as e:
        # Menangani potensi error saat pembuatan atau penyimpanan
        print(f"[!] Error saat membuat QR Code: {e}")
        raise # Melempar kembali error untuk ditangani di level lebih tinggi jika perlu

def read_qr(image_path: str) -> list[str]:
    """
    Membaca data dari sebuah citra QR Code menggunakan OpenCV.

    Args:
        image_path (str): Path ke file citra QR Code.

    Returns:
        list[str]: List berisi data (string UTF-8) yang berhasil dibaca dari QR Code.
                   List bisa kosong jika tidak ada QR Code yang terdeteksi.

    Raises:
        FileNotFoundError: Jika file citra tidak ditemukan.
        Exception: Jika terjadi error lain saat membuka atau membaca citra.
    """
    # Memastikan file ada sebelum mencoba membukanya
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"File tidak ditemukan: {image_path}")

    try:
        # Membaca citra menggunakan OpenCV
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Gagal membaca citra: {image_path}")

        # Inisialisasi QR code detector
        qr_detector = cv2.QRCodeDetector()
        
        # Membaca QR code dari citra
        # retval: bool (berhasil/tidak)
        # decoded_info: string (data QR code)
        # points: numpy.ndarray (koordinat QR code)
        # straight_qrcode: numpy.ndarray (citra QR code yang telah diluruskan)
        retval, decoded_info, points, straight_qrcode = qr_detector.detectAndDecodeMulti(img)
        
        # Jika QR code terdeteksi
        if retval:
            # Filter out empty strings and convert to list
            data_list = [text for text in decoded_info if text]
        else:
            data_list = []

        # Memberi informasi jika tidak ada QR Code yang terdeteksi
        if not data_list:
            print(f"[!] Tidak ada QR Code yang terdeteksi di: {image_path}")
        return data_list
    except Exception as e:
        # Menangani potensi error saat membuka citra atau proses decoding
        print(f"[!] Error saat membaca QR Code: {e}")
        raise # Melempar kembali error

def add_crc32_checksum(data: str) -> dict:
    """
    Menambahkan CRC32 checksum untuk validasi integritas data QR Code.
    
    Args:
        data (str): Data asli QR Code
        
    Returns:
        dict: Data dengan checksum
    """
    try:
        checksum = zlib.crc32(data.encode('utf-8')) & 0xffffffff
        
        return {
            "data": data,
            "crc32": checksum,
            "timestamp": int(time.time()) if 'time' in globals() else None
        }
    except Exception as e:
        print(f"[!] Error menambahkan CRC32: {e}")
        return {"data": data, "crc32": None}

def verify_crc32_checksum(qr_data_with_checksum: dict) -> bool:
    """
    Memverifikasi integritas data menggunakan CRC32 checksum.
    
    Args:
        qr_data_with_checksum (dict): Data QR dengan checksum
        
    Returns:
        bool: True jika valid, False jika tidak
    """
    try:
        if not isinstance(qr_data_with_checksum, dict):
            return False
            
        original_data = qr_data_with_checksum.get("data")
        stored_checksum = qr_data_with_checksum.get("crc32")
        
        if not original_data or stored_checksum is None:
            return False
            
        calculated_checksum = zlib.crc32(original_data.encode('utf-8')) & 0xffffffff
        return calculated_checksum == stored_checksum
        
    except Exception as e:
        print(f"[!] Error verifikasi CRC32: {e}")
        return False

def analyze_image_pixels(image_path: str, sample_size: int = 100) -> dict:
    """
    Menganalisis nilai pixel dari gambar dan mengembalikan statistik.
    
    Args:
        image_path (str): Path ke file gambar
        sample_size (int): Jumlah pixel sample untuk ditampilkan
        
    Returns:
        dict: Analisis pixel termasuk sample values, statistik, dan info file
    """
    try:
        # Baca gambar
        image = cv2.imread(image_path)
        if image is None:
            return {"error": "Tidak dapat membaca gambar"}
        
        # Konversi ke RGB untuk PIL
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        height, width, channels = image.shape
        
        # Informasi file
        file_size = os.path.getsize(image_path)
        
        # Sample pixel values (dari beberapa posisi acak)
        np.random.seed(42)  # Untuk hasil konsisten
        sample_positions = np.random.choice(height * width, min(sample_size, height * width), replace=False)
        
        pixel_samples = []
        for pos in sample_positions[:20]:  # Ambil 20 sample untuk ditampilkan
            y, x = divmod(pos, width)
            pixel_rgb = image_rgb[y, x]
            pixel_samples.append({
                "position": [int(x), int(y)],
                "rgb": [int(pixel_rgb[0]), int(pixel_rgb[1]), int(pixel_rgb[2])]
            })
        
        # Statistik pixel
        pixel_stats = {
            "mean_rgb": [float(np.mean(image_rgb[:,:,0])), float(np.mean(image_rgb[:,:,1])), float(np.mean(image_rgb[:,:,2]))],
            "std_rgb": [float(np.std(image_rgb[:,:,0])), float(np.std(image_rgb[:,:,1])), float(np.std(image_rgb[:,:,2]))],
            "min_rgb": [int(np.min(image_rgb[:,:,0])), int(np.min(image_rgb[:,:,1])), int(np.min(image_rgb[:,:,2]))],
            "max_rgb": [int(np.max(image_rgb[:,:,0])), int(np.max(image_rgb[:,:,1])), int(np.max(image_rgb[:,:,2]))]
        }
        
        return {
            "success": True,
            "image_info": {
                "width": width,
                "height": height,
                "channels": channels,
                "total_pixels": width * height,
                "file_size_bytes": file_size,
                "file_size_kb": round(file_size / 1024, 2)
            },
            "pixel_samples": pixel_samples,
            "pixel_statistics": pixel_stats
        }
        
    except Exception as e:
        return {"error": f"Error menganalisis gambar: {str(e)}"}

def calculate_mse_psnr(original_path: str, watermarked_path: str) -> dict:
    """
    Menghitung MSE (Mean Squared Error) dan PSNR (Peak Signal-to-Noise Ratio) 
    antara gambar asli dan gambar yang sudah di-watermark.
    
    Args:
        original_path (str): Path ke gambar asli
        watermarked_path (str): Path ke gambar yang sudah di-watermark
        
    Returns:
        dict: Hasil perhitungan MSE dan PSNR
    """
    try:
        # Baca kedua gambar
        original = cv2.imread(original_path)
        watermarked = cv2.imread(watermarked_path)
        
        if original is None or watermarked is None:
            return {"error": "Tidak dapat membaca salah satu gambar"}
        
        # Pastikan kedua gambar memiliki ukuran yang sama
        if original.shape != watermarked.shape:
            return {"error": "Ukuran gambar tidak sama"}
        
        # Konversi ke float untuk perhitungan yang akurat
        original_float = original.astype(np.float64)
        watermarked_float = watermarked.astype(np.float64)
        
        # Hitung MSE
        mse = np.mean((original_float - watermarked_float) ** 2)
        
        # Hitung PSNR
        if mse == 0:
            psnr = float('inf')
        else:
            max_pixel_value = 255.0
            psnr = 20 * np.log10(max_pixel_value / np.sqrt(mse))
        
        # Interpretasi kualitas berdasarkan PSNR
        if psnr == float('inf'):
            quality = "Identik"
        elif psnr > 40:
            quality = "Sangat Baik"
        elif psnr > 30:
            quality = "Baik"
        elif psnr > 20:
            quality = "Cukup"
        else:
            quality = "Buruk"
        
        return {
            "success": True,
            "mse": float(mse),
            "psnr": float(psnr),
            "quality": quality,
            "max_pixel_value": 255
        }
        
    except Exception as e:
        return {"error": f"Error menghitung MSE/PSNR: {str(e)}"}

# --- End of qr_utils.py ---
