# File: qr_utils.py
# Deskripsi: Fungsi utilitas untuk membuat dan membaca QR Code.

import qrcode
import cv2
from PIL import Image
import os

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

# --- End of qr_utils.py ---
