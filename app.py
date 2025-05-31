# File: app.py
# Deskripsi: Aplikasi web Flask untuk watermarking dokumen .docx dengan QR Code LSB.

import os
import subprocess
import uuid
import shutil
from flask import Flask, render_template, request, jsonify, send_from_directory
from PIL import Image
import numpy as np

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

ALLOWED_DOCX_EXTENSIONS = {'docx'}
ALLOWED_IMAGE_EXTENSIONS = {'png'}


def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


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

    args = ['generate_qr', '--data', data, '--output', qr_output_path]
    result = run_main_script(args)

    if result["success"] and os.path.exists(qr_output_path):
        return jsonify({
            "success": True,
            "message": "QR Code berhasil dibuat!",
            "qr_url": f"/static/generated/{qr_filename}",
            "qr_filename": qr_filename,
            "log": result["stdout"]
        })
    else:
        return jsonify({
            "success": False,
            "message": "Gagal membuat QR Code.",
            "log": result["stderr"] or result.get("error", "Error tidak diketahui")
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
        error_msg = "Format Dokumen harus .docx"
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

    stego_docx_filename = f"stego_doc_{uuid.uuid4().hex}.docx"
    stego_docx_output_path = os.path.join(app.config['GENERATED_FOLDER'], stego_docx_filename)
    
    # Juga siapkan path untuk dokumen hasil di folder documents
    documents_filename = f"watermarked_{uuid.uuid4().hex}.docx"
    documents_output_path = os.path.join(app.config['DOCUMENTS_FOLDER'], documents_filename)

    args = ['embed_docx', '--docx', docx_temp_path, '--qr', qr_temp_path, '--output', stego_docx_output_path]
    print("[*] Memulai proses embed_docx")
    result = run_main_script(args)

    if result["success"]:
        print("[*] Proses embed_docx berhasil")
        
        # Run the embed_watermark_to_docx function directly to get the processed images
        try:
            print("[*] Mendapatkan informasi gambar yang diproses")
            process_result = embed_watermark_to_docx(docx_temp_path, qr_temp_path, stego_docx_output_path)
            
            # Get processed images info if available
            processed_images = []
            qr_image_url = ""
            public_dir = ""
            qr_info = None
            
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
        except Exception as e:
            print(f"[!] Error saat mendapatkan informasi gambar: {str(e)}")
            processed_images = []
            qr_image_url = ""
            public_dir = ""
            qr_info = None
        
        # Hitung MSE dan PSNR
        metrics = calculate_metrics(docx_temp_path, stego_docx_output_path)
        print(f"[*] Metrik MSE: {metrics['mse']}, PSNR: {metrics['psnr']}")

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

        # Hapus file temporary setelah perhitungan metrik
        if os.path.exists(docx_temp_path):
            os.remove(docx_temp_path)
        if os.path.exists(qr_temp_path):
            os.remove(qr_temp_path)

        return jsonify({
            "success": True,
            "message": "Watermark berhasil disisipkan ke dokumen!",
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
            "qr_data": qr_data
        })
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
        return jsonify({"success": False, "message": "Format Dokumen harus .docx"}), 400

    docx_validate_filename = f"doc_extract_in_{uuid.uuid4().hex}.docx"
    docx_temp_path = os.path.join(app.config['UPLOAD_FOLDER'], docx_validate_filename)
    docx_file.save(docx_temp_path)

    extraction_id = uuid.uuid4().hex
    output_extraction_dir_name = f"extraction_{extraction_id}"
    output_extraction_dir_path = os.path.join(app.config['GENERATED_FOLDER'], output_extraction_dir_name)

    args = ['extract_docx', '--docx', docx_temp_path, '--output_dir', output_extraction_dir_path]
    print("[*] Memulai proses extract_docx")
    result = run_main_script(args)

    if result["success"]:
        extracted_qrs_info = []
        if os.path.exists(output_extraction_dir_path) and os.path.isdir(output_extraction_dir_path):
            for filename in os.listdir(output_extraction_dir_path):
                if filename.lower().endswith('.png'):
                    extracted_qrs_info.append({
                        "filename": filename,
                        "url": f"/static/generated/{output_extraction_dir_name}/{filename}"
                    })

        if not extracted_qrs_info and "Tidak ada gambar yang ditemukan" not in result["stdout"]:
            pass

        # Hapus file temporary setelah selesai
        if os.path.exists(docx_temp_path):
            os.remove(docx_temp_path)

        print("[*] Proses extract_docx berhasil")
        return jsonify({
            "success": True,
            "message": "Proses ekstraksi selesai.",
            "extracted_qrs": extracted_qrs_info,
            "log": result["stdout"]
        })
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


@app.route('/download_generated/<filename>')
def download_generated(filename):
    """Endpoint untuk mengunduh file dari folder generated."""
    return send_from_directory(app.config['GENERATED_FOLDER'], filename, as_attachment=True)


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
