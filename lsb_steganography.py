# File: lsb_steganography.py
# Deskripsi: Fungsi inti untuk menyisipkan dan mengekstrak QR Code menggunakan LSB.

from PIL import Image
from PIL.Image import Resampling
import itertools
import os
import math

HEADER_TERMINATOR_BIN = '00000000'
HEADER_TERMINATOR_LEN = len(HEADER_TERMINATOR_BIN)


def _int_to_binary(integer: int, bits: int) -> str:
    """
    Konversi integer ke string biner dengan panjang tetap.
    Memastikan output selalu memiliki jumlah bit yang ditentukan dengan padding '0' di depan.
    Contoh: _int_to_binary(10, 8) -> '00001010'
    """
    return format(integer, f'0{bits}b')


def _binary_to_int(binary_string: str) -> int:
    """Konversi string biner ke integer."""
    return int(binary_string, 2)


def _embed_bit(pixel_value: int, bit: str) -> int:
    """
    Menyisipkan satu bit ('0' atau '1') ke LSB (Least Significant Bit)
    dari sebuah nilai integer (byte piksel).
    Jika bit = '0', LSB di-set ke 0.
    Jika bit = '1', LSB di-set ke 1.
    """
    if bit == '0':
        return pixel_value & 254
    else:
        return pixel_value | 1


def _extract_lsb(pixel_value: int) -> str:
    """
    Mengekstrak LSB dari sebuah nilai integer (byte piksel).
    Mengembalikan '1' jika nilai ganjil (LSB=1), '0' jika genap (LSB=0).
    """
    return '1' if pixel_value % 2 == 1 else '0'


def _resize_qr_for_capacity(qr_img, max_capacity: int):
    """
    Menyesuaikan ukuran QR code agar muat dalam kapasitas citra penampung.

    Args:
        qr_img: Objek Image dari QR code yang perlu disesuaikan.
        max_capacity: Kapasitas maksimum yang tersedia dalam bit.

    Returns:
        Objek Image dari QR code yang telah diresize.
    """
    # Kurangi kapasitas untuk header (16+16+8 bit)
    available_bits_for_qr = max_capacity - (16 + 16 + HEADER_TERMINATOR_LEN)

    if available_bits_for_qr <= 0:
        raise ValueError("Kapasitas cover image terlalu kecil bahkan untuk header saja.")

    # Hitung dimensi maksimum berdasarkan akar kuadrat dari kapasitas
    # Kita perlu bilangan bulat yang ketika dikuadratkan <= available_bits_for_qr
    new_dimension = int(math.sqrt(available_bits_for_qr))

    # Jika QR lebih kecil dari dimensi maksimal, tidak perlu diresize
    if qr_img.width <= new_dimension and qr_img.height <= new_dimension:
        return qr_img

    # Resize QR secara proporsional tapi tidak lebih besar dari dimensi maksimum
    new_size = min(new_dimension, new_dimension)
    # Resize QR code dengan tetap mempertahankan mode
    resized_qr = qr_img.resize((new_size, new_size), Resampling.NEAREST)
    print(f"[*] QR code diresize dari {qr_img.width}x{qr_img.height} ke {new_size}x{new_size} agar muat dalam kapasitas.")
    return resized_qr


def embed_qr_to_image(cover_image_path: str, qr_image_path: str, output_stego_path: str, resize_qr_if_needed: bool = True):
    """
    Menyisipkan citra QR Code ke dalam LSB channel Biru dari citra penampung.

    Args:
        cover_image_path (str): Path ke citra penampung (disarankan PNG).
        qr_image_path (str): Path ke citra QR Code yang akan disembunyikan (harus hitam putih).
        output_stego_path (str): Path untuk menyimpan citra hasil (harus PNG).
        resize_qr_if_needed (bool): Jika True, QR code akan diresize otomatis agar muat dalam kapasitas.

    Raises:
        FileNotFoundError: Jika file input tidak ditemukan.
        ValueError: Jika kapasitas citra penampung tidak cukup atau format output salah.
        Exception: Jika terjadi error lain selama proses.
    """

    print("[*] Memulai proses embed_qr_to_image")  # Log awal fungsi

    # Validasi keberadaan file input
    if not os.path.exists(cover_image_path):
        raise FileNotFoundError(f"File cover tidak ditemukan: {cover_image_path}")
    if not os.path.exists(qr_image_path):
        raise FileNotFoundError(f"File QR Code tidak ditemukan: {qr_image_path}")
    # Memastikan output adalah PNG untuk menjaga integritas LSB
    if not output_stego_path.lower().endswith('.png'):
        raise ValueError("Output file harus berformat PNG untuk menjaga LSB.")

    try:
        # 1. Buka kedua citra
        cover_img = Image.open(cover_image_path).convert('RGB')  # Pastikan format RGB
        qr_img = Image.open(qr_image_path).convert('1')  # Konversi QR ke mode 1-bit (hitam/putih)

        # Cek apakah file cover dan QR sama
        if os.path.abspath(cover_image_path) == os.path.abspath(qr_image_path):
            print("[!] Warning: File cover dan QR sama. Ini dapat menyebabkan masalah kapasitas.")

        cover_width, cover_height = cover_img.size
        qr_width, qr_height = qr_img.size

        # Hitung kapasitas citra penampung
        max_capacity = cover_width * cover_height

        # 2. Buat aliran bit dari QR Code
        # Cek dulu jika perlu resize QR
        original_qr_size = (qr_width, qr_height)

        # Perkiraan kebutuhan bit untuk header dan data QR
        header_bits_len = 16 + 16 + HEADER_TERMINATOR_LEN
        qr_bits_len = qr_width * qr_height
        total_bits_needed = header_bits_len + qr_bits_len

        # Jika kapasitas tidak cukup, resize QR jika opsi diaktifkan
        if total_bits_needed > max_capacity:
            if resize_qr_if_needed:
                qr_img = _resize_qr_for_capacity(qr_img, max_capacity)
                qr_width, qr_height = qr_img.size
                print("[*] QR code diresize untuk menyesuaikan dengan kapasitas.")
            else:
                raise ValueError(f"Kapasitas citra tidak cukup. Dibutuhkan: {total_bits_needed} bits, Tersedia: {max_capacity} bits.")

        # Iterasi piksel QR, '1' untuk hitam (nilai 0 di mode '1'), '0' untuk putih (nilai 255)
        qr_bits = "".join(['1' if qr_img.getpixel((x, y)) == 0 else '0'
                          for y in range(qr_height) for x in range(qr_width)])
        num_qr_bits = len(qr_bits)

        # 3. Buat header: 16 bit untuk lebar QR, 16 bit untuk tinggi QR, + terminator
        header_bits = _int_to_binary(qr_width, 16) + _int_to_binary(qr_height, 16) + HEADER_TERMINATOR_BIN
        num_header_bits = len(header_bits)

        # Total bit yang perlu disisipkan
        total_bits_to_embed = num_header_bits + num_qr_bits

        # 4. Cek kapasitas final citra penampung setelah resize (jika ada)
        if total_bits_to_embed > max_capacity:
            raise ValueError(f"Kapasitas citra tidak cukup bahkan setelah resize. Dibutuhkan: {total_bits_to_embed} bits, Tersedia: {max_capacity} bits.")

        # Informasi proses
        print(f"[*] Ukuran QR Code: {qr_width}x{qr_height}")
        if original_qr_size != (qr_width, qr_height):
            print(f"[*] QR Code diresize dari {original_qr_size[0]}x{original_qr_size[1]} ke {qr_width}x{qr_height}")
        print(f"[*] Jumlah bit QR Code: {num_qr_bits}")
        print(f"[*] Jumlah bit Header: {num_header_bits}")
        print(f"[*] Total bit untuk disisipkan: {total_bits_to_embed}")
        print(f"[*] Kapasitas citra penampung (Blue channel LSB): {max_capacity} bits")

        # 5. Siapkan data untuk disisipkan dan citra output
        data_bits_iterator = iter(header_bits + qr_bits)  # Iterator untuk bit header + QR
        stego_img = cover_img.copy()  # Salin citra asli untuk dimodifikasi
        pixels_processed = 0

        # 6. Proses penyisipan bit ke LSB channel Biru
        for y in range(cover_height):
            for x in range(cover_width):
                try:
                    # Ambil bit berikutnya dari iterator
                    bit_to_embed = next(data_bits_iterator)
                    # Dapatkan nilai RGB piksel saat ini
                    r, g, b = stego_img.getpixel((x, y))
                    # Modifikasi hanya channel Biru (b) dengan bit yang akan disisipkan
                    new_b = _embed_bit(b, bit_to_embed)
                    # Update piksel di citra stego
                    stego_img.putpixel((x, y), (r, g, new_b))
                    pixels_processed += 1
                except StopIteration:
                    # Jika iterator habis (semua bit sudah disisipkan)
                    print(f"[*] Penyisipan selesai. {pixels_processed} piksel dimodifikasi.")
                    # Simpan stego image dalam format PNG
                    stego_img.save(output_stego_path, "PNG")
                    print(f"[*] Stego image disimpan di: {output_stego_path}")
                    return  # Keluar dari fungsi setelah penyimpanan berhasil

        # Baris ini seharusnya tidak tercapai jika kapasitas cukup
        print("[!] Warning: Loop selesai tapi tidak semua bit tersisip? Cek logika kapasitas.")

    # Menangani error spesifik dan umum
    except FileNotFoundError as e:
        print(f"[!] Error: {e}")
        raise
    except ValueError as e:
        print(f"[!] Error: {e}")
        raise
    except Exception as e:
        print(f"[!] Error saat proses embedding: {e}")
        raise


def extract_qr_from_image(stego_image_path: str, output_qr_path: str):
    """
    Mengekstrak citra QR Code yang tersembunyi dari LSB channel Biru stego image.

    Args:
        stego_image_path (str): Path ke stego image (harus PNG).
        output_qr_path (str): Path untuk menyimpan citra QR hasil ekstraksi (akan dibuat PNG).

    Raises:
        FileNotFoundError: Jika file stego tidak ditemukan.
        ValueError: Jika header tidak valid, terminator tidak ditemukan, atau data tidak cukup.
        Exception: Jika terjadi error lain selama proses.
    """

    print("[*] Memulai proses extract_qr_from_image")  # Log awal fungsi

    # Validasi file input
    if not os.path.exists(stego_image_path):
        raise FileNotFoundError(f"File stego tidak ditemukan: {stego_image_path}")
    # Menyesuaikan output path jika tidak diakhiri .png
    if not output_qr_path.lower().endswith('.png'):
        print("[!] Warning: Output path disarankan .png, akan disimpan sebagai PNG.")
        output_qr_path = os.path.splitext(output_qr_path)[0] + ".png"

    try:
        # Buka stego image dalam mode RGB
        stego_img = Image.open(stego_image_path).convert('RGB')
        width, height = stego_img.size

        extracted_bits = ""  # String untuk menampung bit yang diekstrak
        pixels_processed = 0  # Counter piksel yang diproses
        header_found = False  # Flag penanda header sudah ditemukan
        qr_width = 0
        qr_height = 0
        # Total panjang header = 16 (lebar) + 16 (tinggi) + panjang terminator
        num_header_bits = 16 + 16 + HEADER_TERMINATOR_LEN

        # 1. Ekstrak Header (Dimensi QR)
        print("[*] Mengekstrak header...")
        # Iterasi piksel stego image
        for y in range(height):
            for x in range(width):
                # Dapatkan nilai RGB
                r, g, b = stego_img.getpixel((x, y))
                # Ekstrak LSB dari channel Biru
                extracted_bits += _extract_lsb(b)
                pixels_processed += 1

                # Cek apakah sudah cukup bit untuk header + terminator
                if len(extracted_bits) >= num_header_bits:
                    # Cek apakah bagian akhir bit cocok dengan terminator
                    if extracted_bits.endswith(HEADER_TERMINATOR_BIN):
                        # Ambil bagian header (sebelum terminator)
                        header_data = extracted_bits[:-HEADER_TERMINATOR_LEN]
                        # Pastikan panjangnya 32 bit (16+16)
                        if len(header_data) == 32:
                            # Konversi bit header ke integer untuk lebar dan tinggi
                            qr_width = _binary_to_int(header_data[:16])
                            qr_height = _binary_to_int(header_data[16:])
                            header_found = True
                            print(f"[*] Header ditemukan! Dimensi QR: {qr_width}x{qr_height}")
                            break  # Keluar dari loop x karena header sudah ketemu
                        else:
                            # Error jika panjang header tidak sesuai
                            raise ValueError("Panjang header tidak sesuai setelah terminator ditemukan.")
                    # Jika bit sudah banyak tapi terminator belum ketemu, mungkin error
                    elif len(extracted_bits) > num_header_bits + 500:  # Toleransi batas pencarian
                        raise ValueError("Terminator header tidak ditemukan dalam batas wajar piksel.")

            if header_found:
                break  # Keluar dari loop y jika header sudah ketemu

        # Jika setelah iterasi seluruh piksel header tidak ditemukan
        if not header_found:
            raise ValueError("Gagal menemukan header QR Code dalam citra.")

        # 2. Hitung jumlah bit QR yang perlu diekstrak berdasarkan dimensi
        num_qr_bits_expected = qr_width * qr_height
        total_bits_expected = num_header_bits + num_qr_bits_expected

        print(f"[*] Jumlah bit QR yang diharapkan: {num_qr_bits_expected}")
        print(f"[*] Total bit yang diharapkan (header + QR): {total_bits_expected}")

        # 3. Lanjutkan ekstraksi untuk data QR
        qr_bits_list = []  # List untuk menampung bit QR
        # Indeks piksel tempat ekstraksi header berhenti
        start_pixel_index = pixels_processed

        # Konversi indeks piksel linear ke koordinat (x, y) untuk melanjutkan
        start_y = start_pixel_index // width
        start_x = start_pixel_index % width

        print(f"[*] Melanjutkan ekstraksi dari piksel ({start_x}, {start_y})")

        # Buat iterator piksel yang dimulai dari piksel setelah header
        # dan berhenti setelah mengekstrak sejumlah bit yang diperlukan (num_qr_bits_expected)
        pixel_iterator = itertools.islice(
            ((x_, y_) for y_ in range(start_y, height) for x_ in range(width) if y_ > start_y or (y_ == start_y and x_ >= start_x)),
            num_qr_bits_expected
        )

        bits_extracted_count = 0  # Counter bit QR yang diekstrak
        # Iterasi menggunakan iterator piksel yang sudah dibuat
        for x, y in pixel_iterator:
            r, g, b = stego_img.getpixel((x, y))
            # Ekstrak LSB dari channel Biru dan tambahkan ke list
            qr_bits_list.append(_extract_lsb(b))
            bits_extracted_count += 1

        print(f"[*] Jumlah bit QR yang berhasil diekstrak: {bits_extracted_count}")

        # Cek apakah jumlah bit yang diekstrak sesuai harapan
        if bits_extracted_count < num_qr_bits_expected:
            raise ValueError(f"Data tidak cukup. Hanya {bits_extracted_count} dari {num_qr_bits_expected} bit QR yang bisa diekstrak.")

        # Gabungkan list bit menjadi satu string
        qr_bits = "".join(qr_bits_list)

        # 4. Rekonstruksi citra QR Code dari aliran bit
        print("[*] Merekonstruksi citra QR Code...")
        # Buat citra baru mode '1' (hitam/putih) dengan dimensi yang didapat dari header
        reconstructed_qr = Image.new('1', (qr_width, qr_height))
        bit_index = 0
        # Iterasi koordinat citra QR yang akan dibuat
        for y in range(qr_height):
            for x in range(qr_width):
                # Jika bit = '1' (representasi hitam), set piksel ke 0 (hitam di mode '1')
                if qr_bits[bit_index] == '1':
                    reconstructed_qr.putpixel((x, y), 0)
                # Jika bit = '0' (representasi putih), set piksel ke 255 (putih di mode '1')
                else:
                    reconstructed_qr.putpixel((x, y), 255)
                bit_index += 1

        # Simpan citra QR hasil rekonstruksi
        reconstructed_qr.save(output_qr_path, "PNG")
        print(f"[*] Citra QR Code hasil ekstraksi disimpan di: {output_qr_path}")

    # Menangani error spesifik dan umum
    except FileNotFoundError as e:
        print(f"[!] Error: {e}")
        raise
    except ValueError as e:
        print(f"[!] Error: {e}")
        raise
    except Exception as e:
        print(f"[!] Error saat proses extracting: {e}")
        raise

