# Penjelasan Sistem Watermarking Dokumen dengan QR Code

## 1. Proses Generate QR Code

### Alur Proses
Proses pembuatan QR Code dimulai ketika user memasukkan data yang ingin disimpan dalam QR Code.

```python
@app.route('/generate_qr', methods=['POST'])
def generate_qr_route():
    # 1. Ambil data dari form
    data = request.form.get('qrData')
    if not data:
        return jsonify({"success": False, "message": "Data QR tidak boleh kosong"})
    
    # 2. Buat nama file unik untuk QR Code
    qr_filename = f"qr_{uuid.uuid4().hex}.png"
    qr_output_path = os.path.join(app.config['GENERATED_FOLDER'], qr_filename)
    
    # 3. Import fungsi CRC32 untuk keamanan data
    from qr_utils import add_crc32_checksum
    
    try:
        # 4. Tambahkan CRC32 checksum ke data
        data_with_checksum = add_crc32_checksum(data)
        # Struktur data: {"data": "isi data user", "crc32": "nilai checksum"}
        
        # 5. Konversi ke JSON string
        qr_data_json = json.dumps(data_with_checksum, separators=(',', ':'))
        
        # 6. Generate QR Code menggunakan script utama
        args = ['generate_qr', '--data', qr_data_json, '--output', qr_output_path]
        result = run_main_script(args)
        
        if result["success"] and os.path.exists(qr_output_path):
            return jsonify({
                "success": True,
                "message": "QR Code berhasil dibuat",
                "download_url": f"/download_generated/{qr_filename}",
                "qr_image": f"/static/generated/{qr_filename}"
            })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
```

**Fungsi CRC32 Checksum:**
```python
def add_crc32_checksum(data):
    """Menambahkan CRC32 checksum ke data"""
    crc32_value = zlib.crc32(data.encode('utf-8'))
    return {
        "data": data,
        "crc32": format(crc32_value, '08x')  # Format sebagai hex 8 digit
    }
```

## 2. Proses Embed Watermark ke Dokumen

### Alur Proses Embedding
Proses menyisipkan QR Code ke dalam gambar-gambar di dokumen menggunakan metode LSB (Least Significant Bit).

```python
@app.route('/embed_docx', methods=['POST'])
def embed_docx_route():
    # 1. Validasi file yang diupload
    if 'docxFileEmbed' not in request.files or 'qrFileEmbed' not in request.files:
        return jsonify({"success": False, "message": "File dokumen dan QR Code diperlukan"})
    
    docx_file = request.files['docxFileEmbed']
    qr_file = request.files['qrFileEmbed']
    
    # 2. Simpan file sementara
    docx_filename = f"doc_embed_in_{uuid.uuid4().hex}.docx"
    qr_embed_filename = f"qr_embed_in_{uuid.uuid4().hex}.png"
    docx_temp_path = os.path.join(app.config['UPLOAD_FOLDER'], docx_filename)
    qr_temp_path = os.path.join(app.config['UPLOAD_FOLDER'], qr_embed_filename)
    
    docx_file.save(docx_temp_path)
    qr_file.save(qr_temp_path)
    
    # 3. Simpan ukuran file asli untuk perbandingan
    original_file_size = get_file_size_info(docx_temp_path)
    
    # 4. Tentukan jenis file (PDF atau DOCX)
    file_extension = docx_file.filename.rsplit('.', 1)[1].lower()
    is_pdf = file_extension == 'pdf'
    
    # 5. Proses embedding berdasarkan jenis file
    if is_pdf:
        # Proses PDF
        from pdf_utils import embed_watermark_to_pdf_images
        pdf_process_dir = os.path.join(app.config['GENERATED_FOLDER'], f"pdf_process_{uuid.uuid4().hex}")
        os.makedirs(pdf_process_dir, exist_ok=True)
        
        pdf_result = embed_watermark_to_pdf_images(docx_temp_path, qr_temp_path, pdf_process_dir)
    else:
        # Proses DOCX
        stego_docx_output_path = os.path.join(app.config['GENERATED_FOLDER'], stego_docx_filename)
        args = ['embed_docx', '--docx', docx_temp_path, '--qr', qr_temp_path, '--output', stego_docx_output_path]
        result = run_main_script(args)
```

### Detail Proses Embedding LSB:

```python
def embed_lsb(cover_image, secret_image):
    """Menyisipkan watermark menggunakan metode LSB"""
    # 1. Konversi gambar ke array numpy
    cover_array = np.array(cover_image)
    secret_array = np.array(secret_image)
    
    # 2. Resize secret image jika perlu
    if secret_array.shape != cover_array.shape[:2]:
        secret_resized = Image.fromarray(secret_array).resize(
            (cover_array.shape[1], cover_array.shape[0]), 
            Image.Resampling.LANCZOS
        )
        secret_array = np.array(secret_resized)
    
    # 3. Proses embedding per pixel
    stego_array = cover_array.copy()
    for i in range(cover_array.shape[0]):
        for j in range(cover_array.shape[1]):
            # Ambil bit dari secret image
            secret_bit = (secret_array[i, j] // 128) & 1
            
            # Sisipkan ke LSB dari cover image
            for k in range(cover_array.shape[2]):  # RGB channels
                stego_array[i, j, k] = (cover_array[i, j, k] & 0xFE) | secret_bit
    
    return Image.fromarray(stego_array)
```

### Analisis Kualitas:

```python
def calculate_metrics(original_docx_path, stego_docx_path):
    """Menghitung MSE dan PSNR untuk mengukur kualitas"""
    # 1. Ekstrak gambar dari kedua dokumen
    original_images = extract_images_from_docx(original_docx_path, original_images_dir)
    stego_images = extract_images_from_docx(stego_docx_path, stego_images_dir)
    
    total_mse = 0
    all_psnr_values = []
    
    # 2. Hitung metrik untuk setiap pasangan gambar
    for original_img_path, stego_img_path in zip(original_images, stego_images):
        original_img = np.array(Image.open(original_img_path))
        stego_img = np.array(Image.open(stego_img_path))
        
        # 3. Hitung MSE (Mean Square Error)
        mse = np.mean((original_img - stego_img) ** 2)
        total_mse += mse
        
        # 4. Hitung PSNR (Peak Signal-to-Noise Ratio)
        if mse > 0:
            max_pixel = 255.0
            psnr = 20 * np.log10(max_pixel / np.sqrt(mse))
            all_psnr_values.append(psnr)
        else:
            all_psnr_values.append(float('inf'))  # Gambar identik
    
    # 5. Rata-rata metrik
    final_mse = total_mse / len(original_images)
    final_psnr = sum(all_psnr_values) / len(all_psnr_values)
    
    return {"mse": final_mse, "psnr": final_psnr}
```

## 3. Proses Ekstraksi Watermark

### Alur Proses Ekstraksi
Proses mengambil kembali QR Code yang tersembunyi dalam dokumen.

```python
@app.route('/extract_docx', methods=['POST'])
def extract_docx_route():
    # 1. Validasi file upload
    if 'docxFileValidate' not in request.files:
        return jsonify({"success": False, "message": "File dokumen diperlukan"})
    
    docx_file = request.files['docxFileValidate']
    
    # 2. Simpan file sementara
    file_extension = docx_file.filename.rsplit('.', 1)[1].lower()
    docx_validate_filename = f"doc_extract_in_{uuid.uuid4().hex}.{file_extension}"
    docx_temp_path = os.path.join(app.config['UPLOAD_FOLDER'], docx_validate_filename)
    docx_file.save(docx_temp_path)
    
    # 3. Buat direktori output untuk hasil ekstraksi
    extraction_id = uuid.uuid4().hex
    output_extraction_dir_path = os.path.join(
        app.config['GENERATED_FOLDER'], 
        f"extraction_{extraction_id}"
    )
    
    # 4. Proses ekstraksi berdasarkan jenis file
    is_pdf = file_extension == 'pdf'
    
    if is_pdf:
        from pdf_utils import extract_watermark_from_pdf
        pdf_result = extract_watermark_from_pdf(docx_temp_path, output_extraction_dir_path)
        result = {"success": pdf_result.get("success"), "stdout": pdf_result.get("message", "")}
    else:
        args = ['extract_docx', '--docx', docx_temp_path, '--output_dir', output_extraction_dir_path]
        result = run_main_script(args)
```

### Detail Proses Ekstraksi LSB:

```python
def extract_lsb(stego_image, watermark_size):
    """Ekstrak watermark dari gambar menggunakan LSB"""
    # 1. Konversi gambar ke array numpy
    stego_array = np.array(stego_image)
    
    # 2. Siapkan array untuk watermark
    watermark_array = np.zeros((watermark_size[0], watermark_size[1]), dtype=np.uint8)
    
    # 3. Ekstrak LSB dari setiap pixel
    for i in range(watermark_size[0]):
        for j in range(watermark_size[1]):
            if i < stego_array.shape[0] and j < stego_array.shape[1]:
                # Ambil LSB dari channel pertama (R)
                lsb = stego_array[i, j, 0] & 1
                # Konversi ke nilai pixel (0 atau 255)
                watermark_array[i, j] = lsb * 255
    
    return Image.fromarray(watermark_array, mode='L')
```

### Validasi Integritas dengan CRC32:

```python
def verify_crc32_checksum(qr_data_parsed):
    """Verifikasi integritas data menggunakan CRC32"""
    try:
        # 1. Parse data JSON
        data_dict = json.loads(qr_data_parsed)
        
        # 2. Ambil data asli dan checksum yang tersimpan
        original_data = data_dict.get("data", "")
        stored_crc32 = data_dict.get("crc32", "")
        
        # 3. Hitung CRC32 dari data asli
        calculated_crc32 = format(zlib.crc32(original_data.encode('utf-8')), '08x')
        
        # 4. Bandingkan checksum
        is_valid = calculated_crc32 == stored_crc32
        
        return {
            "is_valid": is_valid,
            "data": original_data,
            "stored_crc32": stored_crc32,
            "calculated_crc32": calculated_crc32,
            "message": "Data valid dan tidak rusak" if is_valid else "Data rusak atau telah dimodifikasi"
        }
    except Exception as e:
        return {
            "is_valid": False,
            "error": str(e),
            "message": "Gagal memverifikasi data"
        }
```

### Proses Lengkap Ekstraksi:

```python
def extract_and_validate_qr(image_path):
    """Ekstrak QR Code dari gambar dan validasi"""
    # 1. Buka gambar yang mengandung watermark
    stego_image = Image.open(image_path)
    
    # 2. Ekstrak watermark (QR Code) menggunakan LSB
    extracted_qr = extract_lsb(stego_image, (200, 200))  # Asumsi ukuran QR 200x200
    
    # 3. Simpan QR Code yang diekstrak
    qr_output_path = f"extracted_qr_{uuid.uuid4().hex}.png"
    extracted_qr.save(qr_output_path)
    
    # 4. Baca data dari QR Code
    qr_data = read_qr(qr_output_path)
    
    # 5. Validasi integritas data
    validation_result = verify_crc32_checksum(qr_data)
    
    return {
        "qr_image_path": qr_output_path,
        "qr_data": qr_data,
        "validation": validation_result
    }
```

## Keunggulan Sistem

1. **Keamanan Data**
   - Watermark tersembunyi menggunakan LSB steganography
   - CRC32 checksum memastikan integritas data
   - Data tidak dapat dimodifikasi tanpa terdeteksi

2. **Kualitas Dokumen**
   - Perubahan visual minimal (PSNR > 40 dB)
   - MSE rendah menunjukkan distorsi minimal
   - Ukuran file tidak berubah signifikan

3. **Mendukung Multiple Format**
   - Dapat memproses file DOCX
   - Dapat memproses file PDF
   - Ekstraksi otomatis dari berbagai format gambar

4. **Analisis Lengkap**
   - Laporan MSE dan PSNR untuk setiap gambar
   - Perbandingan ukuran file sebelum dan sesudah
   - Analisis pixel-by-pixel untuk detail maksimal

## Catatan Penting

- Dokumen harus memiliki minimal 1 gambar untuk proses watermarking
- QR Code harus dalam format PNG dengan ukuran yang sesuai
- Semakin besar gambar dalam dokumen, semakin banyak data yang bisa disimpan
- Proses ekstraksi hanya bisa dilakukan pada dokumen yang sudah di-watermark dengan sistem ini
- CRC32 checksum akan memastikan bahwa data yang diekstrak sama persis dengan data asli yang dimasukkan