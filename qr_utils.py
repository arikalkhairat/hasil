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
        
        qr_data = {
            "data": data,
            "crc32": checksum,
            "timestamp": int(time.time()) if 'time' in globals() else None
        }
        
        return qr_data
    except Exception as e:
        print(f"[!] Error menambahkan CRC32: {e}")
        return {"data": data, "crc32": None}

def verify_crc32_checksum(qr_data_with_checksum: dict) -> dict:
    """
    Memverifikasi integritas data menggunakan CRC32 checksum.
    
    Args:
        qr_data_with_checksum (dict): Data QR dengan checksum
        
    Returns:
        dict: Hasil verifikasi dengan detail lengkap
    """
    try:
        if not isinstance(qr_data_with_checksum, dict):
            return {
                "valid": False,
                "error": "Data tidak dalam format yang benar"
            }
            
        original_data = qr_data_with_checksum.get("data")
        stored_checksum = qr_data_with_checksum.get("crc32")
        
        if not original_data or stored_checksum is None:
            return {
                "valid": False,
                "error": "Data atau checksum tidak lengkap"
            }
        
        # Verifikasi checksum data
        calculated_checksum = zlib.crc32(original_data.encode('utf-8')) & 0xffffffff
        data_valid = calculated_checksum == stored_checksum
        
        return {
            "valid": data_valid,
            "data_valid": data_valid,
            "timestamp": qr_data_with_checksum.get("timestamp")
        }
        
    except Exception as e:
        print(f"[!] Error verifikasi CRC32: {e}")
        return {
            "valid": False,
            "error": str(e)
        }

def analyze_image_pixels(image_path: str, sample_size: int = 100) -> dict:
    """
    Menganalisis nilai pixel dari gambar dan mengembalikan statistik detail.
    
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
        
        # Statistik pixel yang lebih detail
        pixel_stats = {
            "mean_rgb": [float(np.mean(image_rgb[:,:,0])), float(np.mean(image_rgb[:,:,1])), float(np.mean(image_rgb[:,:,2]))],
            "std_rgb": [float(np.std(image_rgb[:,:,0])), float(np.std(image_rgb[:,:,1])), float(np.std(image_rgb[:,:,2]))],
            "min_rgb": [int(np.min(image_rgb[:,:,0])), int(np.min(image_rgb[:,:,1])), int(np.min(image_rgb[:,:,2]))],
            "max_rgb": [int(np.max(image_rgb[:,:,0])), int(np.max(image_rgb[:,:,1])), int(np.max(image_rgb[:,:,2]))],
            "median_rgb": [float(np.median(image_rgb[:,:,0])), float(np.median(image_rgb[:,:,1])), float(np.median(image_rgb[:,:,2]))]
        }
        
        # Hitung distribusi nilai pixel per channel
        hist_r, _ = np.histogram(image_rgb[:,:,0], bins=256, range=(0, 256))
        hist_g, _ = np.histogram(image_rgb[:,:,1], bins=256, range=(0, 256))
        hist_b, _ = np.histogram(image_rgb[:,:,2], bins=256, range=(0, 256))
        
        # Analisis pixel berdasarkan region (corner, center, edge)
        region_analysis = get_pixel_region_analysis(image_rgb, width, height)
        
        # Pixel intensity distribution
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        intensity_stats = {
            "mean_intensity": float(np.mean(gray_image)),
            "std_intensity": float(np.std(gray_image)),
            "dark_pixels": int(np.sum(gray_image < 85)),  # < 33% of 255
            "medium_pixels": int(np.sum((gray_image >= 85) & (gray_image < 170))),  # 33-67%
            "bright_pixels": int(np.sum(gray_image >= 170))  # > 67%
        }
        
        return {
            "success": True,
            "image_info": {
                "width": width,
                "height": height,
                "channels": channels,
                "total_pixels": width * height,
                "file_size_bytes": file_size,
                "file_size_kb": round(file_size / 1024, 2),
                "aspect_ratio": round(width / height, 3),
                "megapixels": round((width * height) / 1000000, 2),
                "pixel_density": f"{width}×{height}"
            },
            "pixel_samples": pixel_samples,
            "pixel_statistics": pixel_stats,
            "pixel_distribution": {
                "red_histogram": hist_r.tolist()[:50],  # Simplified for frontend
                "green_histogram": hist_g.tolist()[:50],
                "blue_histogram": hist_b.tolist()[:50]
            },
            "region_analysis": region_analysis,
            "intensity_analysis": intensity_stats,
            "color_analysis": {
                "dominant_color": get_dominant_color(image_rgb),
                "color_variance": float(np.var(image_rgb)),
                "brightness": float(np.mean(image_rgb)),
                "contrast": float(np.std(image_rgb))
            }
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
        
        # Robust MSE calculation
        try:
            mse = np.mean((original_float - watermarked_float) ** 2)
            # Ensure MSE is non-negative and finite
            if not np.isfinite(mse) or mse < 0:
                mse = 0.0
            mse = float(mse)  # Convert to Python float
        except Exception as e:
            print(f"[!] Error calculating MSE: {e}")
            mse = 0.0
        
        # Robust PSNR calculation with error handling
        if mse == 0:
            psnr = 999.99  # Perfect quality
        else:
            try:
                max_pixel_value = 255.0
                sqrt_mse = np.sqrt(mse)
                if sqrt_mse == 0:
                    psnr = 999.99
                else:
                    log_val = max_pixel_value / sqrt_mse
                    if log_val <= 0:
                        psnr = 0  # Very poor quality
                    else:
                        psnr = 20 * np.log10(log_val)
                        # Clamp PSNR to reasonable range
                        psnr = max(0, min(psnr, 999.99))
            except Exception as e:
                print(f"[!] Error calculating PSNR: {e}")
                psnr = 0
        
        # Interpretasi kualitas berdasarkan PSNR
        if psnr >= 999:
            quality = "Identik"
        elif psnr > 40:
            quality = "Sangat Baik"
        elif psnr > 30:
            quality = "Baik"
        elif psnr > 20:
            quality = "Cukup"
        else:
            quality = "Buruk"
        
        # Ensure all values are JSON-safe
        try:
            mse_safe = float(mse) if np.isfinite(mse) else 0.0
            psnr_safe = float(psnr) if np.isfinite(psnr) else 0.0
        except Exception:
            mse_safe = 0.0
            psnr_safe = 0.0
            
        return {
            "success": True,
            "mse": mse_safe,
            "psnr": psnr_safe,
            "quality": quality,
            "max_pixel_value": 255
        }
        
    except Exception as e:
        return {"error": f"Error menghitung MSE/PSNR: {str(e)}"}

def get_pixel_region_analysis(image_rgb: np.ndarray, width: int, height: int) -> dict:
    """
    Menganalisis pixel berdasarkan region dalam gambar (corner, center, edges).
    
    Args:
        image_rgb: Array numpy gambar dalam format RGB
        width: Lebar gambar
        height: Tinggi gambar
        
    Returns:
        dict: Analisis pixel per region
    """
    try:
        # Define regions
        h_third = height // 3
        w_third = width // 3
        
        # Center region
        center_region = image_rgb[h_third:2*h_third, w_third:2*w_third]
        
        # Corner regions
        top_left = image_rgb[0:h_third, 0:w_third]
        top_right = image_rgb[0:h_third, 2*w_third:width]
        bottom_left = image_rgb[2*h_third:height, 0:w_third]
        bottom_right = image_rgb[2*h_third:height, 2*w_third:width]
        
        # Edge regions
        top_edge = image_rgb[0:h_third//2, :]
        bottom_edge = image_rgb[height-h_third//2:height, :]
        left_edge = image_rgb[:, 0:w_third//2]
        right_edge = image_rgb[:, width-w_third//2:width]
        
        def get_region_stats(region):
            if region.size == 0:
                return {"mean_brightness": 0, "pixel_count": 0}
            return {
                "mean_brightness": float(np.mean(region)),
                "pixel_count": int(region.shape[0] * region.shape[1])
            }
        
        return {
            "center": get_region_stats(center_region),
            "corners": {
                "top_left": get_region_stats(top_left),
                "top_right": get_region_stats(top_right),
                "bottom_left": get_region_stats(bottom_left),
                "bottom_right": get_region_stats(bottom_right)
            },
            "edges": {
                "top": get_region_stats(top_edge),
                "bottom": get_region_stats(bottom_edge),
                "left": get_region_stats(left_edge),
                "right": get_region_stats(right_edge)
            }
        }
        
    except Exception as e:
        print(f"Error dalam analisis region: {e}")
        return {"error": str(e)}

def get_dominant_color(image_rgb: np.ndarray) -> list:
    """
    Mendapatkan warna dominan dalam gambar menggunakan K-means clustering.
    
    Args:
        image_rgb: Array numpy gambar dalam format RGB
        
    Returns:
        list: RGB values dari warna dominan [R, G, B]
    """
    try:
        # Reshape gambar menjadi array 2D (pixel, RGB)
        pixels = image_rgb.reshape((-1, 3))
        
        # Sample pixel jika terlalu banyak (untuk performa)
        if len(pixels) > 10000:
            indices = np.random.choice(len(pixels), 10000, replace=False)
            pixels = pixels[indices]
        
        # Simple approach: hitung rata-rata dari semua pixel
        # (untuk implementasi yang lebih sophisticated, bisa gunakan K-means)
        dominant_color = np.mean(pixels, axis=0)
        
        return [int(dominant_color[0]), int(dominant_color[1]), int(dominant_color[2])]
        
    except Exception as e:
        print(f"Error mendapatkan warna dominan: {e}")
        return [128, 128, 128]  # Default gray color

def get_detailed_pixel_info(image_path: str) -> dict:
    """
    Mendapatkan informasi pixel yang sangat detail untuk debugging dan analisis.
    
    Args:
        image_path: Path ke file gambar
        
    Returns:
        dict: Informasi detail pixel
    """
    try:
        analysis = analyze_image_pixels(image_path, sample_size=200)
        
        if not analysis.get("success"):
            return analysis
            
        # Tambahan informasi khusus untuk LSB analysis
        image = cv2.imread(image_path)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Analisis LSB dari channel biru (yang digunakan untuk steganography)
        blue_channel = image_rgb[:,:,2]
        lsb_values = blue_channel & 1  # Extract LSB
        
        lsb_analysis = {
            "lsb_0_count": int(np.sum(lsb_values == 0)),
            "lsb_1_count": int(np.sum(lsb_values == 1)),
            "lsb_distribution": float(np.mean(lsb_values))  # Ratio of 1s
        }
        
        analysis["lsb_analysis"] = lsb_analysis
        analysis["steganography_capacity"] = analysis["image_info"]["total_pixels"]  # 1 bit per pixel in blue channel
        
        return analysis
        
    except Exception as e:
        return {"error": f"Error mendapatkan info detail pixel: {str(e)}"}

# --- End of qr_utils.py ---
