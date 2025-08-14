# File: app.py
# Deskripsi: Aplikasi web Flask untuk watermarking dokumen .docx dengan QR Code LSB.

import os
import subprocess
import uuid
import shutil
from flask import Flask, render_template, request, jsonify, send_from_directory
from PIL import Image
import numpy as np
import json
import time

from main import extract_images_from_docx, embed_watermark_to_docx
from qr_utils import read_qr

# Inisialisasi aplikasi Flask
app = Flask(__name__)

# Konfigurasi path
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
GENERATED_FOLDER = os.path.join(BASE_DIR, 'static', 'generated')
DOCUMENTS_FOLDER = os.path.join(BASE_DIR, 'public', 'documents')
MAIN_SCRIPT_PATH = os.path.join(BASE_DIR, 'main.py')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(GENERATED_FOLDER, exist_ok=True)
os.makedirs(DOCUMENTS_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['GENERATED_FOLDER'] = GENERATED_FOLDER
app.config['DOCUMENTS_FOLDER'] = DOCUMENTS_FOLDER
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
    
    return {
        "original": original_info,
        "processed": processed_info,
        "difference_bytes": difference_bytes,
        "difference_percentage": round(difference_percentage, 2),
        "size_change": size_change
    }


def run_main_script(args):
    """Menjalankan skrip main.py dan menangkap output."""
    command = ['python', MAIN_SCRIPT_PATH] + args
    try:
        print(f"[*] Menjalankan perintah: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
        print(f"[*] Stdout: {result.stdout}")
        print(f"[*] Stderr: {result.stderr}")
        return {"success": True, "stdout": result.stdout, "stderr": result.stderr}
    except subprocess.CalledProcessError as e:
        print(f"[!] Error saat menjalankan skrip: {e}")
        print(f"    Stdout: {e.stdout}")
        print(f"    Stderr: {e.stderr}")
        return {"success": False, "stdout": e.stdout, "stderr": e.stderr, "error": str(e)}
    except FileNotFoundError:
        error_msg = "[!] Error: Perintah 'python' atau skrip 'main.py' tidak ditemukan. Pastikan Python terinstal dan path sudah benar."
        print(error_msg)
        return {"success": False, "stdout": "", "stderr": error_msg, "error": error_msg}
    except Exception as e:
        error_msg = f"[!] Exception saat menjalankan skrip: {str(e)}"
        print(error_msg)
        return {"success": False, "stdout": "", "stderr": error_msg, "error": error_msg}


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
    if not data:
        return jsonify({"success": False, "message": "Data QR tidak boleh kosong."}), 400

    qr_filename = f"qr_{uuid.uuid4().hex}.png"
    qr_output_path = os.path.join(app.config['GENERATED_FOLDER'], qr_filename)

    # Import fungsi CRC32
    from qr_utils import add_crc32_checksum
    
    try:
        # Tambahkan CRC32 checksum
        data_with_checksum = add_crc32_checksum(data)
        
        # Konversi ke JSON
        qr_data_json = json.dumps(data_with_checksum, separators=(',', ':'))
        
        # Generate QR Code dengan checksum
        args = ['generate_qr', '--data', qr_data_json, '--output', qr_output_path]
        result = run_main_script(args)

        if result["success"] and os.path.exists(qr_output_path):
            return jsonify({
                "success": True,
                "message": "QR Code berhasil dibuat dengan CRC32 checksum!",
                "qr_url": f"/static/generated/{qr_filename}",
                "qr_filename": qr_filename,
                "log": result["stdout"],
                "crc32_info": {
                    "checksum": data_with_checksum.get('crc32'),
                    "data_length": len(data),
                    "integrity_protected": True
                }
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
            "message": f"Error menambahkan CRC32: {str(e)}"
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
        # Proses PDF menggunakan pdf_utils
        from pdf_utils import embed_watermark_to_pdf_images, create_watermarked_pdf
        print("[*] Memulai proses embed watermark ke PDF")
        
        # Buat direktori untuk proses PDF
        pdf_process_dir = os.path.join(app.config['GENERATED_FOLDER'], f"pdf_process_{uuid.uuid4().hex}")
        os.makedirs(pdf_process_dir, exist_ok=True)
        
        # Embed watermark ke halaman PDF
        pdf_result = embed_watermark_to_pdf_images(docx_temp_path, qr_temp_path, pdf_process_dir)
        
        if not pdf_result.get("success"):
            return jsonify({
                "success": False,
                "message": pdf_result.get("message", "Gagal memproses PDF"),
                "error_type": pdf_result.get("error_type", "PDF_PROCESSING_ERROR")
            }), 500
        
        # Buat PDF baru dari gambar watermarked
        watermarked_pdf_created = create_watermarked_pdf(
            docx_temp_path, 
            pdf_result["output_directories"]["watermarked_pages"], 
            stego_docx_output_path
        )
        
        if not watermarked_pdf_created:
            return jsonify({
                "success": False,
                "message": "Gagal membuat PDF watermarked",
                "error_type": "PDF_CREATION_ERROR"
            }), 500
        
        result = {"success": True, "stdout": "PDF watermarking berhasil", "stderr": ""}
        process_result = pdf_result
        
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
            # Untuk PDF, konversi path ke format relatif yang benar
            raw_processed_images = process_result.get("processed_images", [])
            processed_images = []
            
            # Ambil nama direktori dari path output PDF
            pdf_dir_name = os.path.basename(pdf_process_dir)
            
            for img_info in raw_processed_images:
                # Salin file ke direktori public untuk akses web
                page_num = img_info.get("page_number", 1) - 1
                original_filename = f"original_{page_num}.png"
                watermarked_filename = f"watermarked_{page_num}.png"
                
                # Path untuk public access
                original_public_path = os.path.join(app.config['GENERATED_FOLDER'], pdf_dir_name, original_filename)
                watermarked_public_path = os.path.join(app.config['GENERATED_FOLDER'], pdf_dir_name, watermarked_filename)
                
                # Salin file dari direktori proses PDF ke direktori public
                try:
                    if "original_path" in img_info and os.path.exists(img_info["original_path"]):
                        shutil.copy(img_info["original_path"], original_public_path)
                    if "watermarked_path" in img_info and os.path.exists(img_info["watermarked_path"]):
                        shutil.copy(img_info["watermarked_path"], watermarked_public_path)
                        
                    # Tambahkan ke processed_images dengan path relatif yang benar
                    processed_images.append({
                        "index": page_num,
                        "original": f"generated/{pdf_dir_name}/{original_filename}",
                        "watermarked": f"generated/{pdf_dir_name}/{watermarked_filename}",
                        "individual_metrics": img_info.get("metrics", {})
                    })
                except Exception as e:
                    print(f"[!] Error menyalin file untuk halaman {page_num + 1}: {e}")
            
            # Salin QR Code ke direktori public juga
            qr_filename = "watermark_qr.png"
            qr_public_path = os.path.join(app.config['GENERATED_FOLDER'], pdf_dir_name, qr_filename)
            try:
                shutil.copy(qr_temp_path, qr_public_path)
                qr_image_url = f"generated/{pdf_dir_name}/{qr_filename}"
            except Exception as e:
                print(f"[!] Error menyalin QR Code: {e}")
                qr_image_url = ""
                
            public_dir = pdf_dir_name
            qr_info = None
            pdf_info = process_result.get("pdf_info", {})
            print(f"[*] PDF berhasil diproses: {len(processed_images)} halaman")
        else:
            # Run the embed_watermark_to_docx function directly to get the processed images
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
        
        # Hitung MSE dan PSNR
        if not is_pdf:
            metrics = calculate_metrics(docx_temp_path, stego_docx_output_path)
            print(f"[*] Metrik MSE: {metrics['mse']}, PSNR: {metrics['psnr']}")
        else:
            # Untuk PDF, gunakan rata-rata dari semua halaman
            metrics = {"mse": 0, "psnr": 0}
            if process_result and "analysis" in process_result and "page_analyses" in process_result["analysis"]:
                page_metrics = [p["metrics"] for p in process_result["analysis"]["page_analyses"] if p["metrics"].get("success")]
                if page_metrics:
                    avg_mse = sum(m["mse"] for m in page_metrics) / len(page_metrics)
                    avg_psnr = sum(m["psnr"] for m in page_metrics if m["psnr"] != float('inf')) / len([m for m in page_metrics if m["psnr"] != float('inf')]) if any(m["psnr"] != float('inf') for m in page_metrics) else float('inf')
                    metrics = {"mse": avg_mse, "psnr": avg_psnr}
                    print(f"[*] Metrik rata-rata PDF - MSE: {avg_mse}, PSNR: {avg_psnr}")
        
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
            for page_analysis in process_result["analysis"].get("page_analyses", []):
                page_num = page_analysis.get("page_number", 0) - 1  # Convert to 0-based index
                image_analyses.append({
                    "image_index": page_num,
                    "original": page_analysis.get("original", {}),
                    "watermarked": page_analysis.get("watermarked", {})
                })
                
                detailed_metrics.append({
                    "image_index": page_num,
                    "metrics": page_analysis.get("metrics", {})
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

        # Hitung perbandingan ukuran file sebelum menghapus file temporary
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
        # Proses PDF menggunakan pdf_utils
        from pdf_utils import extract_watermark_from_pdf
        print("[*] Memulai proses extract watermark dari PDF")
        
        pdf_result = extract_watermark_from_pdf(docx_temp_path, output_extraction_dir_path)
        
        if pdf_result.get("success"):
            result = {"success": True, "stdout": "PDF extraction berhasil", "stderr": ""}
            extracted_qrs_info = pdf_result.get("extracted_qrs", [])
        else:
            result = {"success": False, "stdout": "", "stderr": pdf_result.get("message", "PDF extraction gagal")}
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
            # QR Code lama tanpa CRC32
            return jsonify({
                "success": True,
                "integrity_check": False,
                "message": "QR Code tidak memiliki CRC32 checksum (format lama)",
                "data": qr_data_raw
            })
        
        # Import fungsi verifikasi
        from qr_utils import verify_crc32_checksum
        
        # Verifikasi CRC32
        is_valid = verify_crc32_checksum(qr_data_parsed)
        
        return jsonify({
            "success": True,
            "integrity_check": True,
            "data_valid": is_valid,
            "message": "Data valid dan tidak rusak" if is_valid else "Data rusak atau dimodifikasi",
            "data": qr_data_parsed.get("data", ""),
            "crc32_info": {
                "stored_checksum": qr_data_parsed.get("crc32"),
                "timestamp": qr_data_parsed.get("timestamp"),
                "status": "VALID" if is_valid else "INVALID"
            }
        })
        
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
    return send_from_directory(app.config['GENERATED_FOLDER'], filepath)


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
