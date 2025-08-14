# File: app.py
# Deskripsi: Aplikasi web Flask untuk watermarking dokumen .docx dengan QR Code LSB.

import os
import subprocess
import uuid
import shutil
import sys
import logging
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from PIL import Image
import numpy as np
import json
import time

from main import extract_images_from_docx, embed_watermark_to_docx
from qr_utils import read_qr

# Inisialisasi aplikasi Flask
app = Flask(__name__)

# Konfigurasi path menggunakan pathlib untuk cross-platform compatibility
BASE_DIR = Path(__file__).parent.absolute()
UPLOAD_FOLDER = BASE_DIR / 'static' / 'uploads'
GENERATED_FOLDER = BASE_DIR / 'static' / 'generated'
DOCUMENTS_FOLDER = BASE_DIR / 'public' / 'documents'
MAIN_SCRIPT_PATH = BASE_DIR / 'main.py'

# Setup logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(GENERATED_FOLDER, exist_ok=True)
os.makedirs(DOCUMENTS_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['GENERATED_FOLDER'] = str(GENERATED_FOLDER)
app.config['DOCUMENTS_FOLDER'] = str(DOCUMENTS_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Batas unggah 16MB

ALLOWED_DOCX_EXTENSIONS = {'docx', 'pdf'}
ALLOWED_IMAGE_EXTENSIONS = {'png'}


def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def get_file_size_info(file_path):
    """
    Mendapatkan informasi ukuran file dalam berbagai format.
    
    Args:
        file_path (str): Path ke file yang akan dianalisis
    
    Returns:
        dict: Informasi ukuran file dalam bytes, KB, MB
    """
    if not os.path.exists(file_path):
        return {"bytes": 0, "kb": 0, "mb": 0, "formatted": "File tidak ditemukan"}
    
    size_bytes = os.path.getsize(file_path)
    size_kb = size_bytes / 1024
    size_mb = size_bytes / (1024 * 1024)
    
    # Format yang mudah dibaca
    if size_mb >= 1:
        formatted_size = f"{size_mb:.2f} MB"
    elif size_kb >= 1:
        formatted_size = f"{size_kb:.2f} KB"
    else:
        formatted_size = f"{size_bytes} bytes"
    
    return {
        "bytes": size_bytes,
        "kb": round(size_kb, 2),
        "mb": round(size_mb, 2),
        "formatted": formatted_size
    }


def get_size_recommendation(compression_ratio):
    """
    Memberikan rekomendasi berdasarkan rasio perubahan ukuran file.
    
    Args:
        compression_ratio (float): Rasio ukuran processed/original
    
    Returns:
        dict: Rekomendasi dan status
    """
    abs_change = abs(1 - compression_ratio) * 100
    
    if abs_change < 1:
        return {
            "status": "excellent",
            "message": "Perubahan ukuran sangat minimal (<1%) - steganografi optimal!",
            "color": "success"
        }
    elif abs_change < 5:
        return {
            "status": "good", 
            "message": "Perubahan ukuran dalam batas wajar (1-5%) - steganografi berhasil.",
            "color": "success"
        }
    elif abs_change < 10:
        return {
            "status": "fair",
            "message": "Perubahan ukuran cukup signifikan (5-10%) - masih dapat diterima.",
            "color": "warning"
        }
    else:
        return {
            "status": "poor",
            "message": f"Perubahan ukuran sangat signifikan (>{abs_change:.1f}%) - perlu optimasi.",
            "color": "error"
        }

def analyze_file_size_impact(original_path, processed_path):
    """
    Analisis mendalam terhadap perubahan ukuran file dengan monitoring.
    
    Args:
        original_path (str): Path file asli
        processed_path (str): Path file hasil proses
    
    Returns:
        dict: Analisis lengkap ukuran file
    """
    try:
        original_size = os.path.getsize(original_path)
        processed_size = os.path.getsize(processed_path)
        
        # Hitung compression ratio
        compression_ratio = processed_size / original_size if original_size > 0 else 1
        
        # Warn jika perubahan terlalu besar
        if compression_ratio > 1.1:  # 10% increase
            logging.warning(f"File size increased significantly: {compression_ratio:.2f}x")
        elif compression_ratio < 0.9:  # 10% decrease  
            logging.info(f"File size decreased: {compression_ratio:.2f}x")
        
        recommendation = get_size_recommendation(compression_ratio)
        
        return {
            "original_size": original_size,
            "processed_size": processed_size,
            "size_change_ratio": compression_ratio,
            "size_change_percentage": (compression_ratio - 1) * 100,
            "recommendation": recommendation,
            "original_size_formatted": f"{original_size / 1024:.2f} KB" if original_size >= 1024 else f"{original_size} bytes",
            "processed_size_formatted": f"{processed_size / 1024:.2f} KB" if processed_size >= 1024 else f"{processed_size} bytes"
        }
    except Exception as e:
        logging.error(f"Error analyzing file size impact: {str(e)}")
        return {
            "error": str(e),
            "recommendation": {
                "status": "error",
                "message": "Tidak dapat menganalisis perubahan ukuran file",
                "color": "error"
            }
        }

def calculate_file_size_comparison(original_path, processed_path):
    """
    Membandingkan ukuran file sebelum dan sesudah proses.
    
    Args:
        original_path (str): Path file asli
        processed_path (str): Path file hasil proses
    
    Returns:
        dict: Informasi perbandingan ukuran file
    """
    original_info = get_file_size_info(original_path)
    processed_info = get_file_size_info(processed_path)
    
    if original_info["bytes"] == 0 or processed_info["bytes"] == 0:
        return {
            "original": original_info,
            "processed": processed_info,
            "difference_bytes": 0,
            "difference_percentage": 0,
            "size_change": "Tidak dapat menghitung"
        }
    
    # Hitung selisih
    difference_bytes = processed_info["bytes"] - original_info["bytes"]
    difference_percentage = (difference_bytes / original_info["bytes"]) * 100
    
    # Tentukan jenis perubahan
    if difference_bytes > 0:
        size_change = f"Bertambah {abs(difference_percentage):.2f}%"
    elif difference_bytes < 0:
        size_change = f"Berkurang {abs(difference_percentage):.2f}%"
    else:
        size_change = "Tidak berubah"
    
    # Tambahkan analisis mendalam
    detailed_analysis = analyze_file_size_impact(original_path, processed_path)
    
    return {
        "original": original_info,
        "processed": processed_info,
        "difference_bytes": difference_bytes,
        "difference_percentage": round(difference_percentage, 2),
        "size_change": size_change,
        "detailed_analysis": detailed_analysis
    }


def generate_image_url(folder, filename):
    """Generate consistent URL for images with cross-platform path handling."""
    return f"/static/generated/{folder}/{filename}".replace('\\', '/')

def safe_subprocess_run(command):
    """Cross-platform subprocess execution with proper encoding."""
    try:
        command_str = [str(item) for item in command]  # Convert Path objects to strings
        logging.info(f"[*] Menjalankan perintah: {' '.join(command_str)}")
        
        if sys.platform == 'win32':
            # Windows-specific configuration
            result = subprocess.run(
                command_str, 
                capture_output=True, 
                text=True, 
                check=True,
                encoding='cp1252',
                shell=False
            )
        else:
            # Unix/Linux configuration
            result = subprocess.run(
                command_str, 
                capture_output=True, 
                text=True, 
                check=True, 
                encoding='utf-8'
            )
        
        logging.info(f"[*] Stdout: {result.stdout}")
        if result.stderr:
            logging.warning(f"[*] Stderr: {result.stderr}")
        return {"success": True, "stdout": result.stdout, "stderr": result.stderr}
        
    except subprocess.CalledProcessError as e:
        logging.error(f"[!] Error saat menjalankan skrip: {e}")
        logging.error(f"    Stdout: {e.stdout}")
        logging.error(f"    Stderr: {e.stderr}")
        return {"success": False, "stdout": e.stdout, "stderr": e.stderr, "error": str(e)}
    except FileNotFoundError as e:
        error_msg = f"[!] Error: File tidak ditemukan: {str(e)}"
        logging.error(error_msg)
        return {"success": False, "stdout": "", "stderr": error_msg, "error": error_msg}
    except Exception as e:
        error_msg = f"[!] Exception saat menjalankan skrip: {str(e)}"
        logging.error(error_msg)
        return {"success": False, "stdout": "", "stderr": error_msg, "error": error_msg}

def run_main_script(args):
    """Menjalankan skrip main.py dan menangkap output."""
    command = ['python', MAIN_SCRIPT_PATH] + args
    return safe_subprocess_run(command)


def calculate_metrics(original_docx_path, stego_docx_path):
    """Menghitung MSE dan PSNR antara gambar-gambar dalam dua file .docx."""

    try:
        # Ekstrak gambar dari kedua dokumen
        original_images_dir = os.path.join(app.config['GENERATED_FOLDER'], "original_images")
        stego_images_dir = os.path.join(app.config['GENERATED_FOLDER'], "stego_images")
        os.makedirs(original_images_dir, exist_ok=True)
        os.makedirs(stego_images_dir, exist_ok=True)

        original_images = extract_images_from_docx(original_docx_path, original_images_dir)
        stego_images = extract_images_from_docx(stego_docx_path, stego_images_dir)

        if not original_images or not stego_images:
            print("[!] Tidak dapat membandingkan gambar: Gagal mengekstrak gambar dari dokumen.")
            return {"mse": None, "psnr": None, "error": "Gagal mengekstrak gambar dari dokumen."}

        if len(original_images) != len(stego_images):
            print("[!] Tidak dapat membandingkan gambar: Jumlah gambar tidak sama.")
            return {"mse": None, "psnr": None, "error": "Jumlah gambar tidak sama."}

        total_mse = 0
        all_psnr_values = []

        for original_image_path, stego_image_path in zip(original_images, stego_images):
            try:
                original_image = Image.open(original_image_path).convert('RGB')
                stego_image = Image.open(stego_image_path).convert('RGB')

                if original_image.size != stego_image.size:
                    print(f"[!] Ukuran gambar tidak sama: {original_image_path} vs {stego_image_path}")
                    continue  # Lewati pasangan gambar ini

                original_array = np.array(original_image, dtype=np.float64)
                watermarked_array = np.array(stego_image, dtype=np.float64)

                mse = np.mean((original_array - watermarked_array) ** 2)
                total_mse += mse

                if mse == 0:
                    psnr = float('inf')
                else:
                    max_pixel = 255.0
                    psnr = 20 * np.log10(max_pixel / np.sqrt(mse))
                all_psnr_values.append(psnr)

            except Exception as e:
                print(f"[!] Error memproses pasangan gambar: {e}")

        final_mse = total_mse / len(original_images) if original_images else 0
        # Rata-rata PSNR (hindari ZeroDivisionError jika daftar kosong)
        final_psnr = sum(all_psnr_values) / len(all_psnr_values) if all_psnr_values else 0

        # Convert infinite values to string for JSON serialization
        if final_psnr == float('inf'):
            final_psnr = "Infinity"
        elif final_psnr == float('-inf'):
            final_psnr = "-Infinity"

        # Bersihkan direktori sementara
        if os.path.exists(original_images_dir):
            shutil.rmtree(original_images_dir)
        if os.path.exists(stego_images_dir):
            shutil.rmtree(stego_images_dir)

        return {"mse": final_mse, "psnr": final_psnr}

    except Exception as e:
        print(f"[!] Error keseluruhan dalam calculate_metrics: {e}")
        return {"mse": None, "psnr": None, "error": str(e)}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generate_qr', methods=['POST'])
def generate_qr_route():
    data = request.form.get('qrData')
    use_crc32 = request.form.get('useCrc32') == 'true'
    
    if not data:
        return jsonify({"success": False, "message": "Data QR tidak boleh kosong."}), 400

    qr_filename = f"qr_{uuid.uuid4().hex}.png"
    qr_output_path = os.path.join(app.config['GENERATED_FOLDER'], qr_filename)

    try:
        if use_crc32:
            # Import fungsi CRC32
            from qr_utils import add_crc32_checksum
            
            # Tambahkan CRC32 checksum
            data_with_checksum = add_crc32_checksum(data)
            
            # Konversi ke JSON
            qr_data_final = json.dumps(data_with_checksum, separators=(',', ':'))
            
            message = "QR Code berhasil dibuat dengan CRC32 checksum!"
            
            crc32_info = {
                "checksum": data_with_checksum.get('crc32'),
                "full_checksum": data_with_checksum.get('full_checksum'),
                "data_length": len(data),
                "integrity_protected": True
            }
        else:
            # Gunakan data asli tanpa CRC32
            qr_data_final = data
            message = "QR Code berhasil dibuat!"
            
            crc32_info = {
                "checksum": None,
                "data_length": len(data),
                "integrity_protected": False
            }
        
        # Generate QR Code
        args = ['generate_qr', '--data', qr_data_final, '--output', qr_output_path]
        result = run_main_script(args)

        if result["success"] and os.path.exists(qr_output_path):
            return jsonify({
                "success": True,
                "message": message,
                "qr_url": f"/static/generated/{qr_filename}",
                "qr_filename": qr_filename,
                "log": result["stdout"],
                "crc32_enabled": use_crc32,
                "crc32_info": crc32_info
            })
        else:
            return jsonify({
                "success": False,
                "message": "Gagal membuat QR Code.",
                "log": result["stderr"] or result.get("error", "Error tidak diketahui")
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error dalam pembuatan QR Code: {str(e)}"
        }), 500


@app.route('/embed_docx', methods=['POST'])
def embed_docx_route():
    if 'docxFileEmbed' not in request.files or 'qrFileEmbed' not in request.files:
        error_msg = "File Dokumen dan File QR Code diperlukan."
        print(f"[ERROR] /embed_docx: {error_msg}")
        print(f"[ERROR] Missing fields: docxFileEmbed in files: {'docxFileEmbed' in request.files}, qrFileEmbed in files: {'qrFileEmbed' in request.files}")
        return jsonify({"success": False, "message": error_msg}), 400

    docx_file = request.files['docxFileEmbed']
    qr_file = request.files['qrFileEmbed']

    if docx_file.filename == '' or qr_file.filename == '':
        error_msg = "Nama file tidak boleh kosong."
        print(f"[ERROR] /embed_docx: {error_msg}")
        print(f"[ERROR] Filenames: docx={docx_file.filename}, qr={qr_file.filename}")
        return jsonify({"success": False, "message": error_msg}), 400

    if not (docx_file and allowed_file(docx_file.filename, ALLOWED_DOCX_EXTENSIONS)):
        error_msg = "Format Dokumen harus .docx atau .pdf"
        print(f"[ERROR] /embed_docx: {error_msg}")
        return jsonify({"success": False, "message": error_msg}), 400
    if not (qr_file and allowed_file(qr_file.filename, ALLOWED_IMAGE_EXTENSIONS)):
        error_msg = "Format QR Code harus .png"
        print(f"[ERROR] /embed_docx: {error_msg}")
        return jsonify({"success": False, "message": error_msg}), 400

    docx_filename = f"doc_embed_in_{uuid.uuid4().hex}.docx"
    qr_embed_filename = f"qr_embed_in_{uuid.uuid4().hex}.png"
    docx_temp_path = os.path.join(app.config['UPLOAD_FOLDER'], docx_filename)
    qr_temp_path = os.path.join(app.config['UPLOAD_FOLDER'], qr_embed_filename)
    docx_file.save(docx_temp_path)
    qr_file.save(qr_temp_path)

    # Simpan ukuran file asli sebelum diproses
    original_file_size = get_file_size_info(docx_temp_path)

    file_extension = docx_file.filename.rsplit('.', 1)[1].lower()
    stego_docx_filename = f"stego_doc_{uuid.uuid4().hex}.{file_extension}"
    stego_docx_output_path = os.path.join(app.config['GENERATED_FOLDER'], stego_docx_filename)
    
    # Juga siapkan path untuk dokumen hasil di folder documents
    documents_filename = f"watermarked_{uuid.uuid4().hex}.{file_extension}"
    documents_output_path = os.path.join(app.config['DOCUMENTS_FOLDER'], documents_filename)
    
    # Cek apakah file adalah PDF
    is_pdf = file_extension == 'pdf'
    
    if is_pdf:
        # Proses PDF menggunakan ekstraksi gambar asli (bukan render halaman)
        try:
            from pdf_utils import embed_watermark_to_pdf_real_images
            print("[*] Memulai proses embed watermark ke gambar asli di dalam PDF")
            
            # Generate temporary directories untuk PDF processing
            pdf_work_dir = os.path.join(app.config['GENERATED_FOLDER'], f"pdf_work_{uuid.uuid4().hex}")
            os.makedirs(pdf_work_dir, exist_ok=True)
            
            # Extract dan proses gambar asli dari PDF
            try:
                pdf_result = embed_watermark_to_pdf_real_images(docx_temp_path, qr_temp_path, pdf_work_dir)
                
                if pdf_result.get("success"):
                    result = {"success": True, "stdout": "PDF watermarking gambar asli berhasil", "stderr": ""}
                    process_result = pdf_result
                    
                    # Untuk PDF dengan gambar asli, tidak perlu reconstruct PDF utuh
                    # Cukup simpan hasil watermarked images sebagai ZIP atau individual files
                    # Buat symbolic link atau copy ke output path untuk konsistensi
                    try:
                        import shutil
                        # Gunakan PDF watermarked yang sudah dibuat
                        watermarked_pdf_path = pdf_result.get("watermarked_pdf_path")
                        if watermarked_pdf_path and os.path.exists(watermarked_pdf_path):
                            # Copy PDF watermarked ke lokasi output yang diharapkan
                            shutil.copy2(watermarked_pdf_path, stego_docx_output_path)
                            print(f"[*] PDF watermarked berhasil disalin ke: {stego_docx_output_path}")
                        else:
                            # Fallback: buat file placeholder jika PDF tidak berhasil dibuat
                            processed_images = pdf_result.get("processed_images", [])
                            with open(stego_docx_output_path, 'w') as f:
                                f.write(f"PDF berhasil diproses dengan {len(processed_images)} gambar watermarked.\n")
                                f.write("Lihat hasil di folder watermarked_images.")
                            print("[!] Warning: Menggunakan file placeholder karena PDF watermarked tidak tersedia")
                    except Exception as e:
                        print(f"[!] Warning: {e}")
                else:
                    result = {"success": False, "stdout": "", "stderr": pdf_result.get("message", "PDF watermarking gagal")}
                    process_result = None
                    
            except ValueError as ve:
                if str(ve) == "NO_IMAGES_FOUND":
                    result = {"success": False, "stdout": "", "stderr": "Tidak ada gambar ditemukan di dalam PDF"}
                    process_result = None
                else:
                    result = {"success": False, "stdout": "", "stderr": str(ve)}
                    process_result = None
            except Exception as e:
                result = {"success": False, "stdout": "", "stderr": f"Error: {str(e)}"}
                process_result = None
                
        except ImportError as e:
            print(f"[ERROR] Failed to import PDF utils: {e}")
            result = {"success": False, "stdout": "", "stderr": f"Error loading PDF processing: {str(e)}"}
            process_result = None
        
    else:
        # Proses DOCX seperti biasa
        args = ['embed_docx', '--docx', docx_temp_path, '--qr', qr_temp_path, '--output', stego_docx_output_path]
        print("[*] Memulai proses embed_docx")
        result = run_main_script(args)
        process_result = None

    if result["success"]:
        print("[*] Proses embed_docx berhasil")
        
        # Get processed images info
        if is_pdf and process_result:
            # Untuk PDF, ambil informasi gambar dari process_result
            processed_images = process_result.get("processed_images", [])
            qr_image_url = process_result.get("qr_image", "")
            public_dir = process_result.get("public_dir", "")
            qr_info = process_result.get("qr_info", None)
            pdf_info = process_result.get("pdf_info", {})
            print(f"[*] PDF berhasil diproses: {len(processed_images)} halaman")
        elif not is_pdf:
            # Run the embed_watermark_to_docx function directly to get the processed images for DOCX
            try:
                print("[*] Mendapatkan informasi gambar yang diproses")
                process_result = embed_watermark_to_docx(docx_temp_path, qr_temp_path, stego_docx_output_path)
                
                # Get processed images info if available
                processed_images = []
                qr_image_url = ""
                public_dir = ""
                qr_info = None
                pdf_info = None
                
                if isinstance(process_result, dict) and process_result.get("success"):
                    processed_images = process_result.get("processed_images", [])
                    qr_image_url = process_result.get("qr_image", "")
                    public_dir = process_result.get("public_dir", "")
                    qr_info = process_result.get("qr_info", None)
                    print(f"[*] Mendapatkan {len(processed_images)} gambar yang diproses")
                else:
                    print("[!] Tidak mendapatkan detail gambar yang diproses")
            except ValueError as ve:
                if str(ve) == "NO_IMAGES_FOUND":
                    # Handle no images case
                    return jsonify({
                        "success": False,
                        "message": "Dokumen ini tidak mengandung gambar",
                        "log": result["stderr"],
                        "error_type": "NO_IMAGES_FOUND"
                    }), 400
                print(f"[!] Error saat mendapatkan informasi gambar: {str(ve)}")
                processed_images = []
                qr_image_url = ""
                public_dir = ""
                qr_info = None
                pdf_info = None
            except Exception as e:
                print(f"[!] Error saat mendapatkan informasi gambar: {str(e)}")
                processed_images = []
                qr_image_url = ""
                public_dir = ""
                qr_info = None
                pdf_info = None
        else:
            # PDF processing failed or process_result is None
            processed_images = []
            qr_image_url = ""
            public_dir = ""
            qr_info = None
            pdf_info = {}
            
            # Initialize analysis variables when processing fails
            from qr_utils import get_detailed_pixel_info
            qr_analysis = get_detailed_pixel_info(qr_temp_path)
            image_analyses = []
            detailed_metrics = []
        
        # Hitung MSE dan PSNR
        if not is_pdf:
            metrics = calculate_metrics(docx_temp_path, stego_docx_output_path)
            print(f"[*] Metrik MSE: {metrics['mse']}, PSNR: {metrics['psnr']}")
        else:
            # Untuk PDF, gunakan rata-rata dari semua gambar
            metrics = {"mse": 0, "psnr": 0}
            if process_result and "analysis" in process_result and "image_analyses" in process_result["analysis"]:
                image_metrics = [p["metrics"] for p in process_result["analysis"]["image_analyses"] if p.get("metrics") and p["metrics"].get("success")]
                if image_metrics:
                    avg_mse = sum(m["mse"] for m in image_metrics) / len(image_metrics)
                    finite_psnr_values = [m["psnr"] for m in image_metrics if m["psnr"] != float('inf') and m["psnr"] != float('-inf')]
                    if finite_psnr_values:
                        avg_psnr = sum(finite_psnr_values) / len(finite_psnr_values)
                    else:
                        avg_psnr = "Infinity"  # JSON-safe infinity representation
                    
                    # Ensure JSON-safe values
                    if avg_psnr == float('inf'):
                        avg_psnr = "Infinity"
                    elif avg_psnr == float('-inf'):
                        avg_psnr = "-Infinity"
                    
                    metrics = {"mse": avg_mse, "psnr": avg_psnr}
                    print(f"[*] Metrik rata-rata PDF - MSE: {avg_mse}, PSNR: {avg_psnr}")
                else:
                    print("[!] Tidak ada metrics valid ditemukan untuk PDF")
        
        # Analisis pixel gambar QR dengan detail
        from qr_utils import calculate_mse_psnr, get_detailed_pixel_info
        
        if is_pdf and process_result and "analysis" in process_result:
            # Untuk PDF, gunakan analisis QR dari hasil PDF processing
            qr_analysis = process_result["analysis"].get("qr_analysis", {})
            print(f"[*] Analisis QR Code (PDF): {qr_analysis.get('success', False)}")
            
            # Gunakan analisis yang sudah ada dari PDF processing
            image_analyses = []
            detailed_metrics = []
            
            # Konversi format analisis PDF ke format yang diharapkan frontend
            for image_analysis in process_result["analysis"].get("image_analyses", []):
                image_index = image_analysis.get("image_index", 0) - 1  # Convert to 0-based index
                image_analyses.append({
                    "image_index": image_index,
                    "original": image_analysis.get("original", {}),
                    "watermarked": image_analysis.get("watermarked", {})
                })
                
                detailed_metrics.append({
                    "image_index": image_index,
                    "metrics": image_analysis.get("metrics", {})
                })
        else:
            qr_analysis = get_detailed_pixel_info(qr_temp_path)
            print(f"[*] Analisis QR Code: {qr_analysis.get('success', False)}")
            
            # Analisis gambar yang diproses (jika ada)
            image_analyses = []
            detailed_metrics = []
            if processed_images:
                for i, img_info in enumerate(processed_images):  # Analisis semua gambar
                    if "original_path" in img_info and "watermarked_path" in img_info:
                        # Analisis pixel gambar asli dengan detail
                        original_analysis = get_detailed_pixel_info(img_info["original_path"])
                        
                        # Analisis pixel gambar watermarked dengan detail
                        watermarked_analysis = get_detailed_pixel_info(img_info["watermarked_path"])
                        
                        # MSE/PSNR detail per gambar
                        img_metrics = calculate_mse_psnr(img_info["original_path"], img_info["watermarked_path"])
                        
                        image_analyses.append({
                            "image_index": i,
                            "original": original_analysis,
                            "watermarked": watermarked_analysis
                        })
                        
                        detailed_metrics.append({
                            "image_index": i,
                            "metrics": img_metrics
                        })
                        
                        # Add pixel analysis data and metrics to processed_images for display
                        if i < len(processed_images):
                            processed_images[i]["pixel_analysis"] = {
                                "original": original_analysis,
                                "watermarked": watermarked_analysis
                            }
                            processed_images[i]["individual_metrics"] = img_metrics
        
        print(f"[*] Selesai analisis {len(image_analyses)} {'halaman' if is_pdf else 'gambar'}")

        # Salin dokumen hasil ke folder documents untuk akses permanen
        try:
            shutil.copy2(stego_docx_output_path, documents_output_path)
            print(f"[*] Dokumen hasil disalin ke: {documents_output_path}")
        except Exception as e:
            print(f"[!] Warning: Gagal menyalin dokumen ke folder documents: {str(e)}")

        # Baca data QR code untuk ditampilkan
        qr_data = None
        try:
            qr_data_list = read_qr(qr_temp_path)
            if qr_data_list:
                qr_data = qr_data_list[0]  # Ambil data QR pertama
                print(f"[*] Data QR Code: {qr_data}")
        except Exception as e:
            print(f"[!] Warning: Tidak dapat membaca data QR Code: {str(e)}")

        # Hitung perbandingan ukuran file
        if is_pdf and process_result and process_result.get("file_size_info"):
            # Untuk PDF, gunakan informasi ukuran file dari PDF processing
            pdf_file_size_info = process_result.get("file_size_info")
            file_size_info = {
                "original": {
                    "bytes": pdf_file_size_info["original_size"],
                    "kb": pdf_file_size_info["original_size_kb"],
                    "mb": pdf_file_size_info["original_size_mb"],
                    "formatted": f"{pdf_file_size_info['original_size_kb']:.2f} KB" if pdf_file_size_info['original_size_kb'] >= 1 else f"{pdf_file_size_info['original_size']} bytes"
                },
                "processed": {
                    "bytes": pdf_file_size_info["watermarked_size"],
                    "kb": pdf_file_size_info["watermarked_size_kb"],
                    "mb": pdf_file_size_info["watermarked_size_mb"],
                    "formatted": f"{pdf_file_size_info['watermarked_size_kb']:.2f} KB" if pdf_file_size_info['watermarked_size_kb'] >= 1 else f"{pdf_file_size_info['watermarked_size']} bytes"
                },
                "difference_bytes": pdf_file_size_info["size_difference"],
                "difference_percentage": round(pdf_file_size_info["size_change_percentage"], 2),
                "size_change": f"Bertambah {abs(pdf_file_size_info['size_change_percentage']):.2f}%" if pdf_file_size_info["size_difference"] > 0 else f"Berkurang {abs(pdf_file_size_info['size_change_percentage']):.2f}%" if pdf_file_size_info["size_difference"] < 0 else "Tidak berubah"
            }
            print(f"[*] PDF File size comparison: {file_size_info['original']['formatted']} -> {file_size_info['processed']['formatted']} ({file_size_info['size_change']})")
        else:
            # Untuk DOCX atau jika PDF info tidak tersedia, gunakan perhitungan standar
            processed_size_info = get_file_size_info(stego_docx_output_path)
            
            # Hitung selisih
            size_difference = processed_size_info["bytes"] - original_file_size["bytes"]
            size_change_percentage = (size_difference / original_file_size["bytes"]) * 100 if original_file_size["bytes"] > 0 else 0
            
            # Format perubahan
            if size_difference > 0:
                size_change_text = f"Bertambah {abs(size_change_percentage):.2f}%"
            elif size_difference < 0:
                size_change_text = f"Berkurang {abs(size_change_percentage):.2f}%"
            else:
                size_change_text = "Tidak berubah"

            file_size_info = {
                "original": original_file_size,
                "processed": processed_size_info,
                "difference_bytes": size_difference,
                "difference_percentage": round(size_change_percentage, 2),
                "size_change": size_change_text
            }

        # Hapus file temporary setelah perhitungan metrik
        if os.path.exists(docx_temp_path):
            os.remove(docx_temp_path)
        if os.path.exists(qr_temp_path):
            os.remove(qr_temp_path)

        # Hitung informasi ukuran file
        original_size_info = {
            "bytes": docx_file.content_length or 0,
            "kb": round((docx_file.content_length or 0) / 1024, 2),
            "mb": round((docx_file.content_length or 0) / (1024 * 1024), 2),
            "formatted": f"{(docx_file.content_length or 0) / 1024:.2f} KB" if (docx_file.content_length or 0) >= 1024 else f"{docx_file.content_length or 0} bytes"
        }
        
        # Informasi file hasil
        processed_size_info = get_file_size_info(stego_docx_output_path)
        
        # Hitung perbandingan ukuran file
        original_bytes = original_size_info["bytes"]
        processed_bytes = processed_size_info["bytes"]
        difference_bytes = processed_bytes - original_bytes
        
        if original_bytes > 0:
            difference_percentage = (difference_bytes / original_bytes) * 100
        else:
            difference_percentage = 0
            
        # Tentukan jenis perubahan
        if difference_bytes > 0:
            change_type = "increase"
            change_text = f"+{abs(difference_bytes)} bytes (+{abs(difference_percentage):.2f}%)"
        elif difference_bytes < 0:
            change_type = "decrease"
            change_text = f"-{abs(difference_bytes)} bytes (-{abs(difference_percentage):.2f}%)"
        else:
            change_type = "no-change"
            change_text = "Tidak ada perubahan ukuran"
        
        # Quality assessment berdasarkan persentase perubahan
        if abs(difference_percentage) < 1:
            quality = "Excellent"
            quality_color = "success"
        elif abs(difference_percentage) < 5:
            quality = "Good"
            quality_color = "success"
        elif abs(difference_percentage) < 10:
            quality = "Fair"
            quality_color = "warning"
        else:
            quality = "Poor"
            quality_color = "error"
            
        file_size_comparison = {
            "original": original_size_info,
            "processed": processed_size_info,
            "difference_bytes": difference_bytes,
            "difference_percentage": round(difference_percentage, 2),
            "change_type": change_type,
            "change_text": change_text,
            "quality": quality,
            "quality_color": quality_color
        }
        
        # Hitung selisih
        size_difference = processed_size_info["bytes"] - original_size_info["bytes"]
        size_change_percentage = (size_difference / original_size_info["bytes"]) * 100 if original_size_info["bytes"] > 0 else 0
        
        # Format perubahan
        if size_difference > 0:
            size_change_text = f"Bertambah {abs(size_change_percentage):.2f}%"
        elif size_difference < 0:
            size_change_text = f"Berkurang {abs(size_change_percentage):.2f}%"
        else:
            size_change_text = "Tidak berubah"

        file_size_info = {
            "original": original_size_info,
            "processed": processed_size_info,
            "difference_bytes": size_difference,
            "difference_percentage": round(size_change_percentage, 2),
            "size_change": size_change_text
        }

        response_data = {
            "success": True,
            "message": f"Watermark berhasil disisipkan ke {'PDF' if is_pdf else 'dokumen'}!",
            "download_url": f"/download_generated/{stego_docx_filename}",
            "documents_url": f"/download_documents/{documents_filename}",
            "documents_filename": documents_filename,
            "log": result["stdout"],
            "mse": metrics["mse"],
            "psnr": metrics["psnr"],
            "processed_images": processed_images,
            "qr_image": qr_image_url,
            "public_dir": public_dir,
            "qr_info": qr_info,
            "qr_data": qr_data,
            "analysis": {
                "qr_analysis": qr_analysis,
                "image_analyses": image_analyses,
                "detailed_metrics": detailed_metrics
            },
            "file_type": "pdf" if is_pdf else "docx",
            "original_filename": docx_file.filename,
            "file_size_info": file_size_info
        }
        
        # Tambahkan informasi ukuran file jika tersedia dari process_result
        if process_result and "file_size_info" in process_result:
            response_data["file_size_info"] = process_result["file_size_info"]
        
        # Tambahkan informasi PDF jika relevan
        if is_pdf and 'pdf_info' in locals():
            response_data["pdf_info"] = pdf_info
            response_data["total_pages"] = pdf_info.get("pages", 0)
            response_data["processed_pages"] = len(processed_images)
            
        return jsonify(response_data)
    else:
        # Hapus file temporary jika terjadi error
        if os.path.exists(docx_temp_path):
            os.remove(docx_temp_path)
        if os.path.exists(qr_temp_path):
            os.remove(qr_temp_path)

        # Check for the specific "NO_IMAGES_FOUND" error
        if result["stderr"] and "NO_IMAGES_FOUND" in result["stderr"]:
            return jsonify({
                "success": False,
                "message": "Dokumen ini tidak mengandung gambar",
                "log": result["stderr"],
                "error_type": "NO_IMAGES_FOUND"
            }), 400
        
        return jsonify({
            "success": False,
            "message": "Gagal menyisipkan watermark.",
            "log": result["stderr"] or result.get("error", "Error tidak diketahui")
        }), 500


@app.route('/extract_docx', methods=['POST'])
def extract_docx_route():
    if 'docxFileValidate' not in request.files:
        return jsonify({"success": False, "message": "File Dokumen diperlukan untuk validasi."}), 400

    docx_file = request.files['docxFileValidate']

    if docx_file.filename == '':
        return jsonify({"success": False, "message": "Nama file tidak boleh kosong."}), 400
    if not (docx_file and allowed_file(docx_file.filename, ALLOWED_DOCX_EXTENSIONS)):
        return jsonify({"success": False, "message": "Format Dokumen harus .docx atau .pdf"}), 400

    file_extension = docx_file.filename.rsplit('.', 1)[1].lower()
    docx_validate_filename = f"doc_extract_in_{uuid.uuid4().hex}.{file_extension}"
    docx_temp_path = os.path.join(app.config['UPLOAD_FOLDER'], docx_validate_filename)
    docx_file.save(docx_temp_path)

    # Simpan ukuran file untuk informasi
    original_file_size = get_file_size_info(docx_temp_path)

    extraction_id = uuid.uuid4().hex
    output_extraction_dir_name = f"extraction_{extraction_id}"
    output_extraction_dir_path = os.path.join(app.config['GENERATED_FOLDER'], output_extraction_dir_name)

    # Cek apakah file adalah PDF
    is_pdf = file_extension == 'pdf'
    
    if is_pdf:
        # Proses PDF menggunakan ekstraksi gambar asli (bukan render halaman)
        from pdf_utils import extract_watermark_from_pdf_real_images
        print("[*] Memulai proses extract watermark dari gambar asli di dalam PDF")
        
        try:
            pdf_result = extract_watermark_from_pdf_real_images(docx_temp_path, output_extraction_dir_path)
            
            if pdf_result.get("success"):
                result = {"success": True, "stdout": "PDF extraction gambar asli berhasil", "stderr": ""}
                extracted_qrs_info = pdf_result.get("extracted_qrs", [])
            else:
                result = {"success": False, "stdout": "", "stderr": pdf_result.get("message", "PDF extraction gagal")}
                extracted_qrs_info = []
                
        except ValueError as ve:
            if str(ve) == "NO_IMAGES_FOUND":
                result = {"success": False, "stdout": "", "stderr": "Tidak ada gambar ditemukan di dalam PDF"}
                extracted_qrs_info = []
            else:
                result = {"success": False, "stdout": "", "stderr": str(ve)}
                extracted_qrs_info = []
        except Exception as e:
            result = {"success": False, "stdout": "", "stderr": f"Error: {str(e)}"}
            extracted_qrs_info = []
    else:
        # Proses DOCX seperti biasa
        args = ['extract_docx', '--docx', docx_temp_path, '--output_dir', output_extraction_dir_path]
        print("[*] Memulai proses extract_docx")
        result = run_main_script(args)
        extracted_qrs_info = []

    if result["success"]:
        if not is_pdf:
            # Untuk DOCX, scan direktori output
            extracted_qrs_info = []
            if os.path.exists(output_extraction_dir_path) and os.path.isdir(output_extraction_dir_path):
                for filename in os.listdir(output_extraction_dir_path):
                    if filename.lower().endswith('.png'):
                        extracted_qrs_info.append({
                            "filename": filename,
                            "url": f"/static/generated/{output_extraction_dir_name}/{filename}"
                        })
        # Untuk PDF, extracted_qrs_info sudah diset dari pdf_result

        if not extracted_qrs_info and "Tidak ada gambar yang ditemukan" not in result["stdout"]:
            pass

        # Hapus file temporary setelah selesai
        if os.path.exists(docx_temp_path):
            os.remove(docx_temp_path)

        print(f"[*] Proses extract {'PDF' if is_pdf else 'DOCX'} berhasil")
        response_data = {
            "success": True,
            "message": f"Proses ekstraksi {'PDF' if is_pdf else 'dokumen'} selesai.",
            "extracted_qrs": extracted_qrs_info,
            "log": result["stdout"],
            "file_type": "pdf" if is_pdf else "docx",
            "original_file_size": original_file_size
        }
        
        # Tambahkan informasi PDF jika relevan
        if is_pdf and 'pdf_result' in locals():
            response_data["pdf_info"] = pdf_result.get("pdf_info", {})
            response_data["total_pages"] = pdf_result.get("total_pages", 0)
            response_data["qr_found"] = pdf_result.get("qr_found", 0)
            
        return jsonify(response_data)
    else:
        # Hapus file temporary jika terjadi error
        if os.path.exists(docx_temp_path):
            os.remove(docx_temp_path)

        # Check for the specific "NO_IMAGES_FOUND" error
        if result["stderr"] and "NO_IMAGES_FOUND" in result["stderr"]:
            return jsonify({
                "success": False,
                "message": "Dokumen ini tidak mengandung gambar",
                "log": result["stderr"],
                "error_type": "NO_IMAGES_FOUND"
            }), 400

        print("[!] Proses extract_docx gagal")
        return jsonify({
            "success": False,
            "message": "Gagal mengekstrak watermark.",
            "log": result["stderr"] or result.get("error", "Error tidak diketahui")
        }), 500


@app.route('/validate_qr_integrity', methods=['POST'])
def validate_qr_integrity():
    """Validasi integritas QR Code menggunakan CRC32"""
    if 'qrFile' not in request.files:
        return jsonify({"success": False, "message": "File QR Code diperlukan"}), 400
    
    qr_file = request.files['qrFile']
    if qr_file.filename == '':
        return jsonify({"success": False, "message": "Nama file tidak boleh kosong"}), 400
    
    # Simpan file sementara
    temp_filename = f"validate_qr_{uuid.uuid4().hex}.png"
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
    qr_file.save(temp_path)
    
    try:
        # Baca QR Code
        qr_data_list = read_qr(temp_path)
        
        if not qr_data_list:
            return jsonify({
                "success": False,
                "message": "Tidak dapat membaca QR Code"
            }), 400
        
        qr_data_raw = qr_data_list[0]
        
        # Parse JSON data
        try:
            qr_data_parsed = json.loads(qr_data_raw)
        except json.JSONDecodeError:
            # QR Code lama tanpa struktur JSON
            return jsonify({
                "success": True,
                "integrity_check": False,
                "message": "QR Code format lama (tanpa CRC32 checksum)",
                "data": qr_data_raw
            })
        
        # Import fungsi verifikasi
        from qr_utils import verify_crc32_checksum
        
        # Verifikasi integritas CRC32
        validation_result = verify_crc32_checksum(qr_data_parsed)
        
        # Format timestamp yang user-friendly
        timestamp_formatted = None
        
        if validation_result.get("timestamp"):
            timestamp_formatted = time.strftime("%Y-%m-%d %H:%M:%S", 
                                              time.localtime(validation_result["timestamp"]))
        
        # Buat pesan status yang informatif
        if validation_result.get("data_valid"):
            main_message = "Data valid"
        else:
            main_message = "Data rusak/dimodifikasi"
        
        response_data = {
            "success": True,
            "integrity_check": True,
            "data_valid": validation_result.get("data_valid", False),
            "overall_valid": validation_result.get("valid", False),
            "message": main_message,
            "data": qr_data_parsed.get("data", ""),
            "crc32_info": {
                "stored_checksum": qr_data_parsed.get("crc32"),
                "full_checksum": qr_data_parsed.get("full_checksum"),
                "timestamp": timestamp_formatted,
                "status": "VALID" if validation_result.get("data_valid") else "INVALID"
            }
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error validasi: {str(e)}"
        }), 500
        
    finally:
        # Hapus file sementara
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.route('/download_generated/<filename>')
def download_generated(filename):
    """Endpoint untuk mengunduh file dari folder generated."""
    return send_from_directory(app.config['GENERATED_FOLDER'], filename, as_attachment=True)


@app.route('/static/generated/<path:filepath>')
def serve_generated_static(filepath):
    """Endpoint untuk melayani file static dari subdirektori generated."""
    try:
        # Normalize path untuk cross-platform compatibility
        safe_filepath = filepath.replace('\\', '/')
        full_path = os.path.join(app.config['GENERATED_FOLDER'], safe_filepath)
        
        if not os.path.exists(full_path):
            # Enhanced debugging for 404 errors
            parent_dir = os.path.dirname(full_path)
            print(f"[DEBUG] File not found: {full_path}")
            print(f"[DEBUG] Parent directory exists: {os.path.exists(parent_dir)}")
            if os.path.exists(parent_dir):
                try:
                    files_in_dir = os.listdir(parent_dir)
                    print(f"[DEBUG] Files in parent directory: {files_in_dir[:5]}")  # Show first 5 files
                except Exception as e:
                    print(f"[DEBUG] Cannot list parent directory: {e}")
            
            logging.error(f"File tidak ditemukan: {full_path}")
            return jsonify({"error": "File not found", "path": filepath, "full_path": full_path}), 404
            
        return send_from_directory(app.config['GENERATED_FOLDER'], safe_filepath)
    except Exception as e:
        logging.error(f"Error serving static file {filepath}: {str(e)}")
        return jsonify({"error": "Server error", "message": str(e)}), 500

@app.errorhandler(404)
def handle_404(e):
    """Handle 404 errors, especially for static files."""
    if request.path.startswith('/static/'):
        logging.warning(f"Static file not found: {request.path}")
        return jsonify({
            "error": "File not found", 
            "path": request.path,
            "message": "The requested static file could not be found"
        }), 404
    return str(e), 404


@app.route('/download_documents/<filename>')
def download_documents(filename):
    """Endpoint untuk mengunduh file dari folder documents."""
    return send_from_directory(app.config['DOCUMENTS_FOLDER'], filename, as_attachment=True)


@app.route('/list_documents')
def list_documents():
    """Endpoint untuk melihat daftar dokumen yang tersimpan."""
    try:
        documents = []
        for filename in os.listdir(app.config['DOCUMENTS_FOLDER']):
            if filename.endswith('.docx'):
                file_path = os.path.join(app.config['DOCUMENTS_FOLDER'], filename)
                file_stat = os.stat(file_path)
                documents.append({
                    'filename': filename,
                    'size': file_stat.st_size,
                    'created': file_stat.st_ctime,
                    'download_url': f'/download_documents/{filename}'
                })
        
        # Urutkan berdasarkan waktu pembuatan (terbaru dulu)
        documents.sort(key=lambda x: x['created'], reverse=True)
        
        return jsonify({
            'success': True,
            'documents': documents,
            'count': len(documents)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/process_details')
def process_details():
    """Render the process details page."""
    return render_template('process_details.html')


# Menjalankan aplikasi Flask
if __name__ == '__main__':
    ports = [5001, 5002, 5003, 5004, 5005]

    for port in ports:
        try:
            print(f"Mencoba menjalankan aplikasi pada port {port}...")
            app.run(debug=True, host='0.0.0.0', port=port)
            break  # Keluar dari loop jika berhasil
        except OSError as e:
            if "Address already in use" in str(e):
                print(f"Port {port} sudah digunakan. Mencoba port berikutnya...")
            else:
                print(f"Error: {e}")
                break
    else:
        print("Semua port yang dicoba sudah digunakan. Harap tutup beberapa aplikasi dan coba lagi.")
